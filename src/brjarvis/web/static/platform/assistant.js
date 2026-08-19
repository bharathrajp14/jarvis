import { EVENT_TYPES, TASK_STATUS } from './contracts.js';

function escapeText(value) {
    return String(value ?? '');
}

class AssistantTaskProjection {
    constructor(platform) {
        this.platform = platform;
        this.currentTask = null;
        this.root = null;
        this.ensureRoot();
        platform.events.addEventListener('event', (event) => this.handle(event.detail));
        window.addEventListener('brjarvis:legacy-connection', (event) => this.updateConnection(event.detail?.status));
        const existingTasks = platform.events.snapshot().tasks;
        if (existingTasks.length) {
            this.currentTask = existingTasks[existingTasks.length - 1];
            this.renderTask(this.currentTask);
        }
    }

    ensureRoot() {
        const host = document.getElementById('tabTask');
        if (!host || document.getElementById('platformTaskProjection')) return;
        this.root = document.createElement('section');
        this.root.id = 'platformTaskProjection';
        this.root.className = 'platform-task-projection';
        this.root.setAttribute('aria-labelledby', 'platformTaskTitle');
        this.root.innerHTML = `
            <div class="platform-task-header">
                <div>
                    <div class="platform-eyebrow">LIVE EXECUTION</div>
                    <h3 id="platformTaskTitle">No active task</h3>
                </div>
                <span class="platform-task-status" data-status="idle">Idle</span>
            </div>
            <p class="platform-task-goal">Start a request in Assistant to see real execution state.</p>
            <div class="platform-progress-track" aria-label="Task progress"><span class="platform-progress-value"></span></div>
            <div class="platform-task-meta"><span class="platform-current-step">Waiting for runtime event</span><span class="platform-progress-label">—</span></div>
            <div class="platform-task-steps" aria-live="polite"></div>
            <div class="platform-task-actions"><button class="btn btn-secondary platform-task-cancel" type="button" disabled title="Task cancellation is not available in the current backend API">Cancel unavailable</button></div>
        `;
        host.prepend(this.root);
    }

    handle(event) {
        if (!this.root) this.ensureRoot();
        if (!this.root) return;

        if (event.type === EVENT_TYPES.MESSAGE_DELTA_START) {
            this.setStatus('running', 'Streaming response');
            return;
        }
        if (event.type === EVENT_TYPES.MESSAGE_COMPLETED) {
            if (this.currentTask && ![TASK_STATUS.FAILED, TASK_STATUS.CANCELLED].includes(this.currentTask.status)) this.setStatus('completed', 'Response complete');
            return;
        }
        if (event.task) {
            this.currentTask = event.task;
            this.renderTask(event.task);
        }
        if (event.type === EVENT_TYPES.ERROR || event.type === EVENT_TYPES.TASK_FAILED) {
            this.setStatus('failed', event.payload?.error?.message || 'Execution failed');
        }
    }

    renderTask(task) {
        const title = this.root.querySelector('#platformTaskTitle');
        const goal = this.root.querySelector('.platform-task-goal');
        const status = this.root.querySelector('.platform-task-status');
        const progress = this.root.querySelector('.platform-progress-value');
        const progressLabel = this.root.querySelector('.platform-progress-label');
        const currentStep = this.root.querySelector('.platform-current-step');
        const steps = this.root.querySelector('.platform-task-steps');

        if (title) title.textContent = task.goal || `Task ${task.id}`;
        if (goal) goal.textContent = task.goal || 'Runtime task in progress.';
        if (status) {
            status.dataset.status = task.status || 'created';
            status.textContent = this.statusLabel(task.status);
        }
        const hasProgress = Number.isFinite(task.progress);
        if (progress) progress.style.width = `${hasProgress ? Math.round(task.progress * 100) : 0}%`;
        if (progressLabel) progressLabel.textContent = hasProgress ? `${Math.round(task.progress * 100)}% reported` : 'Progress unavailable';
        if (currentStep) currentStep.textContent = task.currentStep || this.stepFallback(task.status);
        if (steps) {
            steps.replaceChildren();
            (task.steps || []).slice(0, 8).forEach((step) => {
                const row = document.createElement('div');
                row.className = 'platform-step-row';
                const indicator = document.createElement('span');
                indicator.className = 'platform-step-indicator';
                indicator.dataset.status = String(step.status || 'pending').toLowerCase();
                indicator.textContent = indicator.dataset.status === 'completed' ? '✓' : indicator.dataset.status === 'failed' ? '!' : '•';
                const label = document.createElement('span');
                label.textContent = escapeText(step.title || step.name || step.step_id || 'Unnamed step');
                row.append(indicator, label);
                steps.append(row);
            });
        }
    }

    updateConnection(status) {
        if (!this.currentTask || !['reconnecting', 'error'].includes(status)) return;
        this.setStatus('disconnected', status === 'reconnecting' ? 'Reconnecting to runtime' : 'Runtime connection error');
    }

    setStatus(status, label) {
        const el = this.root?.querySelector('.platform-task-status');
        if (!el) return;
        el.dataset.status = status;
        el.textContent = label || this.statusLabel(status);
    }

    statusLabel(status) {
        const labels = {
            created: 'Created', planning: 'Planning', running: 'Running', waiting: 'Waiting for approval',
            paused: 'Paused', cancelling: 'Cancelling', completed: 'Completed', failed: 'Failed', cancelled: 'Cancelled',
            disconnected: 'Disconnected', idle: 'Idle',
        };
        return labels[status] || 'Runtime update';
    }

    stepFallback(status) {
        if (status === TASK_STATUS.PLANNING) return 'Planning task';
        if (status === TASK_STATUS.RUNNING) return 'Executing task';
        if (status === TASK_STATUS.WAITING) return 'Waiting for approval or input';
        if (status === TASK_STATUS.COMPLETED) return 'Verified completion';
        if (status === TASK_STATUS.FAILED) return 'Failure requires attention';
        return 'Waiting for runtime event';
    }
}

function initializeAssistantProjection() {
    const platform = window.BRJARVIS?.platform;
    if (!platform || window.__BRJARVIS_ASSISTANT_BOUND) return;
    window.__BRJARVIS_ASSISTANT_BOUND = true;
    window.BRJARVIS.assistant = new AssistantTaskProjection(platform);
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeAssistantProjection, { once: true });
else initializeAssistantProjection();

export { AssistantTaskProjection, initializeAssistantProjection };
