// frontend/script.js

const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const logContainer = document.getElementById('log-container');
const debugPanel = document.getElementById('debug-panel');
const sessionList = document.getElementById('session-list');
const newSessionBtn = document.getElementById('new-session-btn');

// State
let currentSessionId = null;
let lastUserMessage = '';

// --- Session Management ---

async function fetchSessions() {
    try {
        const res = await fetch('/sessions');
        const sessions = await res.json();
        renderSessionList(sessions);

        // Auto-select first if none selected
        if (!currentSessionId && sessions.length > 0) {
            switchSession(sessions[0].id);
        }
    } catch (e) {
        console.error("Failed to fetch sessions", e);
    }
}

async function createNewSession() {
    try {
        const res = await fetch('/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: "New Session" })
        });
        const session = await res.json();
        currentSessionId = session.session_id;

        // Refresh list
        await fetchSessions();
        // Clear UI
        chatMessages.innerHTML = `
            <div class="message system">
               <div class="avatar">🤖</div>
               <div class="content"><p>Session Initialized. How can I help?</p></div>
            </div>
        `;
        logContainer.innerHTML = '';
        addLog('New Session Created', 'accent');
    } catch (e) {
        alert("Failed to create session");
    }
}

async function switchSession(sessionId) {
    if (currentSessionId === sessionId) return;
    currentSessionId = sessionId;

    // Highlight active
    document.querySelectorAll('.session-item').forEach(el => {
        el.classList.remove('bg-gray-700', 'text-white');
        el.classList.add('text-gray-400');
        if (el.dataset.id === sessionId) {
            el.classList.add('bg-gray-700', 'text-white');
            el.classList.remove('text-gray-400', 'hover:bg-gray-800');
        }
    });

    // Load History
    chatMessages.innerHTML = ''; // Clear
    addLog(`Loading session ${sessionId}...`, 'muted');

    try {
        const res = await fetch(`/history/${sessionId}`);
        if (res.ok) {
            const data = await res.json();
            const messages = data.messages || [];
            if (messages.length === 0) {
                chatMessages.innerHTML = `
                    <div class="message system">
                       <div class="avatar">🤖</div>
                       <div class="content"><p>Session Ready.</p></div>
                    </div>
                `;
            } else {
                messages.forEach(msg => {
                    addMessage(msg.content, msg.role); // No save needed
                });
            }
        }
    } catch (e) {
        addLog(`Error loading history: ${e}`, 'error');
    }
}

function renderSessionList(sessions) {
    sessionList.innerHTML = '';
    sessions.forEach(s => {
        const div = document.createElement('div');
        div.className = `session-item p-2 rounded cursor-pointer hover:bg-gray-700 text-sm truncate transition-colors ${s.id === currentSessionId ? 'bg-gray-700 text-white' : 'text-gray-400'}`;
        div.textContent = s.title;
        div.dataset.id = s.id;
        div.onclick = () => switchSession(s.id);
        sessionList.appendChild(div);
    });
}

// Auto-expand textarea
userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = userInput.scrollHeight + 'px';
});

// Handle send
async function handleSend(retryMessage = null) {
    const isRetry = !!retryMessage;
    const text = retryMessage || userInput.value.trim();
    if (!text) return;

    if (!isRetry) {
        lastUserMessage = text;
        userInput.value = '';
        userInput.style.height = 'auto';
        addMessage(text, 'user');
    } else {
        addLog(`🔄 Resuming Mission: ${text.substring(0, 30)}...`, 'accent');
    }

    setLoading(true);
    if (!isRetry) {
        addLog(`Mission Started: ${text.substring(0, 30)}...`, 'accent');
    }

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('API request failed');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));

                    // Check for session init
                    if (data.status === 'session_init') {
                        currentSessionId = data.session_id;
                        await fetchSessions(); // Update sidebar title
                        continue;
                    }

                    if (data.status === 'error') {
                        addMessage(`Error: ${data.message}`, 'system');
                        addLog(`Error: ${data.message}`, 'error');
                        continue;
                    }

                    if (data.status === 'input_request') {
                        addLog(`🔑 Auth Required: ${data.update.message}`, 'warning');
                        showAuthModal(data.update.message);
                        return;
                    }

                    if (data.node) {
                        const icon = data.node === 'repair' ? '🔧' : '✅';
                        addLog(`${icon} Node Finished: ${data.node}`, 'muted');
                        if (data.update && data.update.error) {
                            addLog(`⚠️ Issue in ${data.node}: ${data.update.error}`, 'error');
                        }
                    }

                    if (data.response) {
                        addMessage(data.response, 'system');
                    }

                    if (data.update) {
                        updateDebugPanel(data.update);
                    }
                }
            }
        }

        // Refresh session list title (in case it was updated by chat) (Optional optimization: do only if needed)
        fetchSessions();

    } catch (error) {
        addMessage(`Error: ${error.message}`, 'system');
        addLog(`Error: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

function addMessage(text, side) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${side} mb-4 flex ${side === 'user' ? 'justify-end' : 'justify-start'}`;

    // Improve formatting (basic markdown support or newlines)
    const fmtText = text.replace(/\n/g, '<br>');

    const avatar = side === 'user' ? '👤' : '🤖';
    const bubbleClass = side === 'user' ? 'bg-accent-600 text-white rounded-br-none' : 'bg-gray-700 text-gray-200 rounded-bl-none';

    msgDiv.innerHTML = `
        <div class="flex max-w-[80%] ${side === 'user' ? 'flex-row-reverse' : 'flex-row'} items-end gap-2">
            <div class="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center flex-shrink-0 text-sm shadow">${avatar}</div>
            <div class="px-4 py-2 rounded-2xl shadow-md ${bubbleClass}">
                <p class="leading-relaxed">${fmtText}</p>
            </div>
        </div>
    `;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setLoading(isLoading) {
    userInput.disabled = isLoading;
    sendBtn.disabled = isLoading;
    if (isLoading) {
        sendBtn.innerHTML = `
            <svg class="animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
                <path d="M12 2v4m0 12v4M2 12h4m12 0h4" stroke-linecap="round"/>
            </svg>
        `;
    } else {
        sendBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;
    }
}

function addLog(text, className = '') {
    const logItem = document.createElement('div');
    logItem.className = `log-item ${className} py-1 border-b border-gray-800/50 last:border-0`;
    logItem.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;

    // Clear initial muted text if present
    if (logContainer.querySelector('.muted')) {
        logContainer.innerHTML = '';
    }

    logContainer.appendChild(logItem);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function updateDebugPanel(state) {
    if (!state) return;
    debugPanel.classList.remove('translate-x-full'); // Show panel
    if (state.route_action) addLog(`Decision: ${state.route_action.toUpperCase()}`, 'accent');
}

// --- Auth Modal Functions ---
const authModal = document.getElementById('auth-modal');
const authMessage = document.getElementById('auth-message');
const passwordInput = document.getElementById('sudo-password');

function showAuthModal(message) {
    authMessage.textContent = message;
    authModal.classList.add('active');
    passwordInput.focus();
}

function closeAuthModal() {
    authModal.classList.remove('active');
    passwordInput.value = '';
    setLoading(false); // Enable input again
}

async function submitAuth() {
    const password = passwordInput.value;
    if (!password) return;
    try {
        const response = await fetch('/auth', {
            method: 'POST',
            body: JSON.stringify({ password: password })
        });
        if (response.ok) {
            closeAuthModal();
            addLog('✅ Authenticated. Auto-resuming...', 'accent');
            handleSend(lastUserMessage);
        } else {
            alert("Authentication failed.");
        }
    } catch (e) { alert(e.message); }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    fetchSessions(); // Load sessions
});

// Event Listeners
newSessionBtn.addEventListener('click', createNewSession);
sendBtn.addEventListener('click', () => handleSend());
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
});
passwordInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') submitAuth();
});
