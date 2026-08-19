import { ApiClient } from './api-client.js';
import { CommandRegistry } from './command-registry.js';
import { EventAdapter } from './event-adapter.js';
import './shell.js';
import './assistant.js';
import './palette.js';
import { CAPABILITY_STATUS, EVENT_TYPES, TASK_STATUS } from './contracts.js';

const eventAdapter = new EventAdapter();
const api = new ApiClient();
const commands = new CommandRegistry();

const platform = {
    version: '0.1.0',
    api,
    events: eventAdapter,
    commands,
    constants: { CAPABILITY_STATUS, EVENT_TYPES, TASK_STATUS },
    capabilities: {
        models: true,
        automation: true,
        activeTask: false,
        // The current API exposes task creation/approval but no cancellation route.
        // Keep cancellation visibly unavailable until a real control endpoint exists.
        taskControl: false,
        voice: Boolean(window.MediaRecorder || navigator.mediaDevices),
        vision: false,
    },
    getSnapshot() {
        return {
            capabilities: { ...this.capabilities },
            realtime: eventAdapter.snapshot(),
        };
    },
};

window.BRJARVIS = window.BRJARVIS || {};
window.BRJARVIS.platform = platform;
window.BRJARVIS.api = api;
window.BRJARVIS.events = eventAdapter;
window.BRJARVIS.commands = commands;

window.addEventListener('brjarvis:legacy-message', (event) => {
    eventAdapter.ingest(event.detail);
});

window.addEventListener('brjarvis:legacy-connection', (event) => {
    const { status, detail } = event.detail || {};
    eventAdapter.setConnection(status || 'disconnected', detail || {});
});

eventAdapter.addEventListener('event', (event) => {
    const normalized = event.detail;
    if (normalized.task?.status) platform.capabilities.activeTask = ![TASK_STATUS.COMPLETED, TASK_STATUS.FAILED, TASK_STATUS.CANCELLED].includes(normalized.task.status);
    window.dispatchEvent(new CustomEvent('brjarvis:platform-event', { detail: normalized }));
});

export { platform };
