// web/app.js — BR JARVIS AI Operating System Client Engine v38.5.0
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

    window.apiFetch = function (url, options = {}) {
        const opts = Object.assign({}, options);
        opts.headers = Object.assign({}, opts.headers || {});
        return fetch(url, opts);
    };

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
        toast.className = `toast-item ${type}`;

        const titleEl = document.createElement('div');
        titleEl.style.cssText = "font-weight: bold; font-size: 0.82rem; color: var(--accent-cyan);";
        titleEl.textContent = title;

        const msgEl = document.createElement('div');
        msgEl.style.cssText = "font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;";
        msgEl.textContent = message;

        toast.appendChild(titleEl);
        toast.appendChild(msgEl);
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(40px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    };

    // ── SECURE WEBSOCKET CONNECTION ENGINE (TICKET-BASED) ──
    let wsReconnectDelay = 1000;
    let wsReconnectTimer = null;

    function _setWsStatus(connected) {
        document.querySelectorAll('.ws-status-dot').forEach(el => {
            el.style.background = connected ? 'var(--accent-green, #00dfa2)' : '#ff4444';
            el.title = connected ? 'WebSocket Connected' : 'WebSocket Disconnected — Reconnecting...';
        });
    }

    async function getWsTicket() {
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
        try {
            const ticket = await getWsTicket();
            const wsUrl = ticket ? `${wsProtocol}://${host}/ws?ticket=${encodeURIComponent(ticket)}` : `${wsProtocol}://${host}/ws`;

            socket = new WebSocket(wsUrl);

            socket.onopen = () => {
                wsReconnectDelay = 1000;
                _setWsStatus(true);
                window.showToast('Connected', 'JARVIS AI Core online.', 'success');
                fetchTelemetry();
                fetchConnectorStatus();
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleServerMessage(data);
                } catch (e) {
                    console.log('WS Raw Message:', event.data);
                }
            };

            socket.onclose = () => {
                _setWsStatus(false);
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
        window.apiFetch(`${API_BASE}/api/connectors`)
            .then(r => r.json())
            .then(data => {
                if (!data || !data.connectors) return;
                renderConnectorPanel(data.connectors);
            })
            .catch(() => {});
    }

    function renderConnectorPanel(connectors) {
        const panel = document.getElementById('connectorPanel');
        if (!panel) return;
        panel.innerHTML = '';
        connectors.forEach(c => {
            const isConfigured = c.configured || c.status === 'CONNECTED';
            const badge = document.createElement('div');
            badge.className = `connector-badge ${isConfigured ? 'active' : ''}`;
            badge.title = `${c.name}: ${c.tools ? c.tools.length : 0} tools (${c.status || (isConfigured ? 'CONNECTED' : 'NOT_CONFIGURED')})`;
            badge.onclick = () => window.switchView('connectorsView');

            const iconSpan = document.createElement('span');
            iconSpan.className = 'connector-icon';
            iconSpan.textContent = c.icon || '🔌';

            const nameSpan = document.createElement('span');
            nameSpan.className = 'connector-name';
            nameSpan.textContent = String(c.name || '').split(' ')[0];

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
    window.runConnectorAction = function (name, actionType = 'default') {
        if (actionType === 'browse_contacts') {
            window.switchView('contactsView');
            return;
        }
        window.switchView('chatView');
        if (!chatInput) return;
        let promptText = '';
        const n = String(name || '').toLowerCase();

        if (n.includes('gmail')) {
            promptText = actionType === 'send' ? 'send_email recipient="" subject="" body=""' : 'read_unread_emails';
        } else if (n.includes('github')) {
            promptText = actionType === 'issue' ? 'github_create_issue owner="" repo="" title="" body=""' : 'github_list_prs owner="" repo=""';
        } else if (n.includes('notion')) {
            promptText = actionType === 'create' ? 'notion_create_page title="" content=""' : 'notion_search_pages query=""';
        } else if (n.includes('calendar')) {
            promptText = actionType === 'add' ? 'create_calendar_event summary="" start="" end=""' : 'list_calendar_events date="today"';
        } else if (n.includes('whatsapp')) {
            promptText = actionType === 'contacts' ? 'manage_whatsapp_contacts' : 'send_whatsapp recipient="" message=""';
        } else if (n.includes('wikipedia')) {
            promptText = 'wikipedia_search query=""';
        } else if (n.includes('youtube')) {
            promptText = 'youtube_search query=""';
        } else if (n.includes('weather')) {
            promptText = 'get_weather city=""';
        } else if (n.includes('rss')) {
            promptText = 'fetch_rss_news topic="tech"';
        } else if (n.includes('filesystem')) {
            promptText = 'list_dir path="./"';
        } else if (n.includes('mcp')) {
            promptText = 'mcp_call tool="" params={}';
        } else {
            promptText = `${n.replace(/[^a-z0-9]/g, '_')}_action `;
        }

        chatInput.value = promptText;
        chatInput.focus();
        window.showToast('Connector Selected', `Populated command for ${name}. Complete parameters and press Enter.`, 'info');
    };

    window.openConnectorConfigModal = function (name) {
        const modal = document.getElementById('connectorConfigModal');
        const title = document.getElementById('configModalTitle');
        const inputHidden = document.getElementById('configConnectorName');
        const apiKeyInput = document.getElementById('configApiKeyInput');
        if (title) title.textContent = `🔑 Configure ${name} Key`;
        if (inputHidden) inputHidden.value = name;
        if (apiKeyInput) apiKeyInput.value = '';
        if (modal) modal.classList.add('active');
    };

    window.closeConnectorConfigModal = function () {
        document.getElementById('connectorConfigModal')?.classList.remove('active');
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

    window.fetchConnectors = function () {
        window.apiFetch(`${API_BASE}/api/connectors`)
            .then(res => res.json())
            .then(data => {
                const grid = document.getElementById('connectorsGrid');
                if (!grid || !data.connectors) return;
                grid.innerHTML = '';
                data.connectors.forEach(c => {
                    const isConnected = c.configured || c.status === 'CONNECTED';
                    const st = isConnected ? 'CONNECTED' : 'NOT_CONFIGURED';
                    const card = document.createElement('div');
                    card.className = 'connector-card';

                    const topRow = document.createElement('div');
                    topRow.style.cssText = "display: flex; align-items: center; justify-content: space-between;";
                    const iconSpan = document.createElement('span');
                    iconSpan.style.fontSize = '28px';
                    iconSpan.textContent = c.icon || '🔌';
                    const badgeSpan = document.createElement('span');
                    badgeSpan.className = 'os-badge';
                    badgeSpan.style.cssText = `background: ${isConnected ? 'rgba(0, 223, 162, 0.15)' : 'rgba(255, 183, 3, 0.15)'}; color: ${isConnected ? 'var(--accent-green)' : 'var(--accent-amber)'}; border-color: ${isConnected ? 'rgba(0, 223, 162, 0.4)' : 'rgba(255, 183, 3, 0.4)'};`;
                    badgeSpan.textContent = st;
                    topRow.appendChild(iconSpan);
                    topRow.appendChild(badgeSpan);

                    const titleH4 = document.createElement('h4');
                    titleH4.style.cssText = "color: #fff; font-family: var(--font-heading); margin-top: 10px; font-size: 1.05rem;";
                    titleH4.textContent = c.name;

                    const descP = document.createElement('p');
                    descP.style.cssText = "font-size: 0.78rem; color: var(--text-secondary); flex: 1; margin: 4px 0 12px;";
                    descP.textContent = c.desc || '';

                    const actDiv = document.createElement('div');
                    actDiv.style.cssText = "display: flex; gap: 6px; flex-wrap: wrap;";

                    const actBtn = document.createElement('button');
                    actBtn.className = 'btn btn-secondary';
                    actBtn.textContent = '⚡ Run Action';
                    actBtn.onclick = () => window.runConnectorAction(c.name);
                    actDiv.appendChild(actBtn);

                    const cfgBtn = document.createElement('button');
                    cfgBtn.className = 'btn btn-secondary';
                    cfgBtn.textContent = '⚙ Configure';
                    cfgBtn.onclick = () => window.openConnectorConfigModal(c.name);
                    actDiv.appendChild(cfgBtn);

                    card.appendChild(topRow);
                    card.appendChild(titleH4);
                    card.appendChild(descP);
                    card.appendChild(actDiv);
                    grid.appendChild(card);
                });
            })
            .catch(() => {});
    };

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
            empty.style.cssText = "grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;";
            empty.textContent = 'No contacts found.';
            grid.appendChild(empty);
            return;
        }
        list.slice(0, 60).forEach(c => {
            const card = document.createElement('div');
            card.className = 'contact-card';

            const row = document.createElement('div');
            row.style.cssText = "display: flex; align-items: center; gap: 10px;";

            const avatar = document.createElement('div');
            avatar.style.cssText = "width: 36px; height: 36px; border-radius: 50%; background: var(--accent-purple); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: bold;";
            avatar.textContent = (c.name || '?')[0].toUpperCase();

            const info = document.createElement('div');
            const nameEl = document.createElement('div');
            nameEl.style.cssText = "color: #fff; font-weight: 600; font-size: 14px;";
            nameEl.textContent = c.name;
            const subEl = document.createElement('div');
            subEl.style.cssText = "font-size: 11px; color: var(--text-muted);";
            subEl.textContent = c.phone_number || c.email || (c.aliases ? c.aliases.join(', ') : '');

            info.appendChild(nameEl);
            info.appendChild(subEl);
            row.appendChild(avatar);
            row.appendChild(info);
            card.appendChild(row);
            grid.appendChild(card);
        });
    }

    const contactSearchInput = document.getElementById('contactSearchInput');
    if (contactSearchInput) {
        contactSearchInput.addEventListener('input', debounce((e) => window.fetchContacts(e.target.value.trim()), 200));
    }

    // ── FILE IMPORT & RAG MEMORY ──
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
                .then(data => window.showToast('Success', data.message || `File '${file.name}' ingested.`, 'success'))
                .catch(err => window.showToast('Error', `Failed uploading ${file.name}`, 'error'));
        }
    };

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

    // Initial Engine Bootstrap
    window.fetchConnectors();
    window.fetchSkills();
    initParticleCanvas();
    setInterval(fetchTelemetry, 5000);
    initWebSocket();
});
