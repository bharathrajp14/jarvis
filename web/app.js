// web/app.js — BR JARVIS AI Operating System Client Engine v38.5
document.addEventListener('DOMContentLoaded', () => {
    const host = window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const API_BASE = `${protocol}://${host}`;
    const apiKey = localStorage.getItem('jarvis_api_key') || window.JARVIS_API_KEY || '';
    const WS_URL = `${wsProtocol}://${host}/ws${apiKey ? `?token=${encodeURIComponent(apiKey)}` : ''}`;

    window.apiFetch = function(url, options = {}) {
        const opts = Object.assign({}, options);
        opts.headers = Object.assign({}, opts.headers || {});
        if (apiKey) {
            opts.headers['X-API-Key'] = apiKey;
            opts.headers['Authorization'] = `Bearer ${apiKey}`;
        }
        return fetch(url, opts);
    };

    // DOM Elements
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

    let socket = null;

    // ── ROLE & MODEL CHANGE NOTIFIERS ──
    if (roleSelector) {
        roleSelector.addEventListener('change', (e) => {
            window.showToast('Role Switched', `Persona set to '${e.target.value.toUpperCase()}'`, 'info');
        });
    }

    if (backendSelector) {
        backendSelector.addEventListener('change', (e) => {
            window.showToast('Model Switched', `Active model set to '${e.target.options[e.target.selectedIndex].text}'`, 'info');
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
    window.switchView = function(viewId) {
        navItems.forEach(item => {
            if (item.dataset.view === viewId) item.classList.add('active');
            else item.classList.remove('active');
        });
        viewContainers.forEach(container => {
            if (container.id === viewId) container.classList.add('active');
            else container.classList.remove('active');
        });

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
    window.showToast = function(title, message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast-item ${type}`;
        toast.style.cssText = `
            background: var(--bg-card);
            border: 1px solid var(--border-accent);
            border-radius: var(--radius-md);
            padding: 10px 14px;
            color: #fff;
            min-width: 240px;
            box-shadow: var(--glow-cyan);
            transition: all 0.3s ease;
        `;
        toast.innerHTML = `
            <div style="font-weight: bold; font-size: 0.82rem; color: var(--accent-cyan);">${title}</div>
            <div style="font-size: 0.75rem; color: var(--text-secondary);">${message}</div>
        `;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(50px)';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    };

    // ── WEBSOCKET CONNECTION ENGINE ──
    let wsReconnectDelay = 1000;
    let wsReconnectTimer = null;
    let wsConnected = false;

    function _setWsStatus(connected) {
        wsConnected = connected;
        document.querySelectorAll('.ws-status-dot').forEach(el => {
            el.style.background = connected ? 'var(--accent-green, #00dfa2)' : '#ff4444';
            el.title = connected ? 'Connected' : 'Disconnected — reconnecting...';
        });
    }

    function initWebSocket() {
        if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) return;
        try {
            socket = new WebSocket(WS_URL);

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
        window.apiFetch(`${API_BASE}/api/connector/status`)
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
        panel.innerHTML = connectors.map(c => `
            <div class="connector-badge ${c.configured ? 'active' : 'inactive'}" style="cursor: pointer;" onclick="switchView('connectorsView')" title="${c.name}: ${c.tools ? c.tools.length : 0} tools (click to view)">
                <span class="connector-icon">${c.icon || '🔌'}</span>
                <span class="connector-name">${c.name.split(' ')[0]}</span>
                <span class="connector-dot ${c.configured ? 'green' : 'grey'}"></span>
            </div>
        `).join('');
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
            currentStreamBubble.innerHTML = `
                <div class="msg-author">JARVIS</div>
                <div class="msg-body"></div>
            `;
            chatWindow.appendChild(currentStreamBubble);
            currentStreamBody = currentStreamBubble.querySelector('.msg-body');
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
        let taskList = document.getElementById('webAgentTaskList');
        if (!taskList) {
            const sidebar = document.querySelector('.left-panel .nav-section') || document.body;
            taskList = document.createElement('div');
            taskList.id = 'webAgentTaskList';
            taskList.className = 'web-agent-task-panel';
            taskList.innerHTML = '<div class="nav-title" style="margin-top: 10px;">⚡ LIVE SUB-AGENTS</div>';
            sidebar.appendChild(taskList);
        }
        let card = document.getElementById(`task-card-${taskId}`);
        if (!card) {
            card = document.createElement('div');
            card.id = `task-card-${taskId}`;
            card.className = 'connector-card';
            card.style.padding = '8px 12px';
            taskList.appendChild(card);
        }
        const st = (status || 'running').toUpperCase();
        const pct = Math.round((progress || 0) * 100);
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; font-size: 0.72rem; font-family: var(--font-code);">
                <span style="color: var(--accent-cyan);">🤖 ${name || taskId}</span>
                <span style="color: var(--accent-green);">${st}</span>
            </div>
            <div style="background: rgba(255,255,255,0.1); height: 4px; border-radius: 2px; margin-top: 4px; overflow: hidden;">
                <div style="background: var(--accent-cyan); width: ${pct}%; height: 100%;"></div>
            </div>
        `;
    }

    function removeWebTaskCard(taskId) {
        const card = document.getElementById(`task-card-${taskId}`);
        if (card) card.remove();
    }

    function transmitChat() {
        if (!chatInput) return;
        const text = chatInput.value.trim();
        if (!text) return;

        appendChatMessage('User', text, 'user');
        chatInput.value = '';

        if (socket && socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({
                type: 'chat_prompt',
                prompt: text,
                backend: backendSelector ? backendSelector.value : 'gemini',
                role: roleSelector ? roleSelector.value : 'general'
            }));
        } else {
            window.apiFetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            })
            .then(res => res.json())
            .then(data => {
                appendChatMessage('JARVIS', data.response || data.result, 'system');
            })
            .catch(err => {
                appendChatMessage('JARVIS', `Error: ${err}`, 'system');
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
        bubble.innerHTML = `
            <div class="msg-author">${author}</div>
            <div class="msg-body">${formatMarkdown(text)}</div>
        `;
        chatWindow.appendChild(bubble);
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }

    window.copyCodeToClipboard = function(btn) {
        const codeEl = btn.parentElement ? btn.parentElement.querySelector('code') : null;
        if (codeEl) {
            navigator.clipboard.writeText(codeEl.innerText)
                .then(() => window.showToast('Copied', 'Code copied to clipboard.', 'success'))
                .catch(() => window.showToast('Copy Failed', 'Could not copy code.', 'error'));
        }
    };

    function formatMarkdown(text) {
        if (!text) return '';
        let escaped = String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');

        escaped = escaped.replace(/```([\s\S]*?)```/g, (match, code) => {
            return `<div class="code-block" style="position: relative;"><button class="btn btn-secondary" style="position: absolute; top: 6px; right: 6px; font-size: 0.65rem; padding: 2px 8px; background: rgba(255,255,255,0.1);" onclick="copyCodeToClipboard(this)">📋 Copy Code</button><pre><code>${code}</code></pre></div>`;
        });
        escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        return escaped.replace(/\n/g, '<br>');
    }

    // ── COMMAND PALETTE (Ctrl+K) ──
    const cmdPaletteModal = document.getElementById('cmdPaletteModal');
    const cmdPaletteTrigger = document.getElementById('cmdPaletteTrigger');
    const cmdPaletteInput = document.getElementById('cmdPaletteInput');
    const cmdPaletteResults = document.getElementById('cmdPaletteResults');

    window.openCommandPalette = function() {
        if (cmdPaletteModal) {
            cmdPaletteModal.classList.add('active');
            if (cmdPaletteInput) {
                cmdPaletteInput.value = '';
                cmdPaletteInput.focus();
                renderCmdResults('');
            }
        }
    };

    window.closeCommandPalette = function() {
        if (cmdPaletteModal) cmdPaletteModal.classList.remove('active');
    };

    if (cmdPaletteTrigger) cmdPaletteTrigger.addEventListener('click', window.openCommandPalette);

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            window.openCommandPalette();
        }
        if (e.key === 'Escape') window.closeCommandPalette();
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
            { label: '🔗 Open App Connectors', action: () => window.switchView('connectorsView') },
            { label: '📱 Open Contacts Store', action: () => window.switchView('contactsView') },
            { label: '⚡ Open Skills Library', action: () => window.switchView('skillsView') },
            { label: '🧠 Open Knowledge RAG', action: () => window.switchView('knowledgeView') },
            { label: '🔑 Open Google Auth', action: () => window.openGoogleAuthModal() },
            { label: '👤 Add New Contact', action: () => window.openAddContactModal() }
        ];

        const filtered = query ? items.filter(i => i.label.toLowerCase().includes(q)) : items;
        cmdPaletteResults.innerHTML = filtered.map(item => `
            <div class="cmd-item" onclick="executeCmdItem('${item.label.replace(/'/g, "\\'")}')">${item.label}</div>
        `).join('');

        window._cmdItemsMap = items;
    }

    window.executeCmdItem = function(label) {
        if (window._cmdItemsMap) {
            const found = window._cmdItemsMap.find(i => i.label === label);
            if (found) found.action();
        }
        window.closeCommandPalette();
    };

    // ── CONNECTORS & SKILLS LOADERS ──
    window.runConnectorAction = function(name, actionType = 'default') {
        if (actionType === 'browse_contacts') {
            window.switchView('contactsView');
            return;
        }
        window.switchView('chatView');
        if (!chatInput) return;
        let promptText = '';
        const n = name.toLowerCase();

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

    window.openConnectorConfigModal = function(name) {
        const modal = document.getElementById('connectorConfigModal');
        const title = document.getElementById('configModalTitle');
        const inputHidden = document.getElementById('configConnectorName');
        const apiKeyInput = document.getElementById('configApiKeyInput');
        if (title) title.textContent = `🔑 Configure ${name} Key`;
        if (inputHidden) inputHidden.value = name;
        if (apiKeyInput) apiKeyInput.value = '';
        if (modal) modal.classList.add('active');
    };

    window.closeConnectorConfigModal = function() {
        document.getElementById('connectorConfigModal')?.classList.remove('active');
    };

    window.submitConnectorConfig = function() {
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

    window.fetchConnectors = function() {
        window.apiFetch(`${API_BASE}/api/connectors`)
            .then(res => res.json())
            .then(data => {
                const grid = document.getElementById('connectorsGrid');
                if (!grid || !data.connectors) return;
                grid.innerHTML = data.connectors.map(c => {
                    const st = (c.status || 'NOT_CONFIGURED').toUpperCase();
                    const isConnected = st === 'CONNECTED';
                    const safeName = c.name.replace(/'/g, "\\'");
                    const n = c.name.toLowerCase();
                    
                    let actBtns = '';
                    if (n.includes('gmail')) {
                        actBtns = `
                            <button class="btn btn-secondary" onclick="openGoogleAuthModal()">🔑 Google Login</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'inbox')">📬 Read Inbox</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'send')">✉️ Send Email</button>
                        `;
                    } else if (n.includes('contacts')) {
                        actBtns = `
                            <button class="btn btn-secondary" onclick="openContactImportModal()">📥 Import VCF/CSV</button>
                            <button class="btn btn-secondary" onclick="openAddContactModal()">👤 Add Contact</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'browse_contacts')">🔍 Browse</button>
                        `;
                    } else if (n.includes('github')) {
                        actBtns = `
                            <button class="btn btn-secondary" onclick="openConnectorConfigModal('${safeName}')">🔑 Set Token</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'prs')">📋 List PRs</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'issue')">🐛 Create Issue</button>
                        `;
                    } else if (n.includes('notion')) {
                        actBtns = `
                            <button class="btn btn-secondary" onclick="openConnectorConfigModal('${safeName}')">🔑 Set Key</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'search')">🔍 Search</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'create')">📝 Create Page</button>
                        `;
                    } else if (n.includes('calendar')) {
                        actBtns = `
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'list')">📅 Events</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'add')">➕ Add Event</button>
                        `;
                    } else if (n.includes('whatsapp')) {
                        actBtns = `
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'send')">💬 Send Msg</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}', 'contacts')">👥 Contacts</button>
                        `;
                    } else if (n.includes('weather')) {
                        actBtns = `
                            <button class="btn btn-secondary" onclick="openConnectorConfigModal('${safeName}')">🔑 Set Key</button>
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}')">🌤️ Weather</button>
                        `;
                    } else {
                        actBtns = `
                            <button class="btn btn-secondary" onclick="runConnectorAction('${safeName}')">⚡ Action</button>
                        `;
                    }

                    return `
                        <div class="connector-card">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-size: 28px;">${c.icon}</span>
                                <span class="os-badge" style="background: ${isConnected ? 'rgba(0, 223, 162, 0.15)' : 'rgba(255, 183, 3, 0.15)'}; color: ${isConnected ? 'var(--accent-green)' : 'var(--accent-amber)'}; border-color: ${isConnected ? 'rgba(0, 223, 162, 0.4)' : 'rgba(255, 183, 3, 0.4)'};">${st}</span>
                            </div>
                            <h4 style="color: #fff; font-family: var(--font-heading); margin-top: 10px; font-size: 1.05rem;">${c.name}</h4>
                            <p style="font-size: 0.78rem; color: var(--text-secondary); flex: 1; margin: 4px 0 12px;">${c.desc}</p>
                            <div style="display: flex; gap: 6px; flex-wrap: wrap;">${actBtns}</div>
                        </div>
                    `;
                }).join('');
            })
            .catch(() => {});
    };

    let allSkills = [];
    window.fetchSkills = function(query = '') {
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
        if (filtered.length === 0) {
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;">No matching skills found.</div>`;
            return;
        }
        grid.innerHTML = filtered.map(s => `
            <div class="skill-card">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <h4 style="margin: 0; color: var(--accent-cyan); font-family: var(--font-code); font-size: 14px;">⚡ /${s.name}</h4>
                    <span class="os-badge">Built-in</span>
                </div>
                <p style="font-size: 11px; color: var(--text-secondary); flex: 1;">${s.description}</p>
                <button class="btn btn-secondary" style="width: 100%;" onclick="runSkill('${s.name}')">⚡ Run Skill</button>
            </div>
        `).join('');
    }

    window.runSkill = function(skillName) {
        window.switchView('chatView');
        if (chatInput) {
            chatInput.value = `/${skillName} `;
            chatInput.focus();
            window.showToast('Skill Selected', `Populated '/${skillName}'. Add parameters if required, then press Enter.`, 'info');
        }
    };

    const skillSearchInput = document.getElementById('skillSearchInput');
    if (skillSearchInput) {
        skillSearchInput.addEventListener('input', (e) => renderSkills(allSkills, e.target.value.trim()));
    }

    // ── CONTACTS HUB ──
    window.fetchContacts = function(query = '') {
        const url = query ? `${API_BASE}/api/contacts?query=${encodeURIComponent(query)}` : `${API_BASE}/api/contacts`;
        window.apiFetch(url)
            .then(res => res.json())
            .then(data => renderContacts(data.contacts || []))
            .catch(() => {});
    };

    function renderContacts(list) {
        const grid = document.getElementById('contactsGrid');
        if (!grid) return;
        if (!list || list.length === 0) {
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;">No contacts found.</div>`;
            return;
        }
        grid.innerHTML = list.slice(0, 60).map(c => `
            <div class="contact-card">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <div style="width: 36px; height: 36px; border-radius: 50%; background: var(--accent-purple); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: bold;">${(c.name || '?')[0].toUpperCase()}</div>
                    <div>
                        <div style="color: #fff; font-weight: 600; font-size: 14px;">${c.name}</div>
                        <div style="font-size: 11px; color: var(--text-muted);">${c.phone_number || c.email || ''}</div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    const contactSearchInput = document.getElementById('contactSearchInput');
    if (contactSearchInput) {
        contactSearchInput.addEventListener('input', (e) => window.fetchContacts(e.target.value.trim()));
    }

    // ── FILE IMPORT & RAG MEMORY ──
    window.triggerFileImport = function(type = 'universal') {
        const input = document.getElementById('fileImportInput');
        if (input) {
            input.value = '';
            input.click();
        }
    };

    window.uploadKnowledgeFiles = function(files) {
        if (!files || !files.length) return;
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);
            window.showToast('Uploading', `Ingesting '${file.name}' into RAG memory...`, 'info');
            window.apiFetch(`${API_BASE}/api/import/file`, { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => window.showToast('Success', data.message || 'File ingested.', 'success'))
                .catch(err => window.showToast('Error', `Failed uploading ${file.name}`, 'error'));
        }
    };

    // ── MODAL HELPERS ──
    window.openContactImportModal = () => document.getElementById('contactImportModal')?.classList.add('active');
    window.closeContactImportModal = () => document.getElementById('contactImportModal')?.classList.remove('active');
    window.openGoogleAuthModal = () => document.getElementById('googleAuthModal')?.classList.add('active');
    window.closeGoogleAuthModal = () => document.getElementById('googleAuthModal')?.classList.remove('active');
    window.openAddContactModal = () => document.getElementById('addContactModal')?.classList.add('active');
    window.closeAddContactModal = () => document.getElementById('addContactModal')?.classList.remove('active');

    window.toggleGoogleAuthMode = function() {
        const sel = document.getElementById('googleAuthMode');
        const appGroup = document.getElementById('googleAppPasswordGroup');
        const btn = document.getElementById('submitGoogleAuthBtn');
        if (!sel) return;
        if (sel.value === 'credentials') {
            if (appGroup) appGroup.style.display = 'block';
            if (btn) btn.textContent = 'SAVE CREDENTIALS';
        } else {
            if (appGroup) appGroup.style.display = 'none';
            if (btn) btn.textContent = 'INITIATE GOOGLE LOGIN';
        }
    };

    window.submitGoogleAuth = function() {
        const sel = document.getElementById('googleAuthMode');
        const mode = sel ? sel.value : 'credentials';
        if (mode === 'credentials') {
            const email = (document.getElementById('googleEmail') || {}).value || '';
            const pwd = (document.getElementById('googleAppPassword') || {}).value || '';
            if (!email || !pwd) {
                window.showToast('Fields Required', 'Please provide both Gmail address and App Password.', 'error');
                return;
            }
            if (chatInput) {
                chatInput.value = `gmail_login mode='credentials' email='${email}' app_password='${pwd}'`;
                transmitChat();
            }
        } else {
            if (chatInput) {
                chatInput.value = `gmail_login mode='browser'`;
                transmitChat();
            }
        }
        window.closeGoogleAuthModal();
        window.showToast('Google Auth', 'Google login request sent to JARVIS.', 'info');
    };

    window.submitNewContactFromForm = function() {
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

    window.submitContactImportByPath = function() {
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

    // ── VOICE AUDIO CANVAS ──
    let voiceAnimFrameId = null;
    window.triggerVoiceDictation = function() {
        window.switchView('voiceView');
        initVoiceAudioVisualizer();
    };

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
            phase += 0.05;
            ctx.beginPath();
            ctx.lineWidth = 3;
            ctx.strokeStyle = '#00f2fe';
            for (let x = 0; x < width; x++) {
                const y = height / 2 + Math.sin(x * 0.02 + phase) * 25 * Math.sin(x * 0.005);
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            voiceAnimFrameId = requestAnimationFrame(drawWave);
        }
        voiceAnimFrameId = requestAnimationFrame(drawWave);
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
        for (let i = 0; i < 40; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.4,
                vy: (Math.random() - 0.5) * 0.4,
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
                ctx.fillStyle = 'rgba(0, 242, 254, 0.4)';
                ctx.fill();
            }
            requestAnimationFrame(render);
        }
        requestAnimationFrame(render);
    }

    window.fetchConnectors();
    window.fetchSkills();
    initParticleCanvas();
    setInterval(fetchTelemetry, 5000);
    initWebSocket();
});
