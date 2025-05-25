// Chat application JavaScript

// Configuration
const API_URL = 'https://eidbi-backend-service-5geiseeama-uc.a.run.app';

// DOM Elements
const messagesContainer = document.getElementById('messagesContainer');
const chatForm = document.getElementById('chatForm');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const clearChatButton = document.getElementById('clearChat');

// Chat state
let isLoading = false;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    messageInput.focus();
    loadChatHistory();
});

// Event Listeners
chatForm.addEventListener('submit', handleSubmit);
clearChatButton.addEventListener('click', clearChat);

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    if (!message || isLoading) return;
    
    // Add user message
    addMessage(message, 'user');
    
    // Clear input
    messageInput.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send to API
    await sendQuery(message);
}

// Add message to chat
function addMessage(content, type) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `flex ${type === 'user' ? 'justify-end' : 'justify-start'} mb-4 message-enter`;
    
    if (type === 'user') {
        messageDiv.innerHTML = `
            <div class="flex items-start gap-2 md:gap-3 max-w-[85%] md:max-w-[80%]">
                <div class="bg-green-600 rounded-2xl px-3 py-2 md:px-4 md:py-3 shadow-md">
                    <p class="text-white text-sm md:text-base">${escapeHtml(content)}</p>
                </div>
                <div class="w-7 h-7 md:w-8 md:h-8 bg-green-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg class="w-4 h-4 md:w-5 md:h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                    </svg>
                </div>
            </div>
        `;
    } else {
        messageDiv.innerHTML = `
            <div class="flex items-start gap-2 md:gap-3 max-w-[85%] md:max-w-[80%]">
                <div class="w-7 h-7 md:w-8 md:h-8 bg-gray-700 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg class="w-4 h-4 md:w-5 md:h-5 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                    </svg>
                </div>
                <div class="bg-gray-700 rounded-2xl px-3 py-2 md:px-4 md:py-3 shadow-md">
                    <p class="text-gray-100 text-sm md:text-base">${formatMessage(content)}</p>
                </div>
            </div>
        `;
    }
    
    messagesContainer.appendChild(messageDiv);
    scrollToBottom();
    
    // Save to local storage
    saveChatHistory();
}

// Show typing indicator
function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.id = 'typingIndicator';
    typingDiv.className = 'flex justify-start mb-4';
    typingDiv.innerHTML = `
        <div class="flex items-start gap-2 md:gap-3">
            <div class="w-7 h-7 md:w-8 md:h-8 bg-gray-700 rounded-full flex items-center justify-center flex-shrink-0">
                <svg class="w-4 h-4 md:w-5 md:h-5 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                </svg>
            </div>
            <div class="bg-gray-700 rounded-2xl shadow-md typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    
    messagesContainer.appendChild(typingDiv);
    scrollToBottom();
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Send query to API
async function sendQuery(query) {
    isLoading = true;
    sendButton.disabled = true;
    
    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query_text: query,
                num_results: 5,
                use_hybrid_search: true,
                use_reranking: true
            })
        });
        
        removeTypingIndicator();
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Add assistant response
        addMessage(data.answer, 'assistant');
        
        // Add metadata if available
        if (data.retrieved_chunk_ids && data.retrieved_chunk_ids.length > 0) {
            addMetadata(data);
        }
        
    } catch (error) {
        console.error('Error:', error);
        removeTypingIndicator();
        addMessage('Sorry, I encountered an error while processing your request. Please try again later.', 'assistant');
    } finally {
        isLoading = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

// Add metadata about the response
function addMetadata(data) {
    const metadataDiv = document.createElement('div');
    metadataDiv.className = 'flex justify-start mb-4 pl-10 md:pl-12';
    metadataDiv.innerHTML = `
        <div class="text-xs text-gray-500">
            <span>Sources: ${data.retrieved_chunk_ids.length} documents</span>
            ${data.cached ? ' • Cached response' : ''}
            ${data.search_method ? ` • ${data.search_method} search` : ''}
        </div>
    `;
    messagesContainer.appendChild(metadataDiv);
}

// Format message content (handle line breaks, etc.)
function formatMessage(content) {
    return content
        .split('\n')
        .map(line => escapeHtml(line))
        .join('<br>');
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Scroll to bottom of chat
function scrollToBottom() {
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Clear chat
function clearChat() {
    // Keep only the welcome message
    const messages = messagesContainer.querySelectorAll('.message-enter');
    for (let i = 1; i < messages.length; i++) {
        messages[i].remove();
    }
    
    // Clear metadata
    const metadata = messagesContainer.querySelectorAll('.pl-10, .pl-12');
    metadata.forEach(m => m.remove());
    
    // Clear local storage
    localStorage.removeItem('chatHistory');
    
    messageInput.focus();
}

// Save chat history to local storage
function saveChatHistory() {
    const messages = [];
    const messageElements = messagesContainer.querySelectorAll('.message-enter');
    
    messageElements.forEach((elem, index) => {
        if (index === 0) return; // Skip welcome message
        
        const isUser = elem.classList.contains('justify-end');
        const content = elem.querySelector('p').textContent;
        messages.push({ type: isUser ? 'user' : 'assistant', content });
    });
    
    localStorage.setItem('chatHistory', JSON.stringify(messages));
}

// Load chat history from local storage
function loadChatHistory() {
    const historyStr = localStorage.getItem('chatHistory');
    if (!historyStr) return;
    
    try {
        const history = JSON.parse(historyStr);
        history.forEach(msg => {
            addMessage(msg.content, msg.type);
        });
    } catch (e) {
        console.error('Failed to load chat history:', e);
    }
}

// Handle Enter key in input
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        chatForm.dispatchEvent(new Event('submit'));
    }
}); 