// frontend/script.js

const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const logContainer = document.getElementById('log-container');
// const debugPanel = document.getElementById('debug-panel'); // Removed in v3 layout
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

// --- Strategy Graph ---
let currentDag = null;
let lastGraphState = { currentNodeId: null, completedNodes: [] };

async function renderGraph(dag, currentNodeId, completedNodes = []) {
    if (!dag || !dag.nodes) return;
    currentDag = dag;

    const graphDiv = document.getElementById('strategy-graph');

    // Construct Mermaid Syntax
    let graphDef = 'graph TD\n';

    // Nodes
    dag.nodes.forEach(node => {
        // Sanitize ID
        const safeId = node.id.replace(/[^a-zA-Z0-9]/g, '_');
        // Truncate task text
        const label = node.task.length > 20 ? node.task.substring(0, 18) + '...' : node.task;
        graphDef += `    ${safeId}["${label}"]\n`;
    });

    // Edges
    dag.nodes.forEach(node => {
        const safeId = node.id.replace(/[^a-zA-Z0-9]/g, '_');
        if (node.dependencies) {
            node.dependencies.forEach(dep => {
                const safeDep = dep.replace(/[^a-zA-Z0-9]/g, '_');
                graphDef += `    ${safeDep} --> ${safeId}\n`;
            });
        }
    });

    // Styles
    completedNodes.forEach(nodeId => {
        const safeId = nodeId.replace(/[^a-zA-Z0-9]/g, '_');
        graphDef += `    style ${safeId} fill:#064e3b,stroke:#059669,stroke-width:2px,color:#fff\n`; // Green-ish
    });

    if (currentNodeId) {
        const safeId = currentNodeId.replace(/[^a-zA-Z0-9]/g, '_');
        graphDef += `    style ${safeId} fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,stroke-dasharray: 5 5,color:#fff\n`; // Blue active
    }

    // Default style for others
    graphDef += `    classDef default fill:#1f2937,stroke:#374151,color:#cbd5e1\n`;

    // Render
    try {
        const { svg } = await mermaid.render('graphDiv', graphDef);
        graphDiv.innerHTML = svg;
    } catch (e) {
        console.warn("Mermaid render failed", e);
    }
}

// --- Modal Logic ---
const strategyModal = document.getElementById('strategy-modal');

function showStrategyModal() {
    strategyModal.showModal();
    if (currentDag && currentDag.nodes) {
        renderGraph(currentDag, lastGraphState.currentNodeId, lastGraphState.completedNodes);
    }
}

function closeStrategyModal() {
    strategyModal.close();
}

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

    // Flag for new DAG
    let hasDagUpdate = false;

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

                    // --- Render DAG if present ---
                    if (data.dag) {
                        hasDagUpdate = true;
                        currentDag = data.dag;
                        const update = data.update || {};

                        lastGraphState = {
                            currentNodeId: update.current_node_id,
                            completedNodes: update.completed_nodes || []
                        };

                        // If modal is open, auto-refresh
                        if (strategyModal.open) {
                            await renderGraph(currentDag, lastGraphState.currentNodeId, lastGraphState.completedNodes);
                        }
                    }

                    if (data.node) {
                        const icon = data.node === 'repair' ? '🔧' : '✅';
                        if (['supervisor', 'decomposer', 'executor', 'repair', 'reply'].includes(data.node)) {
                            addLog(`${icon} Node Finished: ${data.node}`, 'muted');
                        }

                        if (data.update && data.update.error) {
                            addLog(`⚠️ Issue in ${data.node}: ${data.update.error}`, 'error');
                        }
                    }

                    if (data.response) {
                        console.log("📨 Response received, hasDagUpdate:", hasDagUpdate);
                        addMessage(data.response, 'system', hasDagUpdate);
                    }

                    if (data.update) {
                        updateDebugPanel(data.update);
                    }
                }
            }
        }

        // Refresh session list title
        fetchSessions();

    } catch (error) {
        addMessage(`Error: ${error.message}`, 'system');
        addLog(`Error: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

function addMessage(text, side, hasStrategy = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${side} mb-5 flex ${side === 'user' ? 'justify-start' : 'justify-end'}`;

    // Improve formatting (basic markdown support or newlines)
    const fmtText = text.replace(/\n/g, '<br>');

    const avatar = side === 'user' ? '👤' : '🤖';
    const bubbleClass = side === 'user'
        ? 'bg-accent-600 text-white rounded-bl-none shadow-sm shadow-accent-600/20'
        : 'bg-gray-800/70 text-gray-100 rounded-br-none border border-gray-700/60 shadow-sm';

    let actionBtn = '';
    if (hasStrategy && side === 'system') {
        actionBtn = `
            <div class="mt-3 pt-3 border-t border-white/10">
                <button onclick="showStrategyModal()" class="group flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 hover:border-emerald-500/50 transition-all duration-200">
                    <svg class="w-4 h-4 text-emerald-400 group-hover:scale-110 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 7m0 13V7m0 0L9 7"/>
                    </svg>
                    <span class="text-xs font-semibold text-emerald-300 group-hover:text-emerald-200">View Strategy Map</span>
                </button>
            </div>
        `;
    }

    msgDiv.innerHTML = `
        <div class="flex max-w-[75%] ${side === 'user' ? 'flex-row' : 'flex-row-reverse'} items-end gap-3">
            <div class="w-9 h-9 rounded-full ${side === 'user' ? 'bg-accent-600' : 'bg-gray-800 border border-gray-700'} flex items-center justify-center flex-shrink-0 text-base shadow-sm">${avatar}</div>
            <div class="px-4 py-3 rounded-2xl ${bubbleClass}">
                <p class="leading-relaxed text-sm">${fmtText}</p>
                ${actionBtn}
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
    // Panel is now permanent, so we don't need to toggle visibility classes
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
