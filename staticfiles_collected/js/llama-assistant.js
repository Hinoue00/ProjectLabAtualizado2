// static/js/llama-assistant.js - Versão OpenRouter

document.addEventListener('DOMContentLoaded', function() {
    const messageForm = document.getElementById('claude-chat-form');
    const messageInput = document.getElementById('claude-message-input');
    const contextInput = document.getElementById('claude-context-input');
    const chatMessages = document.getElementById('claude-chat-messages');
    
    if (!messageForm || !messageInput || !chatMessages) {
        console.error('Chat elements not found');
        return;
    }
    
    // Function to add a message to the chat
    function addMessage(text, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user-message' : 'assistant-message'}`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'chat-avatar';
        avatarDiv.textContent = isUser ? '👤' : '🤖';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'chat-text';
        textDiv.textContent = text;
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(textDiv);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return textDiv; // Return the text div for updating later
    }
    
    // Function to add a typing indicator
    function addTypingIndicator() {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message assistant-message';
        messageDiv.id = 'typing-indicator';
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'chat-avatar';
        avatarDiv.textContent = '🤖';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'chat-text typing-indicator';
        
        // Add the animated dots
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            textDiv.appendChild(dot);
        }
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(textDiv);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageDiv;
    }
    
    // Function to remove typing indicator
    function removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    // Handle form submission
    messageForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const userMessage = messageInput.value.trim();
        const context = contextInput.value || '';
        
        if (userMessage === '') return;
        
        // Add user message to chat
        addMessage(userMessage, true);
        
        // Clear input
        messageInput.value = '';
        
        // Add typing indicator
        const typingIndicator = addTypingIndicator();
        
        try {
            // Send request to API with streaming
            const response = await fetch('/api/assistant/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    message: userMessage,
                    context: context
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Remove typing indicator
            removeTypingIndicator();
            
            // Create a placeholder for the assistant's response
            const responseTextDiv = addMessage('', false);
            
            // Use a reader to read the streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { value, done } = await reader.read();
                
                if (done) break;
                
                // Decode the chunk and parse the JSON
                const chunk = decoder.decode(value, { stream: true });
                
                // Split by newline in case multiple JSON objects are received
                const lines = chunk.split('\n').filter(line => line.trim());
                
                for (const line of lines) {
                    try {
                        const data = JSON.parse(line);
                        
                        if (data.error) {
                            console.error('Error from API:', data.error);
                            responseTextDiv.textContent = 'Desculpe, ocorreu um erro ao processar sua solicitação.';
                        } else if (data.chunk) {
                            // Update the response text with the full text so far
                            responseTextDiv.textContent = data.full;
                            chatMessages.scrollTop = chatMessages.scrollHeight;
                        }
                    } catch (error) {
                        console.error('Error parsing JSON:', error, line);
                    }
                }
            }
            
        } catch (error) {
            console.error('Error:', error);
            removeTypingIndicator();
            addMessage('Desculpe, ocorreu um erro ao processar sua solicitação. Por favor, tente novamente mais tarde.');
        }
    });
    
    // Get CSRF token from cookies
    function getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});