import { COMMAND_RISK } from './contracts.js';

function initializeCommandPalette() {
    if (window.__BRJARVIS_PALETTE_BOUND) return;
    const input = document.getElementById('cmdPaletteInput');
    const results = document.getElementById('cmdPaletteResults');
    if (!input || !results || !window.BRJARVIS?.commands) return;
    window.__BRJARVIS_PALETTE_BOUND = true;

    const render = () => {
        const capabilities = window.BRJARVIS.platform.capabilities;
        const items = window.BRJARVIS.commands.list({ surface: 'web', capabilities, query: input.value });
        results.replaceChildren();
        if (!items.length) {
            const empty = document.createElement('div');
            empty.className = 'sidebar-empty-state';
            empty.textContent = 'No canonical commands match this search.';
            results.append(empty);
            return;
        }
        items.forEach((item) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'platform-command-result';
            button.dataset.commandId = item.id;
            button.disabled = !item.state.available;
            const title = document.createElement('span');
            title.className = 'platform-command-title';
            title.textContent = item.label;
            const description = document.createElement('span');
            description.className = 'platform-command-description';
            description.textContent = item.state.available ? item.description : `Unavailable: ${item.state.missing.join(', ')}`;
            const meta = document.createElement('span');
            meta.className = 'platform-command-meta';
            meta.textContent = item.shortcut || item.state.risk;
            button.append(title, description, meta);
            results.append(button);
        });
    };

    input.addEventListener('input', render);
    results.addEventListener('click', async (event) => {
        const button = event.target.closest('[data-command-id]');
        if (!button || button.disabled) return;
        const command = window.BRJARVIS.commands.get(button.dataset.commandId);
        try {
            await window.BRJARVIS.commands.execute(command.id, { capabilities: window.BRJARVIS.platform.capabilities, confirm: false });
            if (typeof window.closeCommandPalette === 'function') window.closeCommandPalette();
        } catch (error) {
            const message = error.code === 'CONFIRMATION_REQUIRED'
                ? `${command.label} requires a risk-aware confirmation flow.`
                : error.message;
            if (typeof window.showToast === 'function') window.showToast('Command unavailable', message, error.code === 'CONFIRMATION_REQUIRED' ? 'warning' : 'error');
        }
    });

    const modal = document.getElementById('cmdPaletteModal');
    if (modal) {
        const observer = new MutationObserver(() => {
            if (modal.style.display === 'flex') render();
        });
        observer.observe(modal, { attributes: true, attributeFilter: ['style', 'class'] });
    }
    render();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeCommandPalette, { once: true });
else initializeCommandPalette();

export { initializeCommandPalette };
