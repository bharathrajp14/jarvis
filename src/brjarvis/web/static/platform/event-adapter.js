import { EVENT_TYPES, normalizeTaskStatus, normalizeType } from './contracts.js';

class EventAdapter extends EventTarget {
    constructor({ maxSeenEvents = 2000, maxTaskEvents = 500 } = {}) {
        super();
        this.maxSeenEvents = maxSeenEvents;
        this.maxTaskEvents = maxTaskEvents;
        this.seen = new Set();
        this.seenQueue = [];
        this.connection = 'disconnected';
        this.tasks = new Map();
        this.messages = new Map();
        this.lastEventAt = 0;
    }

    setConnection(status, detail = {}) {
        this.connection = status;
        this.dispatchEvent(new CustomEvent('connection', { detail: { status, ...detail } }));
    }

    ingest(rawEvent) {
        const event = this.normalize(rawEvent);
        if (!event || this.isDuplicate(event.eventId)) return null;

        this.lastEventAt = event.timestamp;
        this.project(event);
        this.dispatchEvent(new CustomEvent('event', { detail: event }));
        this.dispatchEvent(new CustomEvent(event.type, { detail: event }));
        return event;
    }

    normalize(rawEvent) {
        if (!rawEvent || typeof rawEvent !== 'object') return null;
        const payload = rawEvent.payload && typeof rawEvent.payload === 'object' ? rawEvent.payload : {};
        const type = normalizeType(rawEvent.type || rawEvent.event_type);
        const eventId = String(rawEvent.event_id || rawEvent.id || `${type}:${rawEvent.timestamp || Date.now()}:${Math.random()}`);
        const taskId = rawEvent.task_id || payload.task_id || null;
        const conversationId = rawEvent.conversation_id || payload.conversation_id || null;
        const timestamp = Number(rawEvent.timestamp || Date.now() / 1000);

        return {
            eventId,
            type,
            taskId,
            conversationId,
            requestId: rawEvent.request_id || payload.request_id || null,
            timestamp: Number.isFinite(timestamp) ? timestamp : Date.now() / 1000,
            payload,
            raw: rawEvent,
        };
    }

    isDuplicate(eventId) {
        if (this.seen.has(eventId)) return true;
        this.seen.add(eventId);
        this.seenQueue.push(eventId);
        if (this.seenQueue.length > this.maxSeenEvents) {
            const expired = this.seenQueue.shift();
            this.seen.delete(expired);
        }
        return false;
    }

    project(event) {
        const payload = event.payload;
        if (event.taskId || event.type.startsWith('task.')) {
            const id = event.taskId || payload.task_id;
            if (id) {
                const previous = this.tasks.get(id) || { id, steps: [], tools: [], events: [] };
                const status = normalizeTaskStatus(payload.status || this.statusFromType(event.type));
                const next = {
                    ...previous,
                    id,
                    goal: payload.goal || previous.goal || '',
                    status,
                    progress: this.progressFrom(payload, previous.progress),
                    currentStep: payload.current_step || payload.currentStep || previous.currentStep || null,
                    updatedAt: event.timestamp,
                    events: this.appendBounded(previous.events, event, this.maxTaskEvents),
                };
                if (Array.isArray(payload.steps)) next.steps = payload.steps;
                if (Array.isArray(payload.tools)) next.tools = payload.tools;
                if (payload.error) next.error = payload.error;
                if (payload.approval) next.approval = payload.approval;
                this.tasks.set(id, next);
                event.task = next;
            }
        }

        if (event.type.startsWith('message.')) {
            const messageId = payload.message?.message_id || payload.message?.id || `${event.conversationId || 'conversation'}:${event.taskId || 'message'}`;
            const previous = this.messages.get(messageId) || { id: messageId, text: '' };
            const delta = payload.delta || payload.chunk || '';
            const next = {
                ...previous,
                id: messageId,
                conversationId: event.conversationId,
                taskId: event.taskId,
                text: event.type === EVENT_TYPES.MESSAGE_DELTA ? `${previous.text}${delta}` : (payload.message?.content || previous.text),
                status: event.type === EVENT_TYPES.MESSAGE_COMPLETED ? 'completed' : event.type === EVENT_TYPES.MESSAGE_DELTA_START ? 'streaming' : previous.status,
                updatedAt: event.timestamp,
            };
            this.messages.set(messageId, next);
            event.message = next;
        }
    }

    statusFromType(type) {
        const map = {
            [EVENT_TYPES.TASK_CREATED]: 'created',
            [EVENT_TYPES.TASK_STARTED]: 'running',
            [EVENT_TYPES.TASK_UPDATED]: 'running',
            [EVENT_TYPES.TASK_WAITING]: 'waiting',
            [EVENT_TYPES.TASK_COMPLETED]: 'completed',
            [EVENT_TYPES.TASK_FAILED]: 'failed',
            [EVENT_TYPES.TASK_CANCELLED]: 'cancelled',
            [EVENT_TYPES.AGENT_PLANNING]: 'planning',
            [EVENT_TYPES.AGENT_EXECUTING]: 'running',
            [EVENT_TYPES.AGENT_WAITING]: 'waiting',
        };
        return map[type] || 'created';
    }

    progressFrom(payload, previous = 0) {
        const raw = payload.progress ?? payload.percent ?? previous;
        const value = Number(raw);
        if (!Number.isFinite(value)) return previous;
        return Math.max(0, Math.min(1, value > 1 ? value / 100 : value));
    }

    appendBounded(items, item, limit) {
        const next = [...items, item];
        return next.length > limit ? next.slice(next.length - limit) : next;
    }

    snapshot() {
        return {
            connection: this.connection,
            lastEventAt: this.lastEventAt,
            tasks: Array.from(this.tasks.values()),
            messages: Array.from(this.messages.values()),
        };
    }
}

export { EventAdapter };
