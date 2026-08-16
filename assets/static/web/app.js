// web/app.js — BR JARVIS AI Operating System Client Engine v40.2.0
document.addEventListener('DOMContentLoaded', () => {
    const host = window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const API_BASE = `${protocol}://${host}`;

    // ── HELPER: Safe HTML escaping to prevent XSS ──
    function escapeHTML(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function debounce(func, delay = 250) {
        let timer = null;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => func.apply(this, args), delay);
        };
    }

    // ── AUTHENTICATION & API WRAPPER ──
    let isAuthRequired = false;
    let isAuthenticated = false;

    window.getServerApiKey = function () {
        return localStorage.getItem('jarvis_server_api_key') || localStorage.getItem('jarvis_api_key') || '';
    };

    window.setServerApiKey = function (key) {
        if (key) {
            localStorage.setItem('jarvis_server_api_key', key);
            localStorage.setItem('jarvis_api_key', key);
        } else {
            localStorage.removeItem('jarvis_server_api_key');
            localStorage.removeItem('jarvis_api_key');
        }
    };

    window.apiFetch = async function (url, options = {}) {
        const opts = Object.assign({}, options);
        opts.headers = Object.assign({}, opts.headers || {});
        opts.credentials = 'include';

        const apiKey = window.getServerApiKey();
        if (apiKey && !opts.headers['Authorization'] && !opts.headers['X-API-Key']) {
            opts.headers['Authorization'] = `Bearer ${apiKey}`;
            opts.headers['X-API-Key'] = apiKey;
        }

        try {
            const res = await fetch(url, opts);
            if (res.status === 401 && !url.includes('/api/auth/status') && !url.includes('/api/auth/login')) {
                isAuthenticated = false;
                window.showServerAuthModal();
            }
            return res;
        } catch (err) {
            console.debug('Network fetch error:', url, err);
            throw err;
        }
    };

    // ── SERVER AUTH MODAL ──
    window.showServerAuthModal = function () {
        const modal = document.getElementById('serverAuthModal');
        if (modal) {
            modal.style.display = 'flex';
            const input = document.getElementById('serverApiKeyInput');
            if (input) {
                input.value = window.getServerApiKey();
                setTimeout(() => input.focus(), 50);
            }
        }
    };

    window.closeServerAuthModal = function () {
        const modal = document.getElementById('serverAuthModal');
        if (modal) modal.style.display = 'none';
    };

    window.loginWithApiKey = async function (apiKey, showToast = true) {
        if (!apiKey) return false;
        try {
            const res = await fetch(`${API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ api_key: apiKey }),
                credentials: 'include',
            });
            if (res.ok) {
                isAuthenticated = true;
                window.setServerApiKey(apiKey);
                window.closeServerAuthModal();
                if (showToast) window.showToast('Authenticated', 'Server session established.', 'success');
                if (!socket || socket.readyState !== WebSocket.OPEN) {
                    initWebSocket();
                }
                fetchConnectorStatus();
                if (typeof window.fetchSkills === 'function') window.fetchSkills();
                if (typeof window.fetchConnectors === 'function') window.fetchConnectors();
                return true;
            } else {
                if (showToast) window.showToast('Auth Failed', 'Invalid Server API Key.', 'error');
                return false;
            }
        } catch (e) {
            console.error('Login error:', e);
            return false;
        }
    };

    window.submitServerAuth = function () {
        const input = document.getElementById('serverApiKeyInput');
        if (!input) return;
        const key = input.value.trim();
        if (key) {
            window.loginWithApiKey(key, true);
        }
    };

    async function checkAuthStatus() {
        try {
            const res = await fetch(`${API_BASE}/api/auth/status`, { credentials: 'include' });
            if (res.ok) {
                const data = await res.json();
                isAuthRequired = !!data.auth_required;
                isAuthenticated = !!data.authenticated;

                if (isAuthRequired && !isAuthenticated) {
                    const savedKey = window.getServerApiKey();
                    if (savedKey) {
                        const loggedIn = await window.loginWithApiKey(savedKey, false);
                        if (loggedIn) return;
                    }
                    window.showServerAuthModal();
                    return;
                }
            }
        } catch (e) {
            console.debug('Auth status check error:', e);
        }

        // Connect if authorized or not required
        initWebSocket();
        fetchConnectorStatus();
        if (typeof window.fetchSkills === 'function') window.fetchSkills();
        if (typeof window.fetchConnectors === 'function') window.fetchConnectors();
    }

    // ── DOM ELEMENTS ──
    const networkLatencyEl = document.getElementById('network-latency');
    const backendSelector = document.getElementById('backendSelector');
    const roleSelector = document.getElementById('roleSelector');
    const systemTimeEl = document.getElementById('system-time');

    const navItems = document.querySelectorAll('.nav-item');
    const viewContainers = document.querySelectorAll('.view-container');

    const chatWindow = document.getElementById('chatWindow');
    const chatInput = document.getElementById('chatInput');
    const sendChatBtn = document.getElementById('sendChatBtn');

    // Gauges
    const cpuRing = document.getElementById('cpu-ring');
    const ramRing = document.getElementById('ram-ring');
    const diskRing = document.getElementById('disk-ring');
    const cpuValue = document.getElementById('cpu-value');
    const ramValue = document.getElementById('ram-value');
    const diskValue = document.getElementById('disk-value');

    // Mobile Menu Toggle
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebarNav = document.getElementById('sidebarNav');
    if (mobileMenuToggle && sidebarNav) {
        mobileMenuToggle.addEventListener('click', () => {
            sidebarNav.classList.toggle('mobile-open');
        });
    }

    let socket = null;
    let heartbeatInterval = null;

    // ── ROLE & MODEL CHANGE NOTIFIERS ──
    if (roleSelector) {
        roleSelector.addEventListener('change', (e) => {
            window.showToast('Role Switched', `Persona set to '${escapeHTML(e.target.value.toUpperCase())}'`, 'info');
        });
    }

    if (backendSelector) {
        backendSelector.addEventListener('change', (e) => {
            const selectedText = e.target.options[e.target.selectedIndex].text;
            const backendVal = e.target.value;
            window.apiFetch(`${API_BASE}/api/backend/switch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ backend: backendVal })
            }).catch(() => {});
            window.showToast('Model Switched', `Active model set to '${escapeHTML(selectedText)}'`, 'info');
        });
    }

    // ── SYSTEM TIME & TELEMETRY ──
    function updateSystemTime() {
        if (systemTimeEl) {
            systemTimeEl.textContent = new Date().toLocaleTimeString();
        }
    }
    setInterval(updateSystemTime, 1000);
    updateSystemTime();

    function setGauge(ring, textEl, value) {
        if (!ring || !textEl) return;
        const val = Math.min(100, Math.max(0, parseFloat(value) || 0));
        const offset = 188.4 - (188.4 * val) / 100;
        ring.style.strokeDashoffset = offset;
        textEl.textContent = `${Math.round(val)}%`;
    }

    function fetchTelemetry() {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        const startTime = Date.now();

        window.apiFetch(`${API_BASE}/health`, { signal: controller.signal })
            .then(res => res.json())
            .then(data => {
                clearTimeout(timeoutId);
                const latency = Date.now() - startTime;
                if (networkLatencyEl) networkLatencyEl.textContent = `${latency}ms`;
                if (data.cpu_percent !== undefined) setGauge(cpuRing, cpuValue, data.cpu_percent);
                if (data.memory_percent !== undefined) setGauge(ramRing, ramValue, data.memory_percent);
                if (data.disk_percent !== undefined) setGauge(diskRing, diskValue, data.disk_percent);
            })
            .catch(() => clearTimeout(timeoutId));
    }

    // ── VIEW SWITCHER ──
    window.switchView = function (viewId) {
        navItems.forEach(item => {
            if (item.dataset.view === viewId) item.classList.add('active');
            else item.classList.remove('active');
        });
        viewContainers.forEach(container => {
            if (container.id === viewId) container.classList.add('active');
            else container.classList.remove('active');
        });

        if (sidebarNav && sidebarNav.classList.contains('mobile-open')) {
            sidebarNav.classList.remove('mobile-open');
        }

        if (viewId === 'contactsView') window.fetchContacts();
        if (viewId === 'connectorsView') window.fetchConnectors();
        if (viewId === 'skillsView') window.fetchSkills();
        if (viewId === 'knowledgeView') window.fetchMemories();
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewId = item.dataset.view;
            if (viewId) window.switchView(viewId);
        });
    });

    // ── TOAST NOTIFICATIONS ──
    window.showToast = function (title, message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const titleEl = document.createElement('div');
        titleEl.className = 'toast-title';
        titleEl.textContent = title;

        const msgEl = document.createElement('div');
        msgEl.className = 'toast-msg';
        msgEl.textContent = message;

        toast.appendChild(titleEl);
        toast.appendChild(msgEl);
        container.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    };

    // ── SECURE WEBSOCKET CONNECTION ENGINE (TICKET-BASED + HEARTBEAT) ──
    let wsReconnectDelay = 1000;
    let wsReconnectTimer = null;

    function _setWsStatus(connected) {
        document.querySelectorAll('.ws-status-dot').forEach(el => {
            el.style.background = connected ? 'var(--accent-green, #00dfa2)' : '#ff4444';
            el.title = connected ? 'WebSocket Connected' : 'WebSocket Disconnected — Reconnecting...';
        });
    }

    async function getWsTicket() {
        if (!isAuthenticated && !window.getServerApiKey()) {
            return '';
        }
        try {
            const res = await window.apiFetch(`${API_BASE}/api/auth/ws-ticket`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                return data.ticket;
            }
        } catch (e) {
            console.debug('Ticket fetch error, falling back:', e);
        }
        return '';
    }

    async function initWebSocket() {
        if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) return;
        const apiKey = window.getServerApiKey();

        if (isAuthRequired && !isAuthenticated && !apiKey) {
            window.showServerAuthModal();
            return;
        }

        try {
            const ticket = await getWsTicket();

            if (isAuthRequired && !ticket && !apiKey && !isAuthenticated) {
                window.showServerAuthModal();
                return;
            }

            let wsUrl = `${wsProtocol}://${host}/ws`;
            if (ticket) {
                wsUrl += `?ticket=${encodeURIComponent(ticket)}`;
            } else if (apiKey) {
                wsUrl += `?token=${encodeURIComponent(apiKey)}`;
            }

            socket = new WebSocket(wsUrl);


            socket.onopen = () => {
                wsReconnectDelay = 1000;
                _setWsStatus(true);
                window.showToast('Connected', 'JARVIS AI Core online.', 'success');
                fetchTelemetry();
                fetchConnectorStatus();

                if (heartbeatInterval) clearInterval(heartbeatInterval);
                heartbeatInterval = setInterval(() => {
                    if (socket && socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
                    }
                }, 25000);
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleServerMessage(data);
                } catch (e) {
                    console.log('WS Raw Message:', event.data);
                }
            };

            socket.onclose = (event) => {
                _setWsStatus(false);
                if (heartbeatInterval) clearInterval(heartbeatInterval);
                if (event.code === 4001) {
                    isAuthenticated = false;
                    window.showServerAuthModal();
                    return; // DO NOT retry in loop if unauthorized
                }
                if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
                wsReconnectTimer = setTimeout(() => initWebSocket(), wsReconnectDelay);
                wsReconnectDelay = Math.min(wsReconnectDelay * 2, 30000);
            };

            socket.onerror = (err) => {
                console.warn('WebSocket error:', err);
                _setWsStatus(false);
            };
        } catch (e) {
            console.error('WebSocket Init Error:', e);
        }
    }

    // ── CONNECTOR HUB STATUS ──
    function fetchConnectorStatus() {
        if (isAuthRequired && !isAuthenticated && !window.getServerApiKey()) return;
        window.apiFetch(`${API_BASE}/api/connectors`)
            .then(r => {
                if (r && r.ok) return r.json();
                return null;
            })
            .then(data => {
                if (!data || !data.connectors) return;
                renderConnectorPanel(data.connectors);
            })
            .catch(() => {});
    }

    function _getCleanConnectorName(c) {
        const id = (c.id || '').toLowerCase();
        if (id === 'calendar') return 'Calendar';
        if (id === 'gmail') return 'Gmail';
        if (id === 'telegram') return 'Telegram';
        if (id === 'web_search') return 'Search';
        if (id === 'weather') return 'Weather';
        if (id === 'wikipedia') return 'Wiki';
        if (id === 'rss_news') return 'News';
        if (id === 'github') return 'GitHub';
        if (id === 'notion') return 'Notion';
        if (id === 'slack') return 'Slack';
        if (id === 'mcp_proxy') return 'MCP';
        if (id === 'filesystem') return 'Files';
        if (id === 'youtube') return 'YouTube';
        return String(c.name || '').split(' ')[0];
    }

    function renderConnectorPanel(connectors) {
        const panel = document.getElementById('connectorPanel');
        if (!panel) return;
        panel.innerHTML = '';
        connectors.forEach(c => {
            const isConfigured = c.configured || c.status === 'CONNECTED';
            const badge = document.createElement('div');
            badge.className = `connector-badge ${isConfigured ? 'active' : ''}`;
            const toolCount = c.tools ? c.tools.length : 0;
            badge.title = `${c.name}: ${toolCount} tools active (${c.status || (isConfigured ? 'CONNECTED' : 'NOT_CONFIGURED')})`;
            badge.onclick = () => window.switchView('connectorsView');

            const iconSpan = document.createElement('span');
            iconSpan.className = 'connector-icon';
            iconSpan.textContent = c.icon || '🔌';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'connector-name';
            nameSpan.textContent = _getCleanConnectorName(c);

            const dotSpan = document.createElement('span');
            dotSpan.className = `connector-dot ${isConfigured ? 'green' : 'grey'}`;

            badge.appendChild(iconSpan);
            badge.appendChild(nameSpan);
            badge.appendChild(dotSpan);
            panel.appendChild(badge);
        });
    }

    setInterval(fetchConnectorStatus, 30000);

    // ── CHAT STREAMING & MESSAGING ──
    let currentStreamBubble = null;
    let currentStreamBody = null;
    let currentStreamText = '';

    function appendChatStreamChunk(chunk) {
        if (!chatWindow || !chunk) return;
        if (!currentStreamBubble) {
            currentStreamBubble = document.createElement('div');
            currentStreamBubble.className = 'msg-bubble system streaming';

            const authorEl = document.createElement('div');
            authorEl.className = 'msg-author';
            authorEl.textContent = 'JARVIS';

            currentStreamBody = document.createElement('div');
            currentStreamBody.className = 'msg-body';

            currentStreamBubble.appendChild(authorEl);
            currentStreamBubble.appendChild(currentStreamBody);
            chatWindow.appendChild(currentStreamBubble);
            currentStreamText = '';
        }
        currentStreamText += chunk;
        if (currentStreamBody) {
            currentStreamBody.innerHTML = formatMarkdown(currentStreamText);
        }
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    function finalizeChatStream() {
        if (currentStreamBubble) {
            currentStreamBubble.classList.remove('streaming');
            currentStreamBubble = null;
            currentStreamBody = null;
            currentStreamText = '';
        }
    }

    function handleServerMessage(data) {
        if (data.type === 'telemetry') {
            if (data.cpu !== undefined) setGauge(cpuRing, cpuValue, data.cpu);
            if (data.ram !== undefined) setGauge(ramRing, ramValue, data.ram);
            if (data.disk !== undefined) setGauge(diskRing, diskValue, data.disk);
        } else if (data.type === 'stream_start') {
            finalizeChatStream();
        } else if (data.type === 'stream_chunk' || data.type === 'token') {
            appendChatStreamChunk(data.text || data.chunk || data.token || '');
        } else if (data.type === 'stream_end') {
            finalizeChatStream();
        } else if (data.type === 'chat_response' || data.type === 'response') {
            finalizeChatStream();
            appendChatMessage('JARVIS', data.response || data.message || data.text || '', 'system');
        } else if (data.type === 'agent_task_update' || data.type === 'task_update') {
            updateWebTaskCard(data.task_id || data.id, data.name || data.task_name, data.status, data.progress, data.result);
        } else if (data.type === 'agent_task_remove' || data.type === 'task_remove') {
            removeWebTaskCard(data.task_id || data.id);
        }
    }

    function updateWebTaskCard(taskId, name, status, progress, result) {
        const container = document.getElementById('subAgentCardsContainer');
        if (!container) return;
        const idleMsg = container.querySelector('.subagent-idle-msg');
        if (idleMsg) idleMsg.remove();

        let card = document.getElementById(`task-card-${taskId}`);
        if (!card) {
            card = document.createElement('div');
            card.id = `task-card-${taskId}`;
            card.className = 'connector-card';
            card.style.padding = '8px 12px';
            container.appendChild(card);
        }
        const st = (status || 'running').toUpperCase();
        const pct = Math.min(100, Math.max(0, Math.round((progress || 0) * 100)));

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; font-family: var(--font-code);">
                <span style="color: var(--accent-cyan);">🤖 ${escapeHTML(name || taskId)}</span>
                <span style="color: ${st === 'COMPLETED' ? 'var(--accent-green)' : 'var(--accent-amber)'};">${escapeHTML(st)}</span>
            </div>
            <div style="background: rgba(255,255,255,0.1); height: 4px; border-radius: 2px; margin-top: 6px; overflow: hidden;">
                <div style="background: var(--accent-cyan); width: ${pct}%; height: 100%; transition: width 0.3s ease;"></div>
            </div>
        `;
    }

    function removeWebTaskCard(taskId) {
        const card = document.getElementById(`task-card-${taskId}`);
        if (card) card.remove();
        const container = document.getElementById('subAgentCardsContainer');
        if (container && container.children.length === 0) {
            container.innerHTML = '<div class="subagent-idle-msg">No active background sub-agents</div>';
        }
    }

    function transmitChat() {
        if (!chatInput) return;
        const text = chatInput.value.trim();
        if (!text) return;

        appendChatMessage('User', text, 'user');
        chatInput.value = '';

        const activeBackend = backendSelector ? backendSelector.value : 'gemini';
        const activeRole = roleSelector ? roleSelector.value : 'general';

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: 'chat_prompt',
                prompt: text,
                backend: activeBackend,
                role: activeRole
            }));
        } else {
            window.apiFetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, backend: activeBackend, role: activeRole })
            })
            .then(res => res.json())
            .then(data => {
                appendChatMessage('JARVIS', data.response || data.result || 'Done.', 'system');
            })
            .catch(err => {
                appendChatMessage('JARVIS', `Error communicating with JARVIS Core: ${err}`, 'system');
            });
        }
    }

    if (sendChatBtn) sendChatBtn.addEventListener('click', transmitChat);
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') transmitChat();
        });
    }

    function appendChatMessage(author, text, type) {
        if (!chatWindow) return;
        const bubble = document.createElement('div');
        bubble.className = `msg-bubble ${type}`;

        const authorEl = document.createElement('div');
        authorEl.className = 'msg-author';
        authorEl.textContent = author;

        const bodyEl = document.createElement('div');
        bodyEl.className = 'msg-body';
        bodyEl.innerHTML = formatMarkdown(text);

        bubble.appendChild(authorEl);
        bubble.appendChild(bodyEl);
        chatWindow.appendChild(bubble);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    window.copyCodeToClipboard = function (btn) {
        const codeEl = btn.parentElement ? btn.parentElement.querySelector('code') : null;
        if (codeEl) {
            navigator.clipboard.writeText(codeEl.innerText)
                .then(() => window.showToast('Copied', 'Code copied to clipboard.', 'success'))
                .catch(() => window.showToast('Copy Failed', 'Could not copy code.', 'error'));
        }
    };

    // ── ROBUST MARKDOWN FORMATTING ──
    function formatMarkdown(text) {
        if (!text) return '';
        const codeBlocks = [];

        // 1. Extract code blocks safely
        let formatted = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
            const placeholder = `__CODE_BLOCK_${codeBlocks.length}__`;
            const escapedCode = escapeHTML(code);
            codeBlocks.push(
                `<div class="code-block"><button class="code-copy-btn" onclick="copyCodeToClipboard(this)">📋 Copy</button><pre><code class="${lang}">${escapedCode}</code></pre></div>`
            );
            return placeholder;
        });

        // 2. Escape non-code HTML
        formatted = escapeHTML(formatted);

        // 3. Format inline elements
        formatted = formatted
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*([^*]+)\*/g, '<em>$1</em>')
            .replace(/^### (.*$)/gim, '<h3 style="color: var(--accent-cyan); margin: 8px 0 4px;">$1</h3>')
            .replace(/^## (.*$)/gim, '<h2 style="color: var(--accent-cyan); margin: 10px 0 6px;">$1</h2>')
            .replace(/^# (.*$)/gim, '<h1 style="color: var(--accent-cyan); margin: 12px 0 8px;">$1</h1>')
            .replace(/\n/g, '<br>');

        // 4. Restore code blocks without injected <br>
        codeBlocks.forEach((block, idx) => {
            formatted = formatted.replace(`__CODE_BLOCK_${idx}__`, block);
        });

        return formatted;
    }

    // ── COMMAND PALETTE (Ctrl+K) ──
    const cmdPaletteModal = document.getElementById('cmdPaletteModal');
    const cmdPaletteTrigger = document.getElementById('cmdPaletteTrigger');
    const cmdPaletteInput = document.getElementById('cmdPaletteInput');
    const cmdPaletteResults = document.getElementById('cmdPaletteResults');

    window.openCommandPalette = function () {
        if (cmdPaletteModal) {
            cmdPaletteModal.classList.add('active');
            if (cmdPaletteInput) {
                cmdPaletteInput.value = '';
                cmdPaletteInput.focus();
                renderCmdResults('');
            }
        }
    };

    window.closeCommandPalette = function () {
        if (cmdPaletteModal) cmdPaletteModal.classList.remove('active');
    };

    if (cmdPaletteTrigger) cmdPaletteTrigger.addEventListener('click', window.openCommandPalette);

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            window.openCommandPalette();
        }
        if (e.key === 'Escape') {
            window.closeCommandPalette();
            window.closeGoogleAuthModal();
            window.closeContactImportModal();
            window.closeAddContactModal();
            window.closeConnectorConfigModal();
        }
    });

    if (cmdPaletteInput) {
        cmdPaletteInput.addEventListener('input', (e) => renderCmdResults(e.target.value.trim()));
    }

    function renderCmdResults(query) {
        if (!cmdPaletteResults) return;
        const q = query.toLowerCase();
        const items = [
            { label: '🏠 Switch to Dashboard', action: () => window.switchView('dashboardView') },
            { label: '💬 Open Dialogue Workspace', action: () => window.switchView('chatView') },
            { label: '🎙️ Open Hands-Free Voice', action: () => window.switchView('voiceView') },
            { label: '🔗 Open App Connectors Hub', action: () => window.switchView('connectorsView') },
            { label: '📱 Open Contacts Store', action: () => window.switchView('contactsView') },
            { label: '⚡ Open Skills Library', action: () => window.switchView('skillsView') },
            { label: '🧠 Open Knowledge Base & RAG', action: () => window.switchView('knowledgeView') },
            { label: '🌌 Open 3D Knowledge Galaxy', action: () => window.open('/web/galaxy.html', '_blank') },
            { label: '🔑 Open Google Auth Modal', action: () => window.openGoogleAuthModal() },
            { label: '👤 Add New Contact', action: () => window.openAddContactModal() }
        ];

        const filtered = query ? items.filter(i => i.label.toLowerCase().includes(q)) : items;
        cmdPaletteResults.innerHTML = '';
        filtered.forEach(item => {
            const div = document.createElement('div');
            div.className = 'cmd-item';
            div.textContent = item.label;
            div.onclick = () => {
                item.action();
                window.closeCommandPalette();
            };
            cmdPaletteResults.appendChild(div);
        });
    }

    // ── CONNECTORS & SKILLS LOADERS ──
    let allConnectors = [];
    let currentConnectorCategory = 'all';
    let currentConnectorQuery = '';

    window.runConnectorAction = function (name, toolName = '') {
        window.switchView('chatView');
        if (!chatInput) return;
        const n = String(name || '').toLowerCase();

        let promptText = '';
        if (toolName) {
            promptText = `Use ${name} tool '${toolName}' to `;
        } else if (n.includes('gmail') || n.includes('email')) {
            promptText = 'Read my recent unread emails and summarize them';
        } else if (n.includes('github')) {
            promptText = 'Check the latest status of my GitHub repositories';
        } else if (n.includes('telegram')) {
            promptText = 'Send a test notification message to my Telegram';
        } else if (n.includes('notion')) {
            promptText = 'Search my Notion workspace for recent notes';
        } else if (n.includes('calendar')) {
            promptText = 'List my upcoming calendar events for this week';
        } else if (n.includes('whatsapp')) {
            promptText = 'Send a WhatsApp message to ';
        } else if (n.includes('wikipedia')) {
            promptText = 'Look up Wikipedia article on ';
        } else if (n.includes('youtube')) {
            promptText = 'Search YouTube for ';
        } else if (n.includes('weather')) {
            promptText = 'What is the current weather forecast?';
        } else if (n.includes('rss') || n.includes('news')) {
            promptText = 'Get the latest tech news headlines from RSS feeds';
        } else if (n.includes('search')) {
            promptText = 'Search the web for ';
        } else if (n.includes('filesystem')) {
            promptText = 'List the files in the workspace directory';
        } else {
            promptText = `Run action on ${name} `;
        }

        chatInput.value = promptText;
        chatInput.focus();
        window.showToast('Connector Prompt Loaded', `Prepared prompt for ${name}. Press Enter or customize.`, 'info');
    };

    window.openMcpServerModal = function () {
        const modal = document.getElementById('mcpServerModal');
        const urlInput = document.getElementById('mcpServerUrlInput');
        const nameInput = document.getElementById('mcpServerNameInput');
        const tokenInput = document.getElementById('mcpServerTokenInput');
        if (urlInput) urlInput.value = 'http://localhost:3000';
        if (nameInput) nameInput.value = '';
        if (tokenInput) tokenInput.value = '';
        if (modal) modal.style.display = 'flex';
    };

    window.closeMcpServerModal = function () {
        const modal = document.getElementById('mcpServerModal');
        if (modal) modal.style.display = 'none';
    };

    window.submitAddMcpServer = function () {
        const url = (document.getElementById('mcpServerUrlInput') || {}).value || '';
        const name = (document.getElementById('mcpServerNameInput') || {}).value || '';
        const token = (document.getElementById('mcpServerTokenInput') || {}).value || '';
        if (!url.trim()) {
            window.showToast('URL Required', 'Please enter an MCP server URL (e.g. http://localhost:3000).', 'error');
            return;
        }

        window.apiFetch(`${API_BASE}/api/connector/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                connector: 'mcp_proxy',
                tool: 'add_server',
                params: { url: url.trim(), name: name.trim(), api_key: token.trim() }
            })
        })
        .then(res => res.json())
        .then(data => {
            window.showToast('MCP Server Added', data.result || `Registered server at ${url}`, 'success');
            window.closeMcpServerModal();
            window.fetchConnectors();
        })
        .catch(err => window.showToast('Error', `Failed to connect MCP server: ${err}`, 'error'));
    };

    window.openConnectorConfigModal = function (name, authHint = '') {
        const modal = document.getElementById('connectorConfigModal');
        const title = document.getElementById('configModalTitle');
        const inputHidden = document.getElementById('configConnectorName');
        const apiKeyInput = document.getElementById('configApiKeyInput');
        if (title) title.textContent = `🔑 Configure ${name}`;
        if (inputHidden) inputHidden.value = name;
        if (apiKeyInput) apiKeyInput.value = '';
        if (modal) modal.style.display = 'flex';
        if (authHint) {
            window.showToast('Setup Guide', authHint, 'info');
        }
    };

    window.closeConnectorConfigModal = function () {
        const modal = document.getElementById('connectorConfigModal');
        if (modal) modal.style.display = 'none';
    };

    window.submitConnectorConfig = function () {
        const name = (document.getElementById('configConnectorName') || {}).value || '';
        const key = (document.getElementById('configApiKeyInput') || {}).value || '';
        if (!key.trim()) {
            window.showToast('Key Required', 'Please paste a valid API key or token.', 'error');
            return;
        }
        window.apiFetch(`${API_BASE}/api/connector/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ connector: name, api_key: key.trim() })
        })
        .then(res => res.json())
        .then(data => {
            window.showToast('Key Saved', data.message || `Saved API Key for ${name}`, 'success');
            window.closeConnectorConfigModal();
            window.fetchConnectors();
        })
        .catch(err => window.showToast('Error', `Failed saving key: ${err}`, 'error'));
    };

    window.testConnector = function (connectorId, btnElement) {
        const originalText = btnElement ? btnElement.innerHTML : '';
        if (btnElement) {
            btnElement.innerHTML = '⏳ Testing...';
            btnElement.disabled = true;
        }

        window.apiFetch(`${API_BASE}/api/connector/test`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ connector: connectorId })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                window.showToast('✅ Connection Verified', `${data.display_name}: Verified in ${data.latency_ms}ms`, 'success');
                if (btnElement) {
                    btnElement.innerHTML = `✅ ${data.latency_ms}ms`;
                    btnElement.style.borderColor = 'var(--accent-green)';
                    btnElement.style.color = 'var(--accent-green)';
                }
            } else {
                window.showToast('⚠️ Health Degraded', data.message || 'Connection check failed.', 'error');
                if (btnElement) {
                    btnElement.innerHTML = '❌ Degraded';
                    btnElement.style.borderColor = 'var(--accent-amber)';
                }
            }
        })
        .catch(err => {
            window.showToast('Test Failed', `Error: ${err.message || err}`, 'error');
            if (btnElement) btnElement.innerHTML = '❌ Error';
        })
        .finally(() => {
            setTimeout(() => {
                if (btnElement) {
                    btnElement.innerHTML = originalText;
                    btnElement.disabled = false;
                    btnElement.style.borderColor = '';
                    btnElement.style.color = '';
                }
            }, 4000);
        });
    };

    window.fetchConnectors = function () {
        window.apiFetch(`${API_BASE}/api/connectors`)
            .then(res => res.json())
            .then(data => {
                allConnectors = Array.isArray(data.connectors) ? data.connectors : [];
                renderConnectors(allConnectors, currentConnectorQuery, currentConnectorCategory);
            })
            .catch(() => {});
    };

    function renderConnectors(connectors, query = '', category = 'all') {
        const grid = document.getElementById('connectorsGrid');
        if (!grid) return;

        let filtered = connectors;

        // Category filtering
        if (category === 'active') {
            filtered = filtered.filter(c => c.configured);
        } else if (category === 'zero_auth') {
            filtered = filtered.filter(c => !c.requires_auth);
        } else if (category !== 'all') {
            filtered = filtered.filter(c => c.category === category);
        }

        // Text query filtering
        if (query) {
            const q = query.toLowerCase();
            filtered = filtered.filter(c =>
                (c.name && c.name.toLowerCase().includes(q)) ||
                (c.desc && c.desc.toLowerCase().includes(q)) ||
                (c.id && c.id.toLowerCase().includes(q)) ||
                (c.tools && c.tools.some(t => t.toLowerCase().includes(q)))
            );
        }

        // Update live counters
        const activeCount = connectors.filter(c => c.configured).length;
        const activeSpan = document.getElementById('activeConnectorsCount');
        const totalSpan = document.getElementById('totalConnectorsCount');
        if (activeSpan) activeSpan.textContent = String(activeCount);
        if (totalSpan) totalSpan.textContent = String(connectors.length);

        grid.innerHTML = '';
        if (filtered.length === 0) {
            const empty = document.createElement('div');
            empty.style.cssText = "grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px; font-size: 0.9rem;";
            empty.textContent = 'No matching connectors found. Try a different filter or search term.';
            grid.appendChild(empty);
            return;
        }

        filtered.forEach(c => {
            const isConnected = c.configured;
            const card = document.createElement('div');
            card.className = `connector-card ${isConnected ? 'active-connected' : ''}`;

            // Top Header: Icon + Category + Status Badge
            const topRow = document.createElement('div');
            topRow.style.cssText = "display: flex; align-items: center; justify-content: space-between;";
            
            const leftMeta = document.createElement('div');
            leftMeta.style.cssText = "display: flex; align-items: center; gap: 10px;";
            const iconSpan = document.createElement('span');
            iconSpan.style.fontSize = '26px';
            iconSpan.textContent = c.icon || '🔌';
            
            const catBadge = document.createElement('span');
            catBadge.style.cssText = "font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px;";
            catBadge.textContent = c.category || 'General';
            leftMeta.appendChild(iconSpan);
            leftMeta.appendChild(catBadge);

            const badgeSpan = document.createElement('span');
            badgeSpan.className = 'os-badge';
            if (isConnected) {
                badgeSpan.style.cssText = "background: rgba(0, 223, 162, 0.15); color: var(--accent-green); border-color: rgba(0, 223, 162, 0.4);";
                badgeSpan.textContent = '● ACTIVE';
            } else if (!c.requires_auth) {
                badgeSpan.style.cssText = "background: rgba(0, 242, 254, 0.12); color: var(--accent-cyan); border-color: rgba(0, 242, 254, 0.3);";
                badgeSpan.textContent = '✨ ZERO-SETUP';
            } else {
                badgeSpan.style.cssText = "background: rgba(255, 183, 3, 0.12); color: var(--accent-amber); border-color: rgba(255, 183, 3, 0.3);";
                badgeSpan.textContent = '○ NEEDS KEY';
            }

            topRow.appendChild(leftMeta);
            topRow.appendChild(badgeSpan);

            // Middle: Name & Description
            const midDiv = document.createElement('div');
            const titleH4 = document.createElement('h4');
            titleH4.style.cssText = "color: #fff; font-family: var(--font-heading); margin: 6px 0 4px; font-size: 1.02rem;";
            titleH4.textContent = c.name;

            const descP = document.createElement('p');
            descP.style.cssText = "font-size: 0.78rem; color: var(--text-secondary); line-height: 1.4; margin: 0 0 8px;";
            descP.textContent = c.desc || '';
            midDiv.appendChild(titleH4);
            midDiv.appendChild(descP);

            // Tools Chips Drawer (if tools available)
            if (c.tools && c.tools.length > 0) {
                const toolsTitle = document.createElement('div');
                toolsTitle.style.cssText = "font-size: 0.7rem; color: var(--text-muted); margin-top: 6px; font-weight: 600;";
                toolsTitle.textContent = `TOOLS (${c.tools.length}):`;
                midDiv.appendChild(toolsTitle);

                const chipsDiv = document.createElement('div');
                chipsDiv.className = 'tool-chips-container';
                c.tools.slice(0, 5).forEach(t => {
                    const chip = document.createElement('span');
                    chip.className = 'tool-chip';
                    chip.textContent = t;
                    chip.title = `Click to run tool '${t}'`;
                    chip.onclick = (e) => {
                        e.stopPropagation();
                        window.runConnectorAction(c.name, t);
                    };
                    chipsDiv.appendChild(chip);
                });
                if (c.tools.length > 5) {
                    const moreChip = document.createElement('span');
                    moreChip.className = 'tool-chip';
                    moreChip.style.color = 'var(--text-muted)';
                    moreChip.textContent = `+${c.tools.length - 5} more`;
                    chipsDiv.appendChild(moreChip);
                }
                midDiv.appendChild(chipsDiv);
            }

            // Bottom Actions Row: Run Action + Test Ping + Config (if auth required or MCP)
            const actDiv = document.createElement('div');
            actDiv.style.cssText = "display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.05);";

            const actBtn = document.createElement('button');
            actBtn.className = 'btn btn-secondary';
            actBtn.style.cssText = "padding: 6px 12px; font-size: 0.75rem;";
            actBtn.textContent = '⚡ Run Action';
            actBtn.onclick = () => window.runConnectorAction(c.name);
            actDiv.appendChild(actBtn);

            const testBtn = document.createElement('button');
            testBtn.className = 'btn btn-secondary';
            testBtn.style.cssText = "padding: 6px 10px; font-size: 0.75rem;";
            testBtn.textContent = '🧪 Test';
            testBtn.title = 'Test connection latency & live health';
            testBtn.onclick = () => window.testConnector(c.id || c.name, testBtn);
            actDiv.appendChild(testBtn);

            if (c.id === 'mcp_proxy') {
                const mcpBtn = document.createElement('button');
                mcpBtn.className = 'btn btn-secondary';
                mcpBtn.style.cssText = "padding: 6px 10px; font-size: 0.75rem; color: var(--accent-cyan); border-color: rgba(0, 242, 254, 0.3);";
                mcpBtn.textContent = '+ Add Server';
                mcpBtn.title = 'Connect an MCP tool server';
                mcpBtn.onclick = () => window.openMcpServerModal();
                actDiv.appendChild(mcpBtn);
            } else if (c.requires_auth) {
                const cfgBtn = document.createElement('button');
                cfgBtn.className = 'btn btn-secondary';
                cfgBtn.style.cssText = "padding: 6px 10px; font-size: 0.75rem;";
                cfgBtn.textContent = '⚙ Key';
                cfgBtn.title = 'Configure API Key';
                cfgBtn.onclick = () => window.openConnectorConfigModal(c.name, c.auth_hint);
                actDiv.appendChild(cfgBtn);
            }

            card.appendChild(topRow);
            card.appendChild(midDiv);
            card.appendChild(actDiv);
            grid.appendChild(card);
        });
    }

    // Attach search and filter pill handlers on DOM load
    const connectorSearchEl = document.getElementById('connectorSearchInput');
    if (connectorSearchEl) {
        connectorSearchEl.addEventListener('input', (e) => {
            currentConnectorQuery = e.target.value.trim();
            renderConnectors(allConnectors, currentConnectorQuery, currentConnectorCategory);
        });
    }

    const pillContainer = document.getElementById('connectorCategoryPills');
    if (pillContainer) {
        pillContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('filter-pill')) {
                pillContainer.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
                e.target.classList.add('active');
                currentConnectorCategory = e.target.getAttribute('data-category') || 'all';
                renderConnectors(allConnectors, currentConnectorQuery, currentConnectorCategory);
            }
        });
    }


    let allSkills = [];
    window.fetchSkills = function (query = '') {
        window.apiFetch(`${API_BASE}/api/skills`)
            .then(res => res.json())
            .then(skills => {
                allSkills = Array.isArray(skills) ? skills : [];
                renderSkills(allSkills, query);
            })
            .catch(() => {});
    };

    function renderSkills(skills, query = '') {
        const grid = document.getElementById('skillsGrid');
        if (!grid) return;
        let filtered = skills;
        if (query) {
            const q = query.toLowerCase();
            filtered = skills.filter(s => (s.name && s.name.toLowerCase().includes(q)) || (s.description && s.description.toLowerCase().includes(q)));
        }
        grid.innerHTML = '';
        if (filtered.length === 0) {
            const empty = document.createElement('div');
            empty.style.cssText = "grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;";
            empty.textContent = 'No matching skills found.';
            grid.appendChild(empty);
            return;
        }
        filtered.forEach(s => {
            const card = document.createElement('div');
            card.className = 'skill-card';

            const topRow = document.createElement('div');
            topRow.style.cssText = "display: flex; align-items: center; justify-content: space-between;";
            const nameH4 = document.createElement('h4');
            nameH4.style.cssText = "margin: 0; color: var(--accent-cyan); font-family: var(--font-code); font-size: 14px;";
            nameH4.textContent = `⚡ /${s.name}`;
            const typeBadge = document.createElement('span');
            typeBadge.className = 'os-badge';
            typeBadge.textContent = 'Built-in';
            topRow.appendChild(nameH4);
            topRow.appendChild(typeBadge);

            const descP = document.createElement('p');
            descP.style.cssText = "font-size: 11px; color: var(--text-secondary); flex: 1;";
            descP.textContent = s.description || '';

            const runBtn = document.createElement('button');
            runBtn.className = 'btn btn-secondary';
            runBtn.style.width = '100%';
            runBtn.textContent = '⚡ Run Skill';
            runBtn.onclick = () => window.runSkill(s.name);

            card.appendChild(topRow);
            card.appendChild(descP);
            card.appendChild(runBtn);
            grid.appendChild(card);
        });
    }

    window.runSkill = function (skillName) {
        window.switchView('chatView');
        if (chatInput) {
            chatInput.value = `/${skillName} `;
            chatInput.focus();
            window.showToast('Skill Selected', `Populated '/${skillName}'. Add parameters if required, then press Enter.`, 'info');
        }
    };

    const skillSearchInput = document.getElementById('skillSearchInput');
    if (skillSearchInput) {
        skillSearchInput.addEventListener('input', debounce((e) => renderSkills(allSkills, e.target.value.trim()), 200));
    }

    // ── CONTACTS HUB ──
    window.fetchContacts = function (query = '') {
        const url = query ? `${API_BASE}/api/contacts?query=${encodeURIComponent(query)}` : `${API_BASE}/api/contacts`;
        window.apiFetch(url)
            .then(res => res.json())
            .then(data => renderContacts(data.contacts || []))
            .catch(() => {});
    };

    function renderContacts(list) {
        const grid = document.getElementById('contactsGrid');
        if (!grid) return;
        grid.innerHTML = '';
        if (!list || list.length === 0) {
            const empty = document.createElement('div');
            empty.style.cssText = "grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px; font-size: 0.9rem;";
            empty.textContent = 'No saved contacts found. Import .vcf/.csv or click + Add Contact.';
            grid.appendChild(empty);
            return;
        }
        list.slice(0, 80).forEach(c => {
            const card = document.createElement('div');
            card.className = 'contact-card';

            const topRow = document.createElement('div');
            topRow.style.cssText = "display: flex; align-items: center; justify-content: space-between;";

            const leftGroup = document.createElement('div');
            leftGroup.style.cssText = "display: flex; align-items: center; gap: 10px;";

            const avatar = document.createElement('div');
            avatar.style.cssText = "width: 38px; height: 38px; border-radius: 50%; background: linear-gradient(135deg, var(--accent-purple), var(--accent-cyan)); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 15px;";
            avatar.textContent = (c.name || '?')[0].toUpperCase();

            const info = document.createElement('div');
            const nameEl = document.createElement('div');
            nameEl.style.cssText = "color: #fff; font-weight: 600; font-size: 14px;";
            nameEl.textContent = c.name;
            const subEl = document.createElement('div');
            subEl.style.cssText = "font-size: 11px; color: var(--text-muted);";
            subEl.textContent = c.phone_number || c.email || (c.aliases ? c.aliases.join(', ') : 'No details');

            info.appendChild(nameEl);
            info.appendChild(subEl);
            leftGroup.appendChild(avatar);
            leftGroup.appendChild(info);
            topRow.appendChild(leftGroup);

            // Action Buttons
            const actRow = document.createElement('div');
            actRow.style.cssText = "display: flex; gap: 6px; margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.05);";

            const msgBtn = document.createElement('button');
            msgBtn.className = 'btn btn-secondary';
            msgBtn.style.cssText = "padding: 4px 10px; font-size: 0.72rem; flex: 1;";
            msgBtn.textContent = '💬 Message';
            msgBtn.onclick = () => {
                window.switchView('chatView');
                if (chatInput) {
                    chatInput.value = `Send a message to ${c.name}: `;
                    chatInput.focus();
                }
            };
            actRow.appendChild(msgBtn);

            if (c.email) {
                const emailBtn = document.createElement('button');
                emailBtn.className = 'btn btn-secondary';
                emailBtn.style.cssText = "padding: 4px 10px; font-size: 0.72rem; flex: 1;";
                emailBtn.textContent = '📧 Email';
                emailBtn.onclick = () => {
                    window.switchView('chatView');
                    if (chatInput) {
                        chatInput.value = `Send an email to ${c.name} (${c.email}) about `;
                        chatInput.focus();
                    }
                };
                actRow.appendChild(emailBtn);
            }

            card.appendChild(topRow);
            card.appendChild(actRow);
            grid.appendChild(card);
        });
    }

    const contactSearchInput = document.getElementById('contactSearchInput');
    if (contactSearchInput) {
        contactSearchInput.addEventListener('input', debounce((e) => window.fetchContacts(e.target.value.trim()), 200));
    }

    // ── FILE IMPORT & RAG MEMORY ──
    let allMemories = [];
    const fileImportInput = document.getElementById('fileImportInput');
    const knowledgeDropZone = document.getElementById('knowledgeDropZone');

    window.triggerFileImport = function () {
        if (fileImportInput) {
            fileImportInput.value = '';
            fileImportInput.click();
        }
    };

    if (knowledgeDropZone) {
        knowledgeDropZone.addEventListener('click', window.triggerFileImport);
        knowledgeDropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            knowledgeDropZone.classList.add('dragover');
        });
        knowledgeDropZone.addEventListener('dragleave', () => knowledgeDropZone.classList.remove('dragover'));
        knowledgeDropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            knowledgeDropZone.classList.remove('dragover');
            if (e.dataTransfer && e.dataTransfer.files) {
                window.uploadKnowledgeFiles(e.dataTransfer.files);
            }
        });
    }

    if (fileImportInput) {
        fileImportInput.addEventListener('change', (e) => {
            if (e.target.files) window.uploadKnowledgeFiles(e.target.files);
        });
    }

    window.uploadKnowledgeFiles = function (files) {
        if (!files || !files.length) return;
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);
            window.showToast('Uploading', `Ingesting '${file.name}' into RAG memory...`, 'info');
            window.apiFetch(`${API_BASE}/api/import/file`, { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => {
                    window.showToast('Success', data.message || `File '${file.name}' ingested.`, 'success');
                    window.fetchMemories();
                })
                .catch(err => window.showToast('Error', `Failed uploading ${file.name}`, 'error'));
        }
    };

    window.fetchMemories = function (query = '') {
        Promise.all([
            window.apiFetch(`${API_BASE}/api/memory`).then(r => r.ok ? r.json() : { memories: [] }),
            window.apiFetch(`${API_BASE}/api/galaxy/data`).then(r => r.ok ? r.json() : { nodes: [] })
        ])
        .then(([memData, galaxyData]) => {
            allMemories = Array.isArray(memData.memories) ? memData.memories : [];
            const nodes = Array.isArray(galaxyData.nodes) ? galaxyData.nodes : [];

            const memCountSpan = document.getElementById('memoryCountBadge');
            const galaxyCountSpan = document.getElementById('galaxyNodesBadge');
            if (memCountSpan) memCountSpan.textContent = String(allMemories.length);
            if (galaxyCountSpan) galaxyCountSpan.textContent = String(nodes.length);

            renderMemories(allMemories, query);
        })
        .catch(() => {});
    };

    function renderMemories(memories, query = '') {
        const grid = document.getElementById('memoriesGrid');
        if (!grid) return;
        let filtered = memories;
        if (query) {
            const q = query.toLowerCase();
            filtered = memories.filter(m =>
                (m.name && m.name.toLowerCase().includes(q)) ||
                (m.description && m.description.toLowerCase().includes(q)) ||
                (m.content && m.content.toLowerCase().includes(q))
            );
        }
        grid.innerHTML = '';
        if (filtered.length === 0) {
            const empty = document.createElement('div');
            empty.style.cssText = "grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 30px; font-size: 0.88rem;";
            empty.textContent = query ? 'No matching memory notes found.' : 'No persistent memory notes recorded yet. Say "Remember that..." in chat to save.';
            grid.appendChild(empty);
            return;
        }

        filtered.forEach(m => {
            const card = document.createElement('div');
            card.className = 'connector-card';

            const topRow = document.createElement('div');
            topRow.style.cssText = "display: flex; align-items: center; justify-content: space-between;";

            const typeBadge = document.createElement('span');
            typeBadge.className = 'os-badge';
            typeBadge.style.cssText = "background: rgba(0, 242, 254, 0.1); color: var(--accent-cyan); border-color: rgba(0, 242, 254, 0.3); font-size: 0.7rem;";
            typeBadge.textContent = (m.type || 'NOTE').toUpperCase();

            const dateSpan = document.createElement('span');
            dateSpan.style.cssText = "font-size: 0.72rem; color: var(--text-muted);";
            dateSpan.textContent = m.created || '';
            topRow.appendChild(typeBadge);
            topRow.appendChild(dateSpan);

            const titleH4 = document.createElement('h4');
            titleH4.style.cssText = "color: #fff; font-family: var(--font-heading); margin: 6px 0 2px; font-size: 0.95rem;";
            titleH4.textContent = m.name;

            const descP = document.createElement('p');
            descP.style.cssText = "font-size: 0.75rem; color: var(--text-secondary); line-height: 1.4; margin: 0 0 6px;";
            descP.textContent = m.description || m.content || '';

            const actRow = document.createElement('div');
            actRow.style.cssText = "display: flex; justify-content: flex-end; gap: 6px; margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255, 255, 255, 0.05);";

            const delBtn = document.createElement('button');
            delBtn.className = 'btn btn-secondary';
            delBtn.style.cssText = "padding: 3px 8px; font-size: 0.7rem; color: var(--accent-red);";
            delBtn.textContent = '🗑️ Delete';
            delBtn.onclick = () => window.deleteMemoryEntry(m.name, m.scope);
            actRow.appendChild(delBtn);

            card.appendChild(topRow);
            card.appendChild(titleH4);
            card.appendChild(descP);
            card.appendChild(actRow);
            grid.appendChild(card);
        });
    }

    window.deleteMemoryEntry = function (name, scope = 'user') {
        window.apiFetch(`${API_BASE}/api/memory/${encodeURIComponent(name)}?scope=${encodeURIComponent(scope)}`, {
            method: 'DELETE'
        })
        .then(res => res.json())
        .then(() => {
            window.showToast('Deleted', `Memory '${name}' deleted.`, 'info');
            window.fetchMemories();
        })
        .catch(err => window.showToast('Error', `Failed to delete memory: ${err}`, 'error'));
    };

    const memSearchEl = document.getElementById('memorySearchInput');
    if (memSearchEl) {
        memSearchEl.addEventListener('input', debounce((e) => renderMemories(allMemories, e.target.value.trim()), 200));
    }


    // ── MODAL HELPERS & SECURE CREDENTIAL DISPATCH ──
    const openImportBtn = document.getElementById('openImportContactBtn');
    const openAddBtn = document.getElementById('openAddContactBtn');

    if (openImportBtn) openImportBtn.addEventListener('click', () => window.openContactImportModal());
    if (openAddBtn) openAddBtn.addEventListener('click', () => window.openAddContactModal());

    window.openContactImportModal = () => document.getElementById('contactImportModal')?.classList.add('active');
    window.closeContactImportModal = () => document.getElementById('contactImportModal')?.classList.remove('active');
    window.openGoogleAuthModal = () => document.getElementById('googleAuthModal')?.classList.add('active');
    window.closeGoogleAuthModal = () => document.getElementById('googleAuthModal')?.classList.remove('active');
    window.openAddContactModal = () => document.getElementById('addContactModal')?.classList.add('active');
    window.closeAddContactModal = () => document.getElementById('addContactModal')?.classList.remove('active');

    const googleAuthModeSel = document.getElementById('googleAuthMode');
    if (googleAuthModeSel) {
        googleAuthModeSel.addEventListener('change', () => {
            const appGroup = document.getElementById('googleAppPasswordGroup');
            const btn = document.getElementById('submitGoogleAuthBtn');
            if (googleAuthModeSel.value === 'credentials') {
                if (appGroup) appGroup.style.display = 'block';
                if (btn) btn.textContent = 'SAVE CREDENTIALS';
            } else {
                if (appGroup) appGroup.style.display = 'none';
                if (btn) btn.textContent = 'INITIATE GOOGLE LOGIN';
            }
        });
    }

    window.submitGoogleAuth = function () {
        const sel = document.getElementById('googleAuthMode');
        const mode = sel ? sel.value : 'credentials';
        if (mode === 'credentials') {
            const email = (document.getElementById('googleEmail') || {}).value || '';
            const pwd = (document.getElementById('googleAppPassword') || {}).value || '';
            if (!email || !pwd) {
                window.showToast('Fields Required', 'Please provide both Gmail address and App Password.', 'error');
                return;
            }
            window.apiFetch(`${API_BASE}/api/connector/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    connector: 'Gmail / Google Account',
                    api_key: pwd.trim(),
                    settings: { email: email.trim(), mode: 'credentials' }
                })
            })
            .then(res => res.json())
            .then(data => {
                window.showToast('Google Auth Saved', data.message || 'Credentials securely stored.', 'success');
                window.closeGoogleAuthModal();
                fetchConnectorStatus();
            })
            .catch(err => window.showToast('Auth Error', `Failed storing credentials: ${err}`, 'error'));
        } else {
            window.switchView('chatView');
            if (chatInput) {
                chatInput.value = `gmail_login mode='browser'`;
                transmitChat();
            }
            window.closeGoogleAuthModal();
        }
    };

    window.submitNewContactFromForm = function () {
        const name = (document.getElementById('addContactName') || {}).value || '';
        const phone = (document.getElementById('addContactPhone') || {}).value || '';
        const email = (document.getElementById('addContactEmail') || {}).value || '';
        const alias = (document.getElementById('addContactAlias') || {}).value || '';
        if (!name.trim()) {
            window.showToast('Name Required', 'Please enter a contact name.', 'error');
            return;
        }
        window.apiFetch(`${API_BASE}/api/contacts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name.trim(), phone_number: phone.trim(), email: email.trim(), aliases: alias ? [alias.trim()] : [] })
        })
        .then(res => res.json())
        .then(() => {
            window.showToast('Contact Saved', `Saved contact '${name}'`, 'success');
            window.closeAddContactModal();
            window.fetchContacts();
        })
        .catch(() => window.showToast('Error', 'Failed saving contact', 'error'));
    };

    window.submitContactImportByPath = function () {
        const pathInput = document.getElementById('contactFilePathInput');
        if (!pathInput || !pathInput.value.trim()) return;
        const formData = new FormData();
        formData.append('file_path', pathInput.value.trim());
        window.apiFetch(`${API_BASE}/api/import/contacts`, { method: 'POST', body: formData })
            .then(res => res.json())
            .then(() => {
                window.showToast('Contacts Imported', 'Contacts updated successfully.', 'success');
                window.closeContactImportModal();
                window.fetchContacts();
            })
            .catch(err => window.showToast('Import Error', `${err}`, 'error'));
    };

    // ── REAL WEB SPEECH STT & AUDIO VISUALIZER ──
    let isVoiceListening = false;
    let recognition = null;
    let voiceAnimFrameId = null;

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
        recognition = new SpeechRec();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                if (event.results[i].isFinal) {
                    finalTranscript += event.results[i][0].transcript;
                } else {
                    interimTranscript += event.results[i][0].transcript;
                }
            }

            const box = document.getElementById('liveVoiceTranscript');
            if (box) {
                box.textContent = `"${finalTranscript || interimTranscript || 'Listening...'}"`;
            }

            if (finalTranscript.trim()) {
                window.switchView('chatView');
                if (chatInput) {
                    chatInput.value = finalTranscript.trim();
                    transmitChat();
                }
            }
        };

        recognition.onerror = (event) => {
            console.warn('Speech recognition error:', event.error);
            const badge = document.getElementById('voiceStatusBadge');
            if (badge) badge.textContent = `STATUS: ERROR (${event.error})`;
        };

        recognition.onend = () => {
            if (isVoiceListening) {
                try { recognition.start(); } catch (e) {}
            }
        };
    }

    const toggleVoiceBtn = document.getElementById('toggleVoiceBtn');
    if (toggleVoiceBtn) {
        toggleVoiceBtn.addEventListener('click', toggleVoiceDictation);
    }

    function toggleVoiceDictation() {
        window.switchView('voiceView');
        const badge = document.getElementById('voiceStatusBadge');
        const transcriptBox = document.getElementById('liveVoiceTranscript');

        if (!isVoiceListening) {
            isVoiceListening = true;
            if (badge) {
                badge.textContent = 'STATUS: LISTENING (ACTIVE)';
                badge.style.borderColor = 'var(--accent-green)';
                badge.style.color = 'var(--accent-green)';
            }
            if (transcriptBox) transcriptBox.textContent = '"Listening for speech..."';
            if (recognition) {
                try { recognition.start(); } catch (e) {}
            }
            initVoiceAudioVisualizer();
            window.showToast('Voice Active', 'Listening for speech input...', 'info');
        } else {
            isVoiceListening = false;
            if (badge) {
                badge.textContent = 'STATUS: IDLE';
                badge.style.borderColor = 'var(--border-accent)';
                badge.style.color = 'var(--accent-cyan)';
            }
            if (recognition) {
                try { recognition.stop(); } catch (e) {}
            }
            if (voiceAnimFrameId !== null) cancelAnimationFrame(voiceAnimFrameId);
            window.showToast('Voice Idle', 'Microphone paused.', 'info');
        }
    }

    function initVoiceAudioVisualizer() {
        const cvs = document.getElementById('voiceCanvas');
        if (!cvs) return;
        const ctx = cvs.getContext('2d');
        let width = cvs.width = cvs.parentElement ? cvs.parentElement.clientWidth - 40 : 400;
        let height = cvs.height = 140;
        let phase = 0;

        if (voiceAnimFrameId !== null) cancelAnimationFrame(voiceAnimFrameId);

        function drawWave() {
            ctx.clearRect(0, 0, width, height);
            phase += isVoiceListening ? 0.08 : 0.02;
            const amplitude = isVoiceListening ? 32 : 8;

            ctx.beginPath();
            ctx.lineWidth = 3;
            ctx.strokeStyle = isVoiceListening ? '#00dfa2' : '#00f2fe';
            for (let x = 0; x < width; x++) {
                const y = height / 2 + Math.sin(x * 0.025 + phase) * amplitude * Math.sin(x * 0.006);
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            voiceAnimFrameId = requestAnimationFrame(drawWave);
        }
        drawWave();
    }

    // ── DYNAMIC PARTICLE CANVAS ──
    function initParticleCanvas() {
        const cvs = document.getElementById('particleCanvas');
        if (!cvs) return;
        const ctx = cvs.getContext('2d');
        let width = cvs.width = window.innerWidth;
        let height = cvs.height = window.innerHeight;

        window.addEventListener('resize', () => {
            width = cvs.width = window.innerWidth;
            height = cvs.height = window.innerHeight;
        });

        const particles = [];
        for (let i = 0; i < 35; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.35,
                vy: (Math.random() - 0.5) * 0.35,
                radius: Math.random() * 2 + 1,
            });
        }

        function render() {
            ctx.clearRect(0, 0, width, height);
            for (let i = 0; i < particles.length; i++) {
                const p = particles[i];
                p.x += p.vx;
                p.y += p.vy;
                if (p.x < 0 || p.x > width) p.vx *= -1;
                if (p.y < 0 || p.y > height) p.vy *= -1;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(0, 242, 254, 0.35)';
                ctx.fill();
            }
            requestAnimationFrame(render);
        }
        requestAnimationFrame(render);
    }

    // ── PWA SERVICE WORKER REGISTRATION ──
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/web/sw.js')
            .then(() => console.log('[PWA] Service Worker registered.'))
            .catch(err => console.debug('[PWA] Service worker registration error:', err));
    }

    // ── CAREER OS CLIENT CONTROLLER ──
    window.switchCareerTab = function (tabId) {
        document.querySelectorAll('.career-subtab').forEach(el => el.style.display = 'none');
        const activeTab = document.getElementById(tabId);
        if (activeTab) activeTab.style.display = 'block';

        const pills = document.querySelectorAll('#careerTabPills .filter-pill');
        pills.forEach(p => p.classList.remove('active'));
        if (event && event.target) event.target.classList.add('active');

        if (tabId === 'jobsTab') window.executeJobSearch();
        else if (tabId === 'profileTab') window.loadCareerProfile();
        else if (tabId === 'analyticsTab') window.loadCareerAnalytics();
        else if (tabId === 'pipelineTab') window.loadApplicationsPipeline();
    };

    window.loadCareerProfile = function () {
        window.apiFetch(`${API_BASE}/api/career/profile`)
            .then(res => res.json())
            .then(data => {
                const scoreEl = document.getElementById('careerCompletenessScore');
                if (scoreEl && data.validation) scoreEl.textContent = `${data.validation.score}%`;
                const jsonEl = document.getElementById('canonicalProfileJson');
                if (jsonEl && data.profile) jsonEl.textContent = JSON.stringify(data.profile, null, 2);
            })
            .catch(err => console.debug('Profile load note:', err));
    };

    window.executeJobSearch = function () {
        const queryInput = document.getElementById('careerJobSearchInput');
        const query = (queryInput && queryInput.value.trim()) || 'Autonomous AI Systems Engineer';
        const listEl = document.getElementById('careerJobsList');
        if (listEl) listEl.innerHTML = '<div class="subagent-idle-msg">Searching across Greenhouse, Lever, Ashby...</div>';

        window.apiFetch(`${API_BASE}/api/career/jobs/search?query=${encodeURIComponent(query)}&limit=6`)
            .then(res => res.json())
            .then(data => {
                if (!listEl) return;
                if (!data.matches || data.matches.length === 0) {
                    listEl.innerHTML = '<div class="subagent-idle-msg">No open positions found matching criteria.</div>';
                    return;
                }
                listEl.innerHTML = data.matches.map(m => {
                    const j = m.job;
                    const fit = m.match;
                    return `
                        <div class="connector-card" style="padding: 16px; display: flex; flex-direction: column; justify-content: space-between;">
                            <div>
                                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                                    <h4 style="color: #fff; font-family: var(--font-heading); font-size: 1rem;">${j.title}</h4>
                                    <span class="os-badge" style="background: rgba(0,223,162,0.15); color: var(--accent-green); font-size: 0.8rem;">
                                        Fit: ${fit.overall_score}%
                                    </span>
                                </div>
                                <div style="color: var(--accent-cyan); font-size: 0.85rem; font-weight: 600; margin-bottom: 4px;">${j.company} — ${j.location} (${j.remote_type})</div>
                                <div style="color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 10px;">Salary: ${j.salary || 'Competitive Base'} │ Platform: ${j.platform}</div>
                                <div style="font-size: 0.78rem; color: var(--text-secondary); line-height: 1.4; margin-bottom: 12px;">
                                    ${fit.fit_explanation || (j.description ? j.description.slice(0, 140) + '...' : '')}
                                </div>
                            </div>
                            <div style="display: flex; gap: 8px;">
                                <button class="btn" style="background: var(--accent-cyan); color: #000; font-weight: bold; font-size: 0.8rem; flex: 1;" onclick="window.prepareJobApplication('${j.job_id}')">
                                    ⚡ PREPARE APPLICATION
                                </button>
                                <a href="${j.application_url}" target="_blank" rel="noopener" class="btn btn-secondary" style="font-size: 0.8rem; text-decoration: none; display: flex; align-items: center;">
                                    PORTAL ↗
                                </a>
                            </div>
                        </div>
                    `;
                }).join('');
            })
            .catch(err => {
                if (listEl) listEl.innerHTML = `<div class="subagent-idle-msg">Job search note: ${err.message}</div>`;
            });
    };

    window.generateResumeArtifacts = function () {
        const role = document.getElementById('resumeTargetRoleInput')?.value.trim() || 'Systems Architect';
        const tmpl = document.getElementById('resumeTemplateSelector')?.value || 'ats_classic';
        window.showToast('Rendering Resume', `Generating verified DOCX, PDF, and HTML for '${role}'...`, 'info');

        window.apiFetch(`${API_BASE}/api/career/resumes/create`, {
            method: 'POST',
            body: JSON.stringify({ target_role: role, template_id: tmpl })
        })
        .then(res => res.json())
        .then(data => {
            window.showToast('Resume Verified', `Generated version ${data.version_id}`, 'success');
            const grid = document.getElementById('resumeArtifactsGrid');
            if (grid && data.artifacts) {
                grid.innerHTML = `
                    <div class="connector-card" style="padding: 16px;">
                        <h4 style="color: #fff; margin-bottom: 8px;">${data.resume.title} (v${data.version_id})</h4>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <a href="/api/career/download/${encodeURIComponent(data.artifacts.pdf.path)}" target="_blank" class="btn" style="background: var(--accent-cyan); color: #000; font-weight: bold; font-size: 0.8rem; text-decoration: none;">DOWNLOAD PDF</a>
                            <a href="/api/career/download/${encodeURIComponent(data.artifacts.docx.path)}" target="_blank" class="btn btn-secondary" style="font-size: 0.8rem; text-decoration: none;">DOWNLOAD DOCX</a>
                            <a href="/api/career/download/${encodeURIComponent(data.artifacts.html.path)}" target="_blank" class="btn btn-secondary" style="font-size: 0.8rem; text-decoration: none;">PREVIEW HTML</a>
                        </div>
                    </div>
                `;
            }
        })
        .catch(err => window.showToast('Export Error', `${err.message}`, 'error'));
    };

    window.runAtsAudit = function () {
        const role = document.getElementById('resumeTargetRoleInput')?.value.trim() || 'Systems Architect';
        window.showToast('Auditing ATS', 'Evaluating 7-factor deterministic screening criteria...', 'info');

        window.apiFetch(`${API_BASE}/api/career/ats/score`, {
            method: 'POST',
            body: JSON.stringify({ target_role: role })
        })
        .then(res => res.json())
        .then(data => {
            const scoreEl = document.getElementById('atsOverallScoreDisplay');
            if (scoreEl) scoreEl.textContent = `${data.overall_score}%`;
            const gradeEl = document.getElementById('atsGradeDisplay');
            if (gradeEl) gradeEl.textContent = data.grade;

            const kwEl = document.getElementById('atsKwScore');
            if (kwEl) kwEl.textContent = `${data.keyword_coverage_score}%`;
            const secEl = document.getElementById('atsSecScore');
            if (secEl) secEl.textContent = `${data.section_recognition_score}%`;
            const parseEl = document.getElementById('atsParseScore');
            if (parseEl) parseEl.textContent = `${data.parsing_risk_score}%`;
            const readEl = document.getElementById('atsReadScore');
            if (readEl) readEl.textContent = `${data.readability_score}%`;

            window.showToast('ATS Audit Complete', `Grade: ${data.grade} (${data.overall_score}%)`, 'success');
        })
        .catch(err => window.showToast('ATS Error', `${err.message}`, 'error'));
    };

    window.prepareJobApplication = function (jobId) {
        window.showToast('Assembling Application', 'Tailoring resume, cover letter & opening application portal...', 'info');

        window.apiFetch(`${API_BASE}/api/career/applications/prepare`, {
            method: 'POST',
            body: JSON.stringify({ job_id: jobId, auto_open_browser: true })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                window.showToast('Application Ready', `Package prepared for ${data.company}. Review materials in browser.`, 'success');
                window.switchCareerTab('pipelineTab');
            } else {
                window.showToast('Application Notice', data.message || 'Manual submission required.', 'warning');
            }
        })
        .catch(err => window.showToast('Application Error', `${err.message}`, 'error'));
    };

    window.switchCareerTab = function (tabId) {
        document.querySelectorAll('.career-subtab').forEach(t => t.style.display = 'none');
        const target = document.getElementById(tabId);
        if (target) target.style.display = 'block';

        const pills = document.querySelectorAll('#careerTabPills .filter-pill');
        pills.forEach(p => {
            if (p.getAttribute('onclick')?.includes(tabId)) {
                p.classList.add('active');
            } else {
                p.classList.remove('active');
            }
        });

        if (tabId === 'pipelineTab') window.loadCareerApplications();
        else if (tabId === 'interviewsTab') window.loadInterviews();
        else if (tabId === 'offersTab') window.loadOffers();
        else if (tabId === 'followupsTab') window.loadFollowups();
        else if (tabId === 'emailFeedTab') window.loadEmailEvents();
        else if (tabId === 'analyticsTab') window.loadCareerAnalytics();
    };

    window.loadCareerAnalytics = function () {
        const row = document.getElementById('analyticsMetricsRow');
        if (!row) return;

        window.apiFetch(`${API_BASE}/api/career/analytics`)
            .then(res => res.json())
            .then(a => {
                row.innerHTML = `
                    <div style="background: rgba(0,0,0,0.3); padding: 14px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 1.8rem; font-weight: bold; color: var(--accent-cyan);">${a.total_jobs_discovered}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Jobs Discovered</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 14px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 1.8rem; font-weight: bold; color: var(--accent-green);">${a.total_applications_submitted}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Applications Sent</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 14px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 1.8rem; font-weight: bold; color: var(--accent-purple);">${a.total_interviews}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Interviews</div>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 14px; border-radius: 6px; text-align: center;">
                        <div style="font-size: 1.8rem; font-weight: bold; color: #fff;">${a.response_rate}%</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">Response Rate</div>
                    </div>
                `;
            })
            .catch(err => console.debug('Analytics load error:', err));
    };

    window.loadCareerApplications = function () {
        const grid = document.getElementById('pipelineApplicationsGrid');
        if (!grid) return;

        window.apiFetch(`${API_BASE}/api/career/applications`)
            .then(res => res.json())
            .then(data => {
                if (!data.applications || data.applications.length === 0) {
                    grid.innerHTML = '<div class="subagent-idle-msg">No active applications tracked in Canonical CRM yet.</div>';
                    return;
                }
                grid.innerHTML = data.applications.map(app => {
                    const st = app.application_status || app.status;
                    const priority = app.priority || 'MEDIUM';
                    return `
                    <div class="connector-card" style="padding: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <div>
                                <h4 style="color: #fff; font-family: var(--font-heading); margin-bottom: 4px;">${app.job_title || app.role_title} @ ${app.company}</h4>
                                <span style="font-size: 0.75rem; color: var(--text-muted);">ID: <code>${app.application_id}</code> │ Applied: ${app.date_applied || 'Pending'}</span>
                            </div>
                            <div style="text-align: right;">
                                <span class="os-badge" style="background: rgba(0,242,254,0.15); color: var(--accent-cyan); font-size: 0.8rem; margin-bottom: 4px; display: inline-block;">
                                    ${st}
                                </span>
                                <div style="font-size: 0.7rem; color: var(--accent-amber); font-weight: bold;">${priority} PRIORITY</div>
                            </div>
                        </div>
                        <div style="color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 10px;">
                            Platform: ${app.platform || app.source_platform} │ Match: <strong>${app.match_score ? app.match_score + '%' : 'N/A'}</strong> │ Next Follow-up: <code>${app.next_followup || 'None'}</code>
                        </div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            ${app.job_url || app.application_url ? `<a href="${app.job_url || app.application_url}" target="_blank" rel="noopener" class="btn btn-secondary" style="font-size: 0.75rem; text-decoration: none;">PORTAL ↗</a>` : ''}
                            <button class="btn btn-secondary" style="font-size: 0.75rem;" onclick="window.viewApplicationTimeline('${app.application_id}')">📜 EVENT TIMELINE</button>
                        </div>
                    </div>
                `}).join('');
            })
            .catch(err => console.debug('Applications CRM load error:', err));
    };

    window.loadInterviews = function () {
        const grid = document.getElementById('interviewsGrid');
        if (!grid) return;

        window.apiFetch(`${API_BASE}/api/career/interviews`)
            .then(res => res.json())
            .then(data => {
                if (!data.interviews || data.interviews.length === 0) {
                    grid.innerHTML = '<div class="subagent-idle-msg">No upcoming interview loops scheduled.</div>';
                    return;
                }
                grid.innerHTML = data.interviews.map(iv => `
                    <div class="connector-card" style="padding: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <div>
                                <h4 style="color: #fff; font-family: var(--font-heading); margin-bottom: 4px;">${iv.round}: ${iv.company}</h4>
                                <div style="font-size: 0.8rem; color: var(--accent-cyan);">📅 ${iv.date} at ${iv.time_str} (${iv.timezone})</div>
                            </div>
                            <span class="os-badge" style="background: rgba(0,223,162,0.15); color: var(--accent-green); font-size: 0.8rem;">
                                ${iv.status}
                            </span>
                        </div>
                        <div style="color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 10px;">
                            Interviewer: ${iv.interviewer || 'Hiring Team'} │ Prep: <strong>${iv.preparation_status}</strong>
                        </div>
                        <div style="display: flex; gap: 8px;">
                            ${iv.meeting_url ? `<a href="${iv.meeting_url}" target="_blank" rel="noopener" class="btn" style="background: var(--accent-green); color: #000; font-size: 0.75rem; text-decoration: none; font-weight: bold;">JOIN MEETING ↗</a>` : ''}
                        </div>
                    </div>
                `).join('');
            })
            .catch(err => console.debug('Interviews load error:', err));
    };

    window.loadOffers = function () {
        const grid = document.getElementById('offersGrid');
        if (!grid) return;

        window.apiFetch(`${API_BASE}/api/career/offers`)
            .then(res => res.json())
            .then(data => {
                if (!data.offers || data.offers.length === 0) {
                    grid.innerHTML = '<div class="subagent-idle-msg">No job offers currently staged or detected.</div>';
                    return;
                }
                grid.innerHTML = data.offers.map(off => `
                    <div class="connector-card" style="padding: 16px; border-color: rgba(255,183,3,0.3);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <div>
                                <h4 style="color: #fff; font-family: var(--font-heading); margin-bottom: 4px;">🏆 ${off.company} — ${off.role}</h4>
                                <div style="font-size: 0.85rem; color: var(--accent-green); font-weight: bold;">💰 ${off.salary || 'Compensation specified in offer letter'}</div>
                            </div>
                            <span class="os-badge" style="background: rgba(255,183,3,0.15); color: var(--accent-amber); font-size: 0.8rem;">
                                ${off.status}
                            </span>
                        </div>
                        <div style="color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 10px;">
                            Joining Date: <strong>${off.joining_date || 'TBD'}</strong> │ Expiry: <strong>${off.expiry_date || 'N/A'}</strong> │ Mode: ${off.work_mode}
                        </div>
                        <div style="display: flex; gap: 8px;">
                            ${off.status !== 'OFFER_CONFIRMED' ? `<button class="btn" style="background: var(--accent-amber); color: #000; font-size: 0.75rem; font-weight: bold;" onclick="window.confirmOffer('${off.offer_id}')">CONFIRM OFFER (SAFETY APPROVAL)</button>` : '<span style="color: var(--accent-green); font-size: 0.8rem; font-weight: bold;">✓ CONFIRMED</span>'}
                        </div>
                    </div>
                `).join('');
            })
            .catch(err => console.debug('Offers load error:', err));
    };

    window.confirmOffer = function (offerId) {
        if (!confirm(`Are you sure you want to explicitly confirm offer [${offerId}]? This will record the offer as confirmed in the Canonical CRM.`)) return;

        window.apiFetch(`${API_BASE}/api/career/offers/confirm`, {
            method: 'POST',
            body: JSON.stringify({ offer_id: offerId, user_confirmed: true })
        })
        .then(res => res.json())
        .then(data => {
            window.showToast('Offer Confirmed', data.message, 'success');
            window.loadOffers();
        })
        .catch(err => window.showToast('Confirmation Error', err.message, 'error'));
    };

    window.loadFollowups = function () {
        const grid = document.getElementById('followupsGrid');
        if (!grid) return;

        window.apiFetch(`${API_BASE}/api/career/followups`)
            .then(res => res.json())
            .then(data => {
                if (!data.followups || data.followups.length === 0) {
                    grid.innerHTML = '<div class="subagent-idle-msg">No follow-ups due. All submissions are current.</div>';
                    return;
                }
                grid.innerHTML = data.followups.map(f => `
                    <div class="connector-card" style="padding: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                            <div>
                                <h4 style="color: #fff; font-family: var(--font-heading); margin-bottom: 4px;">${f.company} — ${f.role}</h4>
                                <div style="font-size: 0.8rem; color: var(--accent-amber);">⏰ Due Date: ${f.due_date} (${f.reason})</div>
                            </div>
                            <span class="os-badge" style="background: rgba(0,242,254,0.15); color: var(--accent-cyan); font-size: 0.8rem;">
                                ${f.status}
                            </span>
                        </div>
                        <div style="display: flex; gap: 8px; margin-top: 8px;">
                            <button class="btn btn-secondary" style="font-size: 0.75rem;" onclick="window.generateFollowupDraft('${f.followup_id}')">📝 GENERATE DRAFT</button>
                        </div>
                    </div>
                `).join('');
            })
            .catch(err => console.debug('Follow-ups load error:', err));
    };

    window.generateFollowupDraft = function (followupId) {
        window.apiFetch(`${API_BASE}/api/career/followups/draft`, {
            method: 'POST',
            body: JSON.stringify({ followup_id: followupId, candidate_name: 'Bharath' })
        })
        .then(res => res.json())
        .then(data => {
            alert(`Generated Follow-up Draft (${data.state}):\n\nSubject: ${data.subject}\n\n${data.body}`);
        })
        .catch(err => window.showToast('Follow-up Draft Error', err.message, 'error'));
    };

    window.loadEmailEvents = function () {
        const grid = document.getElementById('emailFeedGrid');
        if (!grid) return;

        window.apiFetch(`${API_BASE}/api/career/email/events`)
            .then(res => res.json())
            .then(data => {
                if (!data.events || data.events.length === 0) {
                    grid.innerHTML = '<div class="subagent-idle-msg">No recruitment email events recorded yet. Connect Gmail/Outlook to ingest messages.</div>';
                    return;
                }
                grid.innerHTML = data.events.map(ev => `
                    <div class="connector-card" style="padding: 14px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                            <div>
                                <strong style="color: #fff; font-size: 0.9rem;">${ev.sender}</strong>
                                <span style="font-size: 0.75rem; color: var(--text-muted);"> (${ev.received_time})</span>
                            </div>
                            <span class="os-badge" style="background: rgba(0,242,254,0.15); color: var(--accent-cyan); font-size: 0.75rem;">
                                ${ev.classification} (${Math.round(ev.confidence*100)}%)
                            </span>
                        </div>
                        <div style="color: var(--text-secondary); font-size: 0.8rem; margin-bottom: 6px;">
                            <em>${ev.subject}</em>
                        </div>
                        <div style="font-size: 0.75rem; color: var(--accent-green);">Action Taken: ${ev.action_taken}</div>
                    </div>
                `).join('');
            })
            .catch(err => console.debug('Email events load error:', err));
    };

    window.syncExcelTracker = function () {
        const out = document.getElementById('excelSyncStatusOutput');
        if (out) out.textContent = 'Syncing Canonical Database to BR_JARVIS_Career_Tracker.xlsx...';

        window.apiFetch(`${API_BASE}/api/career/spreadsheet/sync`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'SUCCESS_VERIFIED') {
                    window.showToast('Excel Synced', `Projected ${data.sheets_projected?.length || 10} sheets. Applications: ${data.applications_count}`, 'success');
                    if (out) out.textContent = `✓ Synced on ${data.timestamp} (${data.applications_count} apps, ${data.interviews_count} interviews, ${data.offers_count} offers).`;
                } else if (data.status === 'QUEUED_LOCKED') {
                    window.showToast('Excel Locked', 'File is currently open in Excel. Projection queued.', 'warning');
                    if (out) out.textContent = '⚠️ File currently open in Excel. Will auto-retry on next cycle.';
                } else {
                    window.showToast('Sync Failed', data.error || 'Projection error', 'error');
                }
            })
            .catch(err => window.showToast('Sync Error', err.message, 'error'));
    };

    window.viewApplicationTimeline = function (applicationId) {
        window.apiFetch(`${API_BASE}/api/career/crm/events/${applicationId}`)
            .then(res => res.json())
            .then(data => {
                if (!data.events || data.events.length === 0) {
                    alert(`No event log found for Application ${applicationId}.`);
                    return;
                }
                const timelineStr = data.events.map(e => `[${new Date(e.timestamp * 1000).toLocaleString()}] ${e.event_type}\nFrom: ${e.previous_state} -> To: ${e.new_state}\nActor: ${e.actor} | Source: ${e.source}\nEvidence: ${e.evidence}`).join('\n\n---\n\n');
                alert(`Event Audit Log for Application [${applicationId}]:\n\n${timelineStr}`);
            })
            .catch(err => window.showToast('Timeline Error', err.message, 'error'));
    };

    // Initial Engine Bootstrap
    initParticleCanvas();
    setInterval(fetchTelemetry, 5000);
    checkAuthStatus();
    window.loadCareerProfile();
});

