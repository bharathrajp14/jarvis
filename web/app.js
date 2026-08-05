// web/app.js — BR JARVIS AI Desktop Operating System Client Engine
document.addEventListener('DOMContentLoaded', () => {
    const host = window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const API_BASE = `${protocol}://${host}`;
    const apiKey = localStorage.getItem('jarvis_api_key') || window.JARVIS_API_KEY || '';
    const WS_URL = `${wsProtocol}://${host}/ws${apiKey ? `?token=${encodeURIComponent(apiKey)}` : ''}`;

    function apiFetch(url, options = {}) {
        const opts = Object.assign({}, options);
        opts.headers = Object.assign({}, opts.headers || {});
        if (apiKey) {
            opts.headers['X-API-Key'] = apiKey;
            opts.headers['Authorization'] = `Bearer ${apiKey}`;
        }
        return fetch(url, opts);
    }

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
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        fetch(`${API_BASE}/health`, { signal: controller.signal })
            .then(res => res.json())
            .then(data => {
                clearTimeout(timeoutId);
                if (data.cpu_percent !== undefined) setGauge(cpuRing, cpuValue, data.cpu_percent);
                if (data.memory_percent !== undefined) setGauge(ramRing, ramValue, data.memory_percent);
                if (data.disk_percent !== undefined) setGauge(diskRing, diskValue, data.disk_percent);
            })
            .catch(() => {
                clearTimeout(timeoutId);
            });
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
    let wsReconnectDelay = 1000;
    let wsReconnectTimer = null;

    function initWebSocket() {
        try {
            socket = new WebSocket(WS_URL);

            socket.onopen = () => {
                wsReconnectDelay = 1000;
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
                if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
                wsReconnectTimer = setTimeout(() => {
                    initWebSocket();
                }, wsReconnectDelay);
                wsReconnectDelay = Math.min(wsReconnectDelay * 2, 16000);
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
            taskList.innerHTML = '<div class="panel-hdr">⚡ LIVE SUB-AGENT WORKFLOWS</div>';
            sidebar.appendChild(taskList);
        }
        let card = document.getElementById(`task-card-${taskId}`);
        if (!card) {
            card = document.createElement('div');
            card.id = `task-card-${taskId}`;
            card.className = 'agent-task-card';
            taskList.appendChild(card);
        }
        const st = (status || 'running').toLowerCase();
        const pct = Math.round((progress || 0) * 100);
        card.innerHTML = `
            <div class="task-card-hdr">
                <span class="task-name">🤖 ${name || taskId}</span>
                <span class="task-badge ${st}">${st.toUpperCase()}</span>
            </div>
            <div class="task-progress-track">
                <div class="task-progress-bar ${st}" style="width: ${pct}%"></div>
            </div>
            ${result ? `<div class="task-result">${result}</div>` : ''}
        `;
    }

    function removeWebTaskCard(taskId) {
        const card = document.getElementById(`task-card-${taskId}`);
        if (card) card.remove();
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
        let escaped = String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');

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

    // ── MODAL & INTERACTIVE HELPERS ──
    window.openContactImportModal = () => document.getElementById('contactImportModal')?.classList.add('active');
    window.closeContactImportModal = () => document.getElementById('contactImportModal')?.classList.remove('active');
    window.openGoogleAuthModal = () => document.getElementById('googleAuthModal')?.classList.add('active');
    window.closeGoogleAuthModal = () => document.getElementById('googleAuthModal')?.classList.remove('active');

    window.openAddContactModal = function() {
        const modal = document.getElementById('addContactModal');
        if (modal) modal.classList.add('active');
        else {
            const name = prompt("Enter contact full name:");
            if (!name) return;
            const phone = prompt("Enter phone number (e.g. +1234567890):") || "";
            const email = prompt("Enter email address:") || "";
            const alias = prompt("Enter nickname / alias (e.g. 'Mom'):") || "";
            submitNewContact(name, phone, email, alias);
        }
    };

    window.closeAddContactModal = function() {
        const modal = document.getElementById('addContactModal');
        if (modal) modal.classList.remove('active');
    };

    window.submitNewContactFromForm = function() {
        const name = (document.getElementById('addContactName') || {}).value || '';
        const phone = (document.getElementById('addContactPhone') || {}).value || '';
        const email = (document.getElementById('addContactEmail') || {}).value || '';
        const alias = (document.getElementById('addContactAlias') || {}).value || '';
        if (!name.trim()) {
            showToast('Name Required', 'Please enter a contact name.', 'error');
            return;
        }
        submitNewContact(name.trim(), phone.trim(), email.trim(), alias.trim());
        closeAddContactModal();
    };

    function submitNewContact(name, phone, email, alias) {
        fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: `manage_contacts action='add' name='${name}' phone_number='${phone}' email='${email}' aliases=['${alias}']` })
        })
        .then(res => res.json())
        .then(() => {
            showToast('Contact Saved', `Saved contact '${name}'`, 'success');
            fetchContacts();
            fetchConnectors();
        })
        .catch(() => showToast('Error', 'Failed saving contact', 'error'));
    }

    window.toggleGoogleAuthMode = function() {
        const sel = document.getElementById('googleAuthMode');
        const appGroup = document.getElementById('googleAppPasswordGroup');
        const btn = document.getElementById('submitGoogleAuthBtn');
        if (!sel) return;
        if (sel.value === 'credentials') {
            if (appGroup) appGroup.style.display = 'block';
            if (btn) btn.textContent = 'SAVE GOOGLE CREDENTIALS';
        } else {
            if (appGroup) appGroup.style.display = 'none';
            if (btn) btn.textContent = 'INITIATE GOOGLE LOGIN';
        }
    };

    window.submitGoogleAuth = function() {
        const sel = document.getElementById('googleAuthMode');
        const mode = sel ? sel.value : 'browser';
        if (mode === 'credentials') {
            const email = (document.getElementById('googleEmail') || {}).value || '';
            const pwd = (document.getElementById('googleAppPassword') || {}).value || '';
            if (!email || !pwd) {
                showToast('Fields Required', 'Please provide both Gmail email and 16-character App Password.', 'error');
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
        closeGoogleAuthModal();
        showToast('Google Auth', 'Google login request transmitted to JARVIS.', 'info');
    };

    let recognition = null;
    let isVoiceActive = false;

    window.speakJARVISResponse = function(text) {
        if (!text) return;
        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel();
            const cleanText = text.replace(/<[^>]*>/g, '').replace(/[*_`#]/g, '');
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            const voices = window.speechSynthesis.getVoices();
            const preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Google') || v.name.includes('Natural') || v.name.includes('Male')));
            if (preferredVoice) utterance.voice = preferredVoice;
            window.speechSynthesis.speak(utterance);
        }
    };

    window.triggerVoiceDictation = function() {
        switchView('voiceView');
        const statusBadge = document.getElementById('voiceStatusBadge');
        const transcriptContainer = document.getElementById('liveVoiceTranscript');

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            showToast('Speech STT Unavailable', 'Browser Web Speech API not supported. Falling back to backend audio recording...', 'warning');
            initVoiceAudioVisualizer();
            return;
        }

        if (isVoiceActive && recognition) {
            recognition.stop();
            isVoiceActive = false;
            if (statusBadge) statusBadge.textContent = 'STATUS: IDLE';
            showToast('Voice Muted', 'Microphone listening stopped.', 'info');
            return;
        }

        recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onstart = () => {
            isVoiceActive = true;
            if (statusBadge) statusBadge.textContent = 'STATUS: LISTENING 🎙️';
            showToast('Voice Active', 'Listening for speech or "JARVIS"...', 'success');
            initVoiceAudioVisualizer();
        };

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

            const currentText = finalTranscript || interimTranscript;
            if (transcriptContainer) {
                transcriptContainer.textContent = `"${currentText}"`;
            }

            if (finalTranscript.trim()) {
                showToast('Speech Recognized', `Executing: "${finalTranscript.trim()}"`, 'info');
                if (chatInput) {
                    chatInput.value = finalTranscript.trim();
                    transmitChat();
                }
            }
        };

        recognition.onerror = (evt) => {
            console.warn('Speech Recognition Error:', evt.error);
            if (statusBadge) statusBadge.textContent = `STATUS: ERROR (${evt.error})`;
        };

        recognition.onend = () => {
            if (isVoiceActive) {
                try { recognition.start(); } catch (e) {}
            } else {
                if (statusBadge) statusBadge.textContent = 'STATUS: IDLE';
            }
        };

        try {
            recognition.start();
        } catch (e) {
            console.error('Speech Start Error:', e);
        }
    };

    function initVoiceAudioVisualizer() {
        const cvs = document.getElementById('voiceCanvas');
        if (!cvs) return;
        const ctx = cvs.getContext('2d');
        let width = cvs.width = cvs.parentElement ? cvs.parentElement.clientWidth - 40 : 400;
        let height = cvs.height = 160;
        let phase = 0;

        function drawWave() {
            ctx.clearRect(0, 0, width, height);
            phase += 0.05;
            ctx.beginPath();
            ctx.lineWidth = 3;
            ctx.strokeStyle = '#00f2fe';
            for (let x = 0; x < width; x++) {
                const y = height / 2 + Math.sin(x * 0.02 + phase) * 30 * Math.sin(x * 0.005);
                if (x === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            requestAnimationFrame(drawWave);
        }
        drawWave();
    }

    let allSkills = [];

    window.fetchSkills = function(query = '') {
        fetch(`${API_BASE}/api/skills`)
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
            filtered = skills.filter(s =>
                (s.name && s.name.toLowerCase().includes(q)) ||
                (s.description && s.description.toLowerCase().includes(q))
            );
        }

        if (filtered.length === 0) {
            grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 20px;">No matching skills found.</div>`;
            return;
        }

        grid.innerHTML = filtered.map(s => `
            <div class="skill-card">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <h4 style="margin: 0; color: var(--accent-cyan); font-family: var(--font-code); font-size: 14px;">⚡ /${s.name}</h4>
                    <span class="status-badge connected">Built-in</span>
                </div>
                <p style="font-size: 11px; color: var(--text-secondary); flex: 1;">${s.description}</p>
                <div>
                    <button class="btn btn-secondary" style="width: 100%;" onclick="runSkill('${s.name}')">⚡ Run Skill</button>
                </div>
            </div>
        `).join('');
    }

    window.runSkill = function(skillName) {
        switchView('chatView');
        if (chatInput) {
            chatInput.value = `/${skillName}`;
            transmitChat();
        }
    };

    const skillSearchInput = document.getElementById('skillSearchInput');
    if (skillSearchInput) {
        skillSearchInput.addEventListener('input', (e) => {
            renderSkills(allSkills, e.target.value.trim());
        });
    }

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
