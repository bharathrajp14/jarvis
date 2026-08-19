import { EVENT_TYPES } from './contracts.js';

const VIEW_BY_COMMAND = Object.freeze({
    'open-assistant': 'chatView',
    'open-tasks': 'automationsView',
    'open-career': 'careerView',
    'open-memory': 'knowledgeView',
    'show-status': 'dashboardView',
});

function ensureShellStatus() {
    const controls = document.querySelector('.header-controls');
    if (!controls || document.getElementById('platformConnectionStatus')) return;

    const status = document.createElement('div');
    status.id = 'platformConnectionStatus';
    status.className = 'platform-connection-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.innerHTML = '<span class="platform-status-dot" aria-hidden="true"></span><span class="platform-status-label">Connecting</span>';
    controls.prepend(status);
}

function setConnectionStatus(status, detail = {}) {
    ensureShellStatus();
    const root = document.getElementById('platformConnectionStatus');
    if (!root) return;
    const label = root.querySelector('.platform-status-label');
    const dot = root.querySelector('.platform-status-dot');
    const labels = {
        connected: 'Runtime online',
        reconnecting: 'Reconnecting',
        error: 'Connection error',
        disconnected: 'Runtime offline',
    };
    const semantic = status === 'connected' ? 'success' : status === 'reconnecting' ? 'warning' : 'error';
    root.dataset.status = semantic;
    if (label) label.textContent = detail.label || labels[status] || 'Runtime status unknown';
    if (dot) dot.dataset.status = semantic;
}

function showSurface(viewId) {
    if (typeof window.switchView === 'function') {
        window.switchView(viewId);
        const first = document.querySelector(`[data-view="${viewId}"]`);
        if (first) first.focus({ preventScroll: true });
    }
}

function bindCommandExecution() {
    const commands = window.BRJARVIS?.commands;
    if (!commands || commands.__shellBound) return;
    commands.__shellBound = true;
    commands.addEventListener('execute', (event) => {
        const id = event.detail.command.id;
        const target = VIEW_BY_COMMAND[id];
        if (target) {
            showSurface(target);
            return;
        }
        if (id === 'cancel-active-task') {
            window.dispatchEvent(new CustomEvent('brjarvis:cancel-task-requested', { detail: event.detail }));
            if (typeof window.showToast === 'function') window.showToast('Cancellation requested', 'JARVIS is stopping the active task.', 'warning');
        }
    });
}

function bindPlatformEvents() {
    if (window.__BRJARVIS_SHELL_BOUND) return;
    window.__BRJARVIS_SHELL_BOUND = true;
    ensureShellStatus();
    window.addEventListener('brjarvis:legacy-connection', (event) => setConnectionStatus(event.detail?.status, event.detail));
    window.addEventListener('brjarvis:platform-event', (event) => {
        const normalized = event.detail;
        if (normalized.type === EVENT_TYPES.SERVER_READY) setConnectionStatus('connected', { label: `Runtime ${normalized.payload?.server_version || 'online'}` });
        if (normalized.type === EVENT_TYPES.ERROR) setConnectionStatus('error');
    });
    bindCommandExecution();
}

function initializeShell() {
    document.documentElement.dataset.platform = 'brjarvis';
    document.body.classList.add('platform-ready');
    document.querySelector('.left-panel')?.setAttribute('aria-label', 'BRJARVIS navigation');
    document.querySelector('.center-panel')?.setAttribute('aria-label', 'BRJARVIS intelligence workspace');
    document.querySelector('.right-panel')?.setAttribute('aria-label', 'Task and context inspector');
    ensureShellStatus();
    bindPlatformEvents();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeShell, { once: true });
else initializeShell();

export { initializeShell, setConnectionStatus };
