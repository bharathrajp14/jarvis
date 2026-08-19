import { COMMANDS, COMMAND_RISK } from './contracts.js';

class CommandRegistry extends EventTarget {
    constructor(commands = COMMANDS) {
        super();
        this.commands = new Map(commands.map((command) => [command.id, { ...command }]));
    }

    list({ surface = null, capabilities = {}, query = '' } = {}) {
        const normalizedQuery = String(query || '').trim().toLowerCase();
        return Array.from(this.commands.values())
            .filter((command) => !surface || command.surfaces?.includes(surface))
            .filter((command) => !normalizedQuery || [command.label, command.description, ...(command.aliases || [])].join(' ').toLowerCase().includes(normalizedQuery))
            .map((command) => ({ ...command, state: this.state(command, capabilities) }));
    }

    get(id) {
        return this.commands.get(id) || null;
    }

    state(command, capabilities = {}) {
        const requirements = command.requires || [];
        const missing = requirements.filter((key) => !capabilities[key]);
        return {
            available: missing.length === 0,
            missing,
            risk: command.risk || COMMAND_RISK.SAFE,
        };
    }

    async execute(id, { capabilities = {}, confirm = false, ...context } = {}) {
        const command = this.get(id);
        if (!command) throw new Error(`Unknown command: ${id}`);
        const state = this.state(command, capabilities);
        if (!state.available) {
            const error = new Error(`${command.label} is unavailable.`);
            error.code = 'CAPABILITY_UNAVAILABLE';
            error.missing = state.missing;
            throw error;
        }
        if ([COMMAND_RISK.CONFIRM, COMMAND_RISK.DESTRUCTIVE, COMMAND_RISK.PRIVACY_SENSITIVE].includes(state.risk) && !confirm) {
            const error = new Error(`${command.label} requires confirmation.`);
            error.code = 'CONFIRMATION_REQUIRED';
            error.command = command;
            throw error;
        }

        const detail = { command, context, state };
        this.dispatchEvent(new CustomEvent('execute', { detail }));
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('brjarvis:command', { detail }));
        }
        return detail;
    }
}

export { CommandRegistry };
