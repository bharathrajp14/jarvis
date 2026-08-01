// web/app.js — BR JARVIS AI Desktop Operating System Client

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

    const consoleLog = document.getElementById('consoleLog');
    const clearConsoleBtn = document.getElementById('clearConsoleBtn');

    // Gauges
    const cpuRing = document.getElementById('cpu-ring');
    const ramRing = document.getElementById('ram-ring');
    const diskRing = document.getElementById('disk-ring');
    const cpuValue = document.getElementById('cpu-value');
    const ramValue = document.getElementById('ram-value');
    const diskValue = document.getElementById('disk-value');

    // Command Palette
    const cmdPaletteTrigger = document.getElementById('cmdPaletteTrigger');
    const cmdPaletteModal = document.getElementById('cmdPaletteModal');
    const cmdPaletteInput = document.getElementById('cmdPaletteInput');
    const cmdPaletteResults = document.getElementById('cmdPaletteResults');

    // Modals
    const screenCastModal = document.getElementById('screenCastModal');
    const addMemoryModal = document.getElementById('addMemoryModal');

    let socket = null;
    let isVoiceActive = false;

    // ── SYSTEM TIME ──
    function updateSystemTime() {
        if (systemTimeEl) {
            systemTimeEl.textContent = new Date().toLocaleTimeString();
        }
    }
    setInterval(updateSystemTime, 1000);
    updateSystemTime();

    // ── GAUGE UPDATES ──
    function setGauge(ring, textEl, value) {
        if (!ring || !textEl) return;
        const val = Math.min(100, Math.max(0, parseFloat(value) || 0));
        const offset = 251.2 - (251.2 * val) / 100;
        ring.style.strokeDashoffset = offset;
        textEl.textContent = `${Math.round(val)}%`;
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
            appendLog(`[ROLE] Persona switched to ${role}`, 'sys');
        });
    }

    // ── COMMAND PALETTE (Ctrl + K) ──
    window.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            toggleCmdPalette();
        }
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });

    if (cmdPaletteTrigger) {
        cmdPaletteTrigger.addEventListener('click', toggleCmdPalette);
    }

    function toggleCmdPalette() {
        if (cmdPaletteModal) {
            cmdPaletteModal.classList.toggle('active');
            if (cmdPaletteModal.classList.contains('active') && cmdPaletteInput) {
                cmdPaletteInput.focus();
                cmdPaletteInput.value = '';
            }
        }
    }

    function closeAllModals() {
        document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    }

    window.executePaletteCommand = function(cmd) {
        closeAllModals();
        if (cmd.startsWith('view:')) {
            switchView(cmd.split(':')[1]);
        } else if (cmd.startsWith('cmd:')) {
            executeQuickCommand(cmd.split(':')[1]);
        } else if (cmd.startsWith('model:')) {
            if (backendSelector) {
                backendSelector.value = cmd.split(':')[1];
                backendSelector.dispatchEvent(new Event('change'));
            }
        } else if (cmd.startsWith('role:')) {
            if (roleSelector) roleSelector.value = cmd.split(':')[1];
        }
    };

    // ── QUICK COMMAND EXECUTION ──
    window.executeQuickCommand = function(text) {
        switchView('chatView');
        if (chatInput) {
            chatInput.value = text;
            transmitChat();
        }
    };

    // ── SCREEN SHARE MODAL ──
    window.openScreenShareModal = function() {
        if (screenCastModal) screenCastModal.classList.add('active');
    };

    window.closeScreenShareModal = function() {
        if (screenCastModal) screenCastModal.classList.remove('active');
    };

    window.confirmScreenCast = function() {
        closeScreenShareModal();
        appendLog('[SCREEN_CAST] Sharing active window / entire screen with Live Vision Engine...', 'sys');
        switchView('voiceView');
    };

    // ── WEBSOCKET CONNECTION ──
    function initWebSocket() {
        try {
            socket = new WebSocket(WS_URL);

            socket.onopen = () => {
                appendLog('[SYSTEM] WebSocket Neural Link Connected', 'sys');
                fetchTelemetry();
            };

            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    handleServerMessage(data);
                } catch (e) {
                    appendLog(event.data, 'log');
                }
            };

            socket.onclose = () => {
                appendLog('[SYSTEM] WebSocket Connection Lost — Reconnecting...', 'err');
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
        if (!chatWindow) return;
        if (!chunk) return;
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
        } else if (data.type === 'chat_response') {
            finalizeChatStream();
            appendChatMessage('JARVIS', data.response || data.text || '', 'system');
        } else if (data.type === 'log') {
            appendLog(data.message, 'log');
        }
    }

    // ── CHAT TRANSMISSION ──
    function transmitChat() {
        if (!chatInput) return;
        const text = chatInput.value.strip ? chatInput.value.strip() : chatInput.value.trim();
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

    if (sendChatBtn) {
        sendChatBtn.addEventListener('click', transmitChat);
    }

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
        // Format code blocks
        escaped = escaped.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        // Format inline code
        escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
        // Format bold
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        return escaped.replace(/\n/g, '<br>');
    }

    function appendLog(msg, type = 'sys') {
        if (!consoleLog) return;
        const line = document.createElement('div');
        line.className = `log-line ${type}`;
        line.textContent = msg;
        consoleLog.appendChild(line);
        consoleLog.scrollTop = consoleLog.scrollHeight;
    }

    if (clearConsoleBtn) {
        clearConsoleBtn.addEventListener('click', () => {
            if (consoleLog) consoleLog.innerHTML = '';
        });
    }

    // ── TELEMETRY FETCHING ──
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

    // ── HTML5 DYNAMIC PARTICLE ENGINE ──
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
        const particleCount = Math.min(45, Math.floor(width / 30));

        for (let i = 0; i < particleCount; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.4,
                vy: (Math.random() - 0.5) * 0.4,
                radius: Math.random() * 2 + 1,
                color: Math.random() > 0.5 ? 'rgba(0, 242, 254, ' : 'rgba(121, 40, 202, '
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
                ctx.fillStyle = p.color + '0.6)';
                ctx.fill();

                // Draw connecting laser lines between nearby particles
                for (let j = i + 1; j < particles.length; j++) {
                    const p2 = particles[j];
                    const dx = p.x - p2.x;
                    const dy = p.y - p2.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);

                    if (dist < 130) {
                        ctx.beginPath();
                        ctx.moveTo(p.x, p.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.strokeStyle = p.color + (1 - dist / 130) * 0.15 + ')';
                        ctx.lineWidth = 0.8;
                        ctx.stroke();
                    }
                }
            }

            requestAnimationFrame(render);
        }

        requestAnimationFrame(render);
    }

    // ── CONNECTORS & SKILLS DYNAMIC LOADERS ──
    // ── TOAST NOTIFICATIONS ──
    window.showToast = function(title, message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast-item ${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
        `;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100px)';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    };

    // ── CONNECTORS HUB FETCH ──
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
                        `<button class="act-btn" onclick="openGoogleAuthModal()">🔑 Google Login</button>` :
                        c.name.includes('Contacts') ?
                        `<button class="act-btn" onclick="openContactImportModal()">📥 Import Contacts</button>` :
                        `<button class="act-btn" onclick="executeQuickCommand('run ${c.name} connector')">⚡ Action</button>`;

                    return `
                        <div class="connector-card">
                            <div class="c-header">
                                <span class="c-icon">${c.icon}</span>
                                <span class="status-badge ${badgeClass}">${c.status}</span>
                            </div>
                            <h4 class="c-title">${c.name}</h4>
                            <p class="c-desc">${c.desc}</p>
                            <div class="c-actions">
                                ${actBtn}
                            </div>
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
                            <h4 style="margin: 0; color: var(--accent-cyan); font-family: var(--font-code); font-size: 15px;">⚡ /${s.name}</h4>
                            <span class="status-badge connected">Built-in</span>
                        </div>
                        <p class="s-desc">${s.description}</p>
                        <div class="s-trigger">
                            Triggers: ${(s.triggers || []).join(', ')}
                        </div>
                    </div>
                `).join('');
            })
            .catch(() => {});
    }

    // ── CONTACTS HUB ──
    let allContacts = [];

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    window.fetchContacts = function(query = '') {
        const url = query ? `${API_BASE}/api/contacts?query=${encodeURIComponent(query)}` : `${API_BASE}/api/contacts`;
        fetch(url)
            .then(res => res.json())
            .then(data => {
                allContacts = data.contacts || [];
                renderContacts(allContacts);
            })
            .catch(() => {});
    };

    function renderContacts(list) {
        const grid = document.getElementById('contactsGrid');
        if (!grid) return;

        if (!list || list.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <span class="icon">📱</span>
                    <p>No mobile contacts found matching search filter.</p>
                </div>
            `;
            return;
        }

        const displayList = list.slice(0, 80);
        grid.innerHTML = displayList.map(c => {
            const initial = c.name ? c.name.charAt(0).toUpperCase() : '?';
            const rawName = c.name || 'Unnamed';
            const safeName = escapeHtml(rawName);
            const aliasList = (c.aliases || []).filter(a => a.toLowerCase() !== rawName.toLowerCase());
            const aliasText = aliasList.join(', ');

            return `
                <div class="contact-card">
                    <div class="contact-header">
                        <div class="contact-avatar">${initial}</div>
                        <div class="contact-info">
                            <div class="contact-name">${safeName}</div>
                            ${aliasText ? `<div class="contact-alias">"${escapeHtml(aliasText)}"</div>` : ''}
                        </div>
                    </div>
                    <div class="contact-details">
                        ${c.phone_number ? `<div>📞 ${escapeHtml(c.phone_number)}</div>` : ''}
                        ${c.email ? `<div>✉️ ${escapeHtml(c.email)}</div>` : ''}
                        ${c.notes ? `<div style="font-size: 10px; color: var(--text-muted);">${escapeHtml(c.notes)}</div>` : ''}
                    </div>
                    <div class="contact-actions">
                        <button class="contact-act-btn" onclick="executeQuickCommand('send whatsapp to ${safeName}')">💬 WhatsApp</button>
                        <button class="contact-act-btn" onclick="executeQuickCommand('send email to ${safeName}')">✉️ Email</button>
                    </div>
                </div>
            `;
        }).join('');
    }

    const contactSearchInput = document.getElementById('contactSearchInput');
    if (contactSearchInput) {
        contactSearchInput.addEventListener('input', (e) => {
            const q = e.target.value.trim();
            fetchContacts(q);
        });
    }

    window.openAddContactModal = function() {
        const name = prompt("Enter contact full name:");
        if (!name) return;
        const phone = prompt("Enter phone number (e.g. +1234567890):") || "";
        const email = prompt("Enter email address:") || "";
        const alias = prompt("Enter nickname / alias (e.g. 'Mom'):") || "";

        fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: `manage_contacts action='add' name='${name}' phone_number='${phone}' email='${email}' aliases=['${alias}']` })
        })
        .then(res => res.json())
        .then(data => {
            showToast('Contact Saved', `Saved contact '${name}'`, 'success');
            fetchContacts();
            fetchConnectors();
        })
        .catch(() => showToast('Error', 'Failed saving contact', 'error'));
    };

    // ── FILE IMPORT TRIGGER HELPERS ──
    window.triggerFileImport = function(type = 'universal') {
        let inputId = 'universalFileInput';
        if (type === 'knowledge') inputId = 'fileImportInput';
        else if (type === 'contact') inputId = 'contactFileInput';

        const input = document.getElementById(inputId);
        if (input) {
            input.value = '';
            input.click();
        } else {
            console.warn('File input element not found:', inputId);
        }
    };

    window.triggerVoiceDictation = function() {
        switchView('voiceView');
        showToast('Voice Dictation Active', 'Speak or say "JARVIS" to send voice commands...', 'info');
    };

    // ── FILE & CONTACT DRAG AND DROP INGESTION ──
    function initDragAndDrop() {
        const ragZone = document.getElementById('ragDropzone');
        const fileInput = document.getElementById('fileImportInput');
        const contactZone = document.getElementById('contactDropzone');
        const contactFileInput = document.getElementById('contactFileInput');
        const universalInput = document.getElementById('universalFileInput');

        // Drag & Drop events for Knowledge zone
        if (ragZone) {
            ['dragenter', 'dragover'].forEach(evt => {
                ragZone.addEventListener(evt, (e) => {
                    e.preventDefault();
                    ragZone.classList.add('drag-over');
                }, false);
            });
            ['dragleave', 'drop'].forEach(evt => {
                ragZone.addEventListener(evt, (e) => {
                    e.preventDefault();
                    ragZone.classList.remove('drag-over');
                }, false);
            });
            ragZone.addEventListener('drop', (e) => {
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    uploadKnowledgeFiles(e.dataTransfer.files);
                }
            });
        }

        // Drag & Drop events for Contact zone
        if (contactZone) {
            ['dragenter', 'dragover'].forEach(evt => {
                contactZone.addEventListener(evt, (e) => {
                    e.preventDefault();
                    contactZone.classList.add('drag-over');
                }, false);
            });
            ['dragleave', 'drop'].forEach(evt => {
                contactZone.addEventListener(evt, (e) => {
                    e.preventDefault();
                    contactZone.classList.remove('drag-over');
                }, false);
            });
            contactZone.addEventListener('drop', (e) => {
                if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    uploadContactFile(e.dataTransfer.files[0]);
                }
            });
        }

        // Input change listeners
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    uploadKnowledgeFiles(e.target.files);
                }
            });
        }

        if (contactFileInput) {
            contactFileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    uploadContactFile(e.target.files[0]);
                }
            });
        }

        if (universalInput) {
            universalInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    uploadKnowledgeFiles(e.target.files);
                }
            });
        }
    }

    function uploadKnowledgeFiles(fileList) {
        for (let i = 0; i < fileList.length; i++) {
            const file = fileList[i];
            const formData = new FormData();
            formData.append('file', file);

            showToast('Uploading File', `Ingesting '${file.name}' into vector memory...`, 'info');

            fetch(`${API_BASE}/api/import/file`, {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast('Import Success', data.message, 'success');
                    appendLog(`[FILE_IMPORT] Ingested ${file.name} into vector RAG store`, 'sys');
                } else {
                    showToast('Import Warning', data.message || 'File import complete.', 'info');
                }
            })
            .catch(err => {
                showToast('Import Failed', `Error importing ${file.name}: ${err}`, 'error');
            });
        }
    }

    function uploadContactFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        showToast('Importing Contacts', `Parsing contacts from '${file.name}'...`, 'info');

        fetch(`${API_BASE}/api/import/contacts`, {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success' && data.result) {
                const r = data.result;
                showToast('Contacts Imported', `Imported ${r.imported_new} new contacts. Total store: ${r.total_store}`, 'success');
                closeContactImportModal();
                fetchContacts();
                fetchConnectors();
            } else {
                showToast('Import Failed', data.detail || 'Could not parse contact file.', 'error');
            }
        })
        .catch(err => {
            showToast('Import Error', `Error parsing file: ${err}`, 'error');
        });
    }

    window.submitContactImportByPath = function() {
        const pathInput = document.getElementById('contactFilePathInput');
        if (!pathInput || !pathInput.value.trim()) {
            showToast('Path Required', 'Please enter a valid file path on your computer.', 'error');
            return;
        }
        const filePath = pathInput.value.trim();
        const formData = new FormData();
        formData.append('file_path', filePath);

        showToast('Importing Contacts', `Reading file at '${filePath}'...`, 'info');

        fetch(`${API_BASE}/api/import/contacts`, {
            method: 'POST',
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success' && data.result) {
                const r = data.result;
                showToast('Contacts Imported', `Imported ${r.imported_new} new contacts. Total store: ${r.total_store}`, 'success');
                closeContactImportModal();
                fetchContacts();
                fetchConnectors();
            } else {
                showToast('Import Failed', data.detail || 'Could not find or parse file.', 'error');
            }
        })
        .catch(err => showToast('Error', `Import error: ${err}`, 'error'));
    };

    // ── GOOGLE AUTH MODAL HANDLERS ──
    window.openGoogleAuthModal = function() {
        const modal = document.getElementById('googleAuthModal');
        if (modal) modal.classList.add('active');
    };

    window.closeGoogleAuthModal = function() {
        const modal = document.getElementById('googleAuthModal');
        if (modal) modal.classList.remove('active');
    };

    window.toggleGoogleAuthMode = function() {
        const sel = document.getElementById('googleAuthMode');
        const appGroup = document.getElementById('googleAppPasswordGroup');
        const modeDesc = document.getElementById('googleAuthModeDesc');
        const btn = document.getElementById('submitGoogleAuthBtn');

        if (!sel) return;
        if (sel.value === 'credentials') {
            if (appGroup) appGroup.style.display = 'block';
            if (modeDesc) modeDesc.innerHTML = 'Enter your Gmail email and 16-character Google App Password for automated headless email access.';
            if (btn) btn.textContent = 'SAVE GOOGLE CREDENTIALS';
        } else {
            if (appGroup) appGroup.style.display = 'none';
            if (modeDesc) modeDesc.innerHTML = 'Clicking <strong>Initiate Google Login</strong> will open Google\'s official sign-in page in your default browser.';
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

            executeQuickCommand(`gmail_login mode='credentials' email='${email}' app_password='${pwd}'`);
        } else {
            executeQuickCommand(`gmail_login mode='browser'`);
        }

        closeGoogleAuthModal();
        showToast('Google Auth', 'Google login request transmitted to JARVIS.', 'info');
    };

    // ── CONTACT IMPORT MODAL HANDLERS ──
    window.openContactImportModal = function() {
        const modal = document.getElementById('contactImportModal');
        if (modal) modal.classList.add('active');
    };

    window.closeContactImportModal = function() {
        const modal = document.getElementById('contactImportModal');
        if (modal) modal.classList.remove('active');
    };

    // ── DYNAMIC BACKEND MODEL SELECTOR & SYNCHRONIZER ──
    function initBackendModelSelector() {
        if (!backendSelector) return;

        function syncModels() {
            fetch(`${API_BASE}/api/models`)
                .then(res => res.json())
                .then(models => {
                    const options = [];
                    let defaultVal = 'gemini';
                    
                    for (const [key, details] of Object.entries(models)) {
                        const opt = document.createElement('option');
                        opt.value = key;
                        opt.textContent = `${details.name} (${details.model})`;
                        if (details.is_default) {
                            opt.selected = true;
                            defaultVal = key;
                        }
                        options.push(opt);
                    }
                    
                    if (options.length > 0) {
                        backendSelector.innerHTML = '';
                        options.forEach(opt => backendSelector.appendChild(opt));
                        backendSelector.value = defaultVal;
                    }
                    appendLog('[SYSTEM] Loaded active AI model backends from server', 'sys');
                })
                .catch(err => {
                    console.warn('Failed to load dynamic model list, using fallback options', err);
                });
        }

        syncModels();

        backendSelector.addEventListener('change', (e) => {
            const selectedBackend = e.target.value;
            appendLog(`[SYSTEM] Switching backend to ${selectedBackend.toUpperCase()}...`, 'sys');
            
            fetch(`${API_BASE}/api/backend/switch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ backend: selectedBackend })
            })
            .then(res => {
                if (!res.ok) {
                    throw new Error(`HTTP ${res.status}`);
                }
                return res.json();
            })
            .then(data => {
                appendLog(`[SYSTEM] ${data.message || 'Successfully switched default backend.'}`, 'sys');
            })
            .catch(err => {
                appendLog(`[SYSTEM] Failed to switch backend: ${err.message}`, 'err');
                syncModels();
            });
        });
    }

    initBackendModelSelector();
    fetchConnectors();
    fetchSkills();
    initDragAndDrop();

    initParticleCanvas();
    setInterval(fetchTelemetry, 5000);
    initWebSocket();

    // Register PWA Service Worker for multi-platform support
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/web/sw.js')
                .then((reg) => console.log('[PWA] ServiceWorker registered with scope:', reg.scope))
                .catch((err) => console.warn('[PWA] ServiceWorker registration failed:', err));
        });
    }
});
