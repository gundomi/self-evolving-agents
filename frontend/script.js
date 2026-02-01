// frontend/script.js

const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const logContainer = document.getElementById('log-container');
const debugPanel = document.getElementById('debug-panel');

// Auto-expand textarea
userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = userInput.scrollHeight + 'px';
});

// Handle send
async function handleSend() {
    const text = userInput.value.trim();
    if (!text) return;

    // Reset input
    userInput.value = '';
    userInput.style.height = 'auto';

    // Add user message
    addMessage(text, 'user');

    // Set loading state
    setLoading(true);
    addLog('Thinking...', 'muted');

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });

        if (!response.ok) throw new Error('API request failed');

        const data = await response.json();

        // Add AI response
        addMessage(data.response, 'system');

        // Update debug panel
        updateDebugPanel(data.state);

    } catch (error) {
        addMessage(`Error: ${error.message}`, 'system');
        addLog(`Error: ${error.message}`, 'error');
    } finally {
        setLoading(false);
    }
}

function addMessage(text, side) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${side}`;

    const avatar = side === 'user' ? '👤' : '🤖';

    msgDiv.innerHTML = `
        <div class="avatar">${avatar}</div>
        <div class="content">
            <p>${text}</p>
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
    logItem.className = `log-item ${className}`;
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

    // Show debug panel on first activity
    // debugPanel.classList.add('active'); // Temporarily hidden as it might be too intrusive

    if (state.route_action) {
        addLog(`Decision: ${state.route_action.toUpperCase()}`, 'accent');
    }

    if (state.skill_gen_data && state.skill_gen_data.skill_name) {
        addLog(`Generating Skill: ${state.skill_gen_data.skill_name}`, 'accent');
    }
}

// Event Listeners
sendBtn.addEventListener('click', handleSend);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
});
