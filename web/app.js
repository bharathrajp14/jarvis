// web/app.js — BR JARVIS AI Desktop Operating System Client Engine
document.addEventListener('DOMContentLoaded', () => {
    const host = window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const API_BASE = `${protocol}://${host}`;
    const WS_URL = `${wsProtocol}://${host}/ws`;

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
    const inputRoleChip = document.getElementById('inputRoleChip');
    const activeRoleBadge = document.getElementById('activeRoleBadge');

    // Gauges
    const cpuRing = document.getElementById('cpu-ring');
    const ramRing = document.getElementById('ram-ring');
    const diskRing = document.getElementById('disk-ring');
    const cpuValue = document.getElementById('cpu-value');
    const ramValue = document.getElementById('ram-value');
    const diskValue = document.getElementById('disk-value');

    let socket = null;

    // ── SYSTEM TIME ──
    function updateSystemTime() {
        if (systemTimeEl) {
            systemTimeEl.textContent = new Date().toLocaleTimeString();
        }
    }
    setInterval(updateSystemTime, 1000);
    updateSystemTime();

    // ── TELEMETRY GAUGES ──
    function setGauge(ring, textEl, value) {
        if (!ring || !textEl) return;
        const val = Math.min(100, Math.max(0, parseFloat(value) || 0));
        const offset = 251.2 - (251.2 * val) / 100;
        ring.style.strokeDashoffset = offset;
        textEl.textContent = `${Math.round(val)}%`;
    }

    function fetchTelemetry() {
        fetch(`${API_BASE}/health`)
            .then(res => res.json())
            .then(data => {
                if (data.cpu_percent !== undefined) setGauge(cpuRing, cpuValue, data.cpu_percent);
                if (data.memory_percent !== undefined) setGauge(ramRing, ramValue, data.memory_percent);
                if (data.disk_percent !== undefined) setGauge(diskRing, diskValue, data.disk_percent);
            })
            .catch(() => {});
    }

    // ── VIEW SWITCHER ──
    window.switchView = function(viewId) {
        navItems.forEach(item => {
            if (item.dataset.view === viewId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });
        viewContainers.forEach(container => {
            if (container.id === viewId) {
                container.classList.add('active');
            } else {
                container.classList.remove('active');
            }
        });
        if (viewId === 'contactsView' && typeof window.fetchContacts === 'function') {
            window.fetchContacts();
        }
    };

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewId = item.dataset.view;
            if (viewId) switchView(viewId);
        });
    });

    // ── ROLE PERSONA SWITCHER ──
    if (roleSelector) {
        roleSelector.addEventListener('change', (e) => {
            const role = e.target.value.toUpperCase();
            if (activeRoleBadge) activeRoleBadge.textContent = `ROLE: ${role}`;
            if (inputRoleChip) inputRoleChip.textContent = `ROLE: ${role}`;
        });
    }

    // ── TOAST NOTIFICATIONS ──
    window.showToast = function(title, message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast-item ${type}`;
        toast.innerHTML = `
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        `;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    };

    // ── WEBSOCKET CONNECTION ──
    function initWebSocket() {
        try {
            socket = new WebSocket(WS_URL);

            socket.onopen = () => {
                showToast('WebSocket Link Active', 'Connected to JARVIS AI Core Server.', 'success');
                fetchTelemetry();
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleServerMessage(data);
                } catch (e) {
                    console.log('WS Message:', event.data);
                }
            };

            socket.onclose = () => {
                setTimeout(initWebSocket, 3000);
            };
        } catch (e) {
            console.error('WebSocket Init Error:', e);
        }
    }

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
        }
    }

    // ── CHAT TRANSMISSION ──
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
            // REST Fallback
            fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: text })
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

    function formatMarkdown(text) {
        if (!text) return '';
        let escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        escaped = escaped.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        return escaped.replace(/\n/g, '<br>');
    }

    // ── CONNECTORS & SKILLS LOADERS ──
    function fetchConnectors() {
        fetch(`${API_BASE}/api/connectors`)
            .then(res => res.json())
            .then(data => {
                const grid = document.getElementById('connectorsGrid');
                if (!grid || !data.connectors) return;
                grid.innerHTML = data.connectors.map(c => {
                    const st = (c.status || 'NOT_CONFIGURED').toLowerCase();
                    const badgeClass = st === 'connected' ? 'connected' : 'not_configured';
                    const actBtn = c.name.includes('Google') ?
                        `<button class="btn btn-secondary" onclick="openGoogleAuthModal()">🔑 Google Login</button>` :
                        c.name.includes('Contacts') ?
                        `<button class="btn btn-secondary" onclick="openContactImportModal()">📥 Import Contacts</button>` :
                        `<button class="btn btn-secondary" onclick="switchView('chatView')">⚡ Action</button>`;

                    return `
                        <div class="connector-card">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-size: 24px;">${c.icon}</span>
                                <span class="status-badge ${badgeClass}">${c.status}</span>
                            </div>
                            <h4 style="color: #fff; font-family: var(--font-heading); margin-top: 8px;">${c.name}</h4>
                            <p style="font-size: 11px; color: var(--text-secondary); flex: 1;">${c.desc}</p>
                            <div>${actBtn}</div>
                        </div>
                    `;
                }).join('');
            })
            .catch(() => {});
    }

    function fetchSkills() {
        fetch(`${API_BASE}/api/skills`)
            .then(res => res.json())
            .then(skills => {
                const grid = document.getElementById('skillsGrid');
                if (!grid || !Array.isArray(skills)) return;
                grid.innerHTML = skills.map(s => `
                    <div class="skill-card">
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <h4 style="margin: 0; color: var(--accent-cyan); font-family: var(--font-code); font-size: 14px;">⚡ /${s.name}</h4>
                            <span class="status-badge connected">Built-in</span>
                        </div>
                        <p style="font-size: 11px; color: var(--text-secondary);">${s.description}</p>
                    </div>
                `).join('');
            })
            .catch(() => {});
    }

    // ── CONTACTS HUB ──
    window.fetchContacts = function(query = '') {
        const url = query ? `${API_BASE}/api/contacts?query=${encodeURIComponent(query)}` : `${API_BASE}/api/contacts`;
        fetch(url)
            .then(res => res.json())
            .then(data => {
                renderContacts(data.contacts || []);
            })
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
        contactSearchInput.addEventListener('input', (e) => fetchContacts(e.target.value.trim()));
    }

    // ── MODAL HELPERS ──
    window.openContactImportModal = () => document.getElementById('contactImportModal')?.classList.add('active');
    window.closeContactImportModal = () => document.getElementById('contactImportModal')?.classList.remove('active');
    window.openGoogleAuthModal = () => document.getElementById('googleAuthModal')?.classList.add('active');
    window.closeGoogleAuthModal = () => document.getElementById('googleAuthModal')?.classList.remove('active');

    window.triggerFileImport = function(type = 'universal') {
        const inputId = type === 'contact' ? 'contactFileInput' : (type === 'knowledge' ? 'fileImportInput' : 'universalFileInput');
        const input = document.getElementById(inputId);
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
            showToast('Uploading', `Ingesting '${file.name}' into RAG memory...`, 'info');
            fetch(`${API_BASE}/api/import/file`, { method: 'POST', body: formData })
                .then(res => res.json())
                .then(data => showToast('Success', data.message || 'File ingested.', 'success'))
                .catch(err => showToast('Error', `Failed uploading ${file.name}`, 'error'));
        }
    };

    window.uploadContactFile = function(file) {
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        showToast('Importing Contacts', `Parsing '${file.name}'...`, 'info');
        fetch(`${API_BASE}/api/import/contacts`, { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                showToast('Import Success', 'Contacts store updated.', 'success');
                closeContactImportModal();
                fetchContacts();
                fetchConnectors();
            })
            .catch(err => showToast('Import Error', `${err}`, 'error'));
    };

    window.submitContactImportByPath = function() {
        const pathInput = document.getElementById('contactFilePathInput');
        if (!pathInput || !pathInput.value.trim()) {
            showToast('Path Required', 'Please enter a valid file path.', 'error');
            return;
        }
        const formData = new FormData();
        formData.append('file_path', pathInput.value.trim());
        showToast('Importing Contacts', `Reading path...`, 'info');
        fetch(`${API_BASE}/api/import/contacts`, { method: 'POST', body: formData })
            .then(res => res.json())
            .then(data => {
                showToast('Contacts Imported', 'Contacts updated successfully.', 'success');
                closeContactImportModal();
                fetchContacts();
                fetchConnectors();
            })
            .catch(err => showToast('Import Error', `${err}`, 'error'));
    };

    // ── DYNAMIC PARTICLE CANVAS ENGINE ──
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
                ctx.fillStyle = 'rgba(0, 242, 254, 0.5)';
                ctx.fill();
            }
            requestAnimationFrame(render);
        }
        requestAnimationFrame(render);
    }

    fetchConnectors();
    fetchSkills();
    initParticleCanvas();
    setInterval(fetchTelemetry, 5000);
    initWebSocket();
});
