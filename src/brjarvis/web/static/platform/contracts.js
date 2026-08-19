const EVENT_TYPES = Object.freeze({
    SERVER_READY: 'session.ready',
    CONNECTION_OPEN: 'connection.open',
    CONNECTION_RECONNECTING: 'connection.reconnecting',
    CONNECTION_CLOSED: 'connection.closed',
    CONNECTION_ERROR: 'connection.error',
    HEARTBEAT: 'transport.heartbeat',
    MESSAGE_CREATED: 'message.created',
    MESSAGE_DELTA_START: 'message.delta_start',
    MESSAGE_DELTA: 'message.delta',
    MESSAGE_COMPLETED: 'message.completed',
    CONVERSATION_CREATED: 'conversation.created',
    TASK_CREATED: 'task.created',
    TASK_STARTED: 'task.started',
    TASK_UPDATED: 'task.updated',
    TASK_WAITING: 'task.waiting',
    TASK_COMPLETED: 'task.completed',
    TASK_FAILED: 'task.failed',
    TASK_CANCELLED: 'task.cancelled',
    AGENT_PLANNING: 'agent.planning',
    AGENT_EXECUTING: 'agent.executing',
    AGENT_WAITING: 'agent.waiting',
    AGENT_COMPLETED: 'agent.completed',
    TOOL_STARTED: 'tool.started',
    TOOL_COMPLETED: 'tool.completed',
    TOOL_FAILED: 'tool.failed',
    PERMISSION_REQUESTED: 'permission.requested',
    PERMISSION_RESOLVED: 'permission.resolved',
    VERIFICATION_COMPLETED: 'verification.completed',
    VERIFICATION_FAILED: 'verification.failed',
    ARTIFACT_CREATED: 'artifact.created',
    ARTIFACT_UPDATED: 'artifact.updated',
    ARTIFACT_FAILED: 'artifact.failed',
    NOTIFICATION_CREATED: 'notification.created',
    MODEL_CONNECTED: 'model.connected',
    MODEL_DISCONNECTED: 'model.disconnected',
    SYSTEM_HEALTH_CHANGED: 'system.health_changed',
    VOICE_LISTENING: 'voice.listening',
    VOICE_SPEAKING: 'voice.speaking',
    VOICE_INTERRUPTED: 'voice.interrupted',
    VISION_STARTED: 'vision.started',
    VISION_COMPLETED: 'vision.completed',
    VISION_FAILED: 'vision.failed',
    ERROR: 'error',
});

const TASK_STATUS = Object.freeze({
    CREATED: 'created',
    PLANNING: 'planning',
    RUNNING: 'running',
    WAITING: 'waiting',
    PAUSED: 'paused',
    CANCELLING: 'cancelling',
    COMPLETED: 'completed',
    FAILED: 'failed',
    CANCELLED: 'cancelled',
});

const CAPABILITY_STATUS = Object.freeze({
    AVAILABLE: 'available',
    UNAVAILABLE: 'unavailable',
    DEGRADED: 'degraded',
    LOADING: 'loading',
    DISCONNECTED: 'disconnected',
    DENIED: 'denied',
    EXPERIMENTAL: 'experimental',
});

const COMMAND_RISK = Object.freeze({
    SAFE: 'safe',
    CONFIRM: 'confirm',
    DESTRUCTIVE: 'destructive',
    PRIVACY_SENSITIVE: 'privacy_sensitive',
});

const COMMANDS = Object.freeze([
    {
        id: 'open-assistant', label: 'Open Assistant', description: 'Open the main intelligence workspace.',
        group: 'navigation', aliases: ['assistant', 'chat'], shortcut: 'Ctrl+1', risk: COMMAND_RISK.SAFE,
        surfaces: ['web', 'assistant', 'widget', 'desktop', 'cli'],
    },
    {
        id: 'open-tasks', label: 'Open Tasks', description: 'Review active and recent task execution.',
        group: 'tasks', aliases: ['tasks'], shortcut: 'Ctrl+2', risk: COMMAND_RISK.SAFE,
        surfaces: ['web', 'assistant', 'widget', 'desktop', 'cli'],
    },
    {
        id: 'open-career', label: 'Open Career OS', description: 'Open career intelligence and applications.',
        group: 'career', aliases: ['career', 'career os'], shortcut: 'Ctrl+3', risk: COMMAND_RISK.SAFE,
        surfaces: ['web', 'assistant', 'desktop', 'cli'],
    },
    {
        id: 'open-memory', label: 'Search Memory', description: 'Search and inspect remembered context.',
        group: 'memory', aliases: ['memory', 'search memory'], shortcut: 'Ctrl+4', risk: COMMAND_RISK.SAFE,
        surfaces: ['web', 'assistant', 'widget', 'desktop', 'cli'],
    },
    {
        id: 'analyze-screen', label: 'Analyze Screen', description: 'Analyze the selected screen or region when vision is available.',
        group: 'assistant', aliases: ['vision', 'screen'], risk: COMMAND_RISK.PRIVACY_SENSITIVE,
        requires: ['vision'], surfaces: ['web', 'assistant', 'widget', 'desktop', 'cli'],
    },
    {
        id: 'run-automation', label: 'Run Automation', description: 'Run an existing automation with its configured policy.',
        group: 'automation', aliases: ['automation', 'run workflow'], risk: COMMAND_RISK.CONFIRM,
        requires: ['automation'], surfaces: ['web', 'assistant', 'widget', 'desktop', 'cli'],
    },
    {
        id: 'switch-model', label: 'Switch Model', description: 'Choose an available model backend.',
        group: 'system', aliases: ['model', 'models'], risk: COMMAND_RISK.SAFE,
        requires: ['models'], surfaces: ['web', 'assistant', 'desktop', 'cli'],
    },
    {
        id: 'show-status', label: 'Show System Status', description: 'Inspect runtime, event bus, model, voice, and vision health.',
        group: 'system', aliases: ['status', 'health'], shortcut: 'Ctrl+/', risk: COMMAND_RISK.SAFE,
        surfaces: ['web', 'assistant', 'widget', 'desktop', 'cli'],
    },
    {
        id: 'cancel-active-task', label: 'Cancel Active Task', description: 'Request cancellation of the current task.',
        group: 'tasks', aliases: ['cancel', 'stop'], shortcut: 'Escape', risk: COMMAND_RISK.CONFIRM,
        requires: ['activeTask', 'taskControl'], surfaces: ['web', 'assistant', 'widget', 'desktop', 'cli'],
    },
]);

function normalizeType(type) {
    const value = String(type || '').trim().toLowerCase();
    const aliases = {
        serverready: EVENT_TYPES.SERVER_READY,
        'stream_start': EVENT_TYPES.MESSAGE_DELTA_START,
        'stream_chunk': EVENT_TYPES.MESSAGE_DELTA,
        'stream_end': EVENT_TYPES.MESSAGE_COMPLETED,
        heartbeat: EVENT_TYPES.HEARTBEAT,
        'task.tool_started': EVENT_TYPES.TOOL_STARTED,
        'task.tool_completed': EVENT_TYPES.TOOL_COMPLETED,
        'notification.created': EVENT_TYPES.NOTIFICATION_CREATED,
    };
    return aliases[value] || value || EVENT_TYPES.ERROR;
}

function normalizeTaskStatus(value) {
    const status = String(value || '').trim().toLowerCase().replaceAll(' ', '_');
    const aliases = {
        started: TASK_STATUS.RUNNING,
        executing: TASK_STATUS.RUNNING,
        in_progress: TASK_STATUS.RUNNING,
        success: TASK_STATUS.COMPLETED,
        succeeded: TASK_STATUS.COMPLETED,
        complete: TASK_STATUS.COMPLETED,
        waiting_for_approval: TASK_STATUS.WAITING,
        waiting_for_user: TASK_STATUS.WAITING,
        waiting_for_input: TASK_STATUS.WAITING,
        error: TASK_STATUS.FAILED,
        failure: TASK_STATUS.FAILED,
    };
    return aliases[status] || status || TASK_STATUS.CREATED;
}

function normalizeError(error, fallbackTitle = 'BRJARVIS request failed') {
    const source = error && typeof error === 'object' ? error : {};
    const nested = source.error && typeof source.error === 'object' ? source.error : source;
    return {
        code: nested.code || 'UNKNOWN_ERROR',
        title: nested.title || fallbackTitle,
        message: nested.message || String(error || 'The request could not be completed.'),
        reason: nested.reason || undefined,
        retryable: nested.retryable !== false,
        severity: nested.severity || 'error',
        suggestedActions: Array.isArray(nested.suggestedActions) ? nested.suggestedActions : [],
        diagnosticsRef: nested.diagnosticsRef || undefined,
    };
}

export {
    EVENT_TYPES,
    TASK_STATUS,
    CAPABILITY_STATUS,
    COMMAND_RISK,
    COMMANDS,
    normalizeType,
    normalizeTaskStatus,
    normalizeError,
};
