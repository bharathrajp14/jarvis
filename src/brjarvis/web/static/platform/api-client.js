import { normalizeError } from './contracts.js';

class ApiError extends Error {
    constructor(userError, status = 0) {
        super(userError.message);
        this.name = 'ApiError';
        this.userError = userError;
        this.status = status;
    }
}

class ApiClient {
    constructor({ baseUrl = '', fetchImpl = null } = {}) {
        this.baseUrl = baseUrl;
        this.fetchImpl = fetchImpl || ((...args) => {
            if (typeof window !== 'undefined' && typeof window.apiFetch === 'function') return window.apiFetch(...args);
            return window.fetch(...args);
        });
    }

    url(path) {
        if (/^https?:\/\//i.test(path)) return path;
        return `${this.baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
    }

    async request(path, { method = 'GET', body, headers = {}, signal } = {}) {
        const options = {
            method,
            credentials: 'include',
            headers: { Accept: 'application/json', ...headers },
            signal,
        };
        if (body !== undefined) {
            options.headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(body);
        }

        let response;
        try {
            response = await this.fetchImpl(this.url(path), options);
        } catch (error) {
            throw new ApiError(normalizeError({ code: 'NETWORK_ERROR', message: 'BRJARVIS could not reach the server.', reason: error?.message }), 0);
        }

        const contentType = response.headers?.get?.('content-type') || '';
        const payload = contentType.includes('application/json') ? await response.json() : await response.text();
        if (!response.ok) {
            throw new ApiError(normalizeError(payload, `Request failed (${response.status})`), response.status);
        }
        return payload;
    }

    get(path, options = {}) {
        return this.request(path, { ...options, method: 'GET' });
    }

    post(path, body, options = {}) {
        return this.request(path, { ...options, method: 'POST', body });
    }

    put(path, body, options = {}) {
        return this.request(path, { ...options, method: 'PUT', body });
    }

    delete(path, options = {}) {
        return this.request(path, { ...options, method: 'DELETE' });
    }

    async getWebSocketTicket() {
        const payload = await this.post('/api/auth/ws-ticket');
        if (!payload?.ticket) {
            throw new ApiError(normalizeError({ code: 'MISSING_WS_TICKET', message: 'The server did not provide a WebSocket ticket.' }), 502);
        }
        return payload.ticket;
    }

    async submitChat({ prompt, conversationId = null, branchId = 'main', backend = null, planOnly = false, taskId = null, signal } = {}) {
        return this.post('/api/chat', {
            prompt, conversation_id: conversationId, branch_id: branchId, backend, plan_only: planOnly, task_id: taskId,
        }, { signal });
    }
}

export { ApiClient, ApiError };
