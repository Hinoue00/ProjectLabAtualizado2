// static/js/chatbot.js
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('claude-chat-form');
    const messageInput = document.getElementById('claude-message-input');
    const chatMessages = document.getElementById('claude-chat-messages');
    const contextInput = document.getElementById('claude-context-input');
    
    if (!chatForm || !messageInput || !chatMessages) {
        console.error('Elementos do chatbot não encontrados');
        return;
    }
    
    // Função para adicionar mensagem ao chat
    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isUser ? 'user-message' : 'assistant-message'}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = isUser ? '👤' : '🤖';
        
        const text = document.createElement('div');
        text.className = 'chat-text';
        text.innerHTML = message.replace(/\n/g, '<br>');
        
        if (isUser) {
            messageDiv.appendChild(text);
            messageDiv.appendChild(avatar);
        } else {
            messageDiv.appendChild(avatar);
            messageDiv.appendChild(text);
        }
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageDiv;
    }
    
    // Função para mostrar indicador de digitação
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message assistant-message typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = '🤖';
        
        const text = document.createElement('div');
        text.className = 'chat-text';
        text.innerHTML = '<span class="typing-dots">Digitando<span>.</span><span>.</span><span>.</span></span>';
        
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(text);
        chatMessages.appendChild(typingDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
    
    // Função para remover indicador de digitação
    function removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    // Função para processar resposta em streaming
    async function processStreamingResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentMessage = '';
        let messageElement = null;
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                
                // Processa todas as linhas completas
                for (let i = 0; i < lines.length - 1; i++) {
                    const line = lines[i].trim();
                    if (line) {
                        try {
                            const data = JSON.parse(line);
                            if (data.message && data.message.content) {
                                currentMessage += data.message.content;
                                
                                // Cria o elemento da mensagem se não existir
                                if (!messageElement) {
                                    removeTypingIndicator();
                                    messageElement = addMessage('', false);
                                }
                                
                                // Atualiza o conteúdo da mensagem
                                const textElement = messageElement.querySelector('.chat-text');
                                if (textElement) {
                                    textElement.innerHTML = currentMessage.replace(/\n/g, '<br>');
                                }
                                
                                // Scroll para o final
                                chatMessages.scrollTop = chatMessages.scrollHeight;
                            }
                        } catch (e) {
                            console.error('Erro ao processar linha:', line, e);
                        }
                    }
                }
                
                // Mantém a última linha incompleta no buffer
                buffer = lines[lines.length - 1];
            }
        } catch (error) {
            console.error('Erro no streaming:', error);
            removeTypingIndicator();
            addMessage('Erro ao processar resposta em tempo real.', false);
        }
    }
    
    // Função para enviar mensagem
    async function sendMessage(message) {
        try {
            const response = await fetch('/api/assistant/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    message: message,
                    context: contextInput ? contextInput.value : ''
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Verificar se a resposta é streaming
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                // Resposta em streaming
                await processStreamingResponse(response);
            } else {
                // Resposta JSON normal (fallback)
                const data = await response.json();
                removeTypingIndicator();
                
                if (data.error) {
                    addMessage(`Erro: ${data.error}`, false);
                } else {
                    addMessage(data.response || 'Resposta vazia', false);
                }
            }
            
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            removeTypingIndicator();
            addMessage('Desculpe, ocorreu um erro ao processar sua mensagem. Verifique se o serviço Ollama está funcionando.', false);
        }
    }
    
    // Função para obter CSRF token
    function getCookie(name) {
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
    
    // Event listener para o formulário
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Adicionar mensagem do usuário
        addMessage(message, true);
        
        // Limpar input
        messageInput.value = '';
        
        // Mostrar indicador de digitação
        showTypingIndicator();
        
        // Enviar mensagem
        await sendMessage(message);
    });
    
    // Permitir envio com Enter
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
    
    // Auto-resize do input
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
    
    // Adicionar sugestões rápidas
    const quickSuggestions = [
        'Como agendar um laboratório?',
        'Quem são os laboratoristas?',
        'Como funciona o inventário?',
        'Quando posso fazer agendamentos?'
    ];
    
    // Criar botões de sugestão
    function createQuickSuggestions() {
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.className = 'quick-suggestions';
        
        quickSuggestions.forEach(suggestion => {
            const button = document.createElement('button');
            button.className = 'suggestion-btn';
            button.textContent = suggestion;
            button.onclick = function() {
                messageInput.value = suggestion;
                chatForm.dispatchEvent(new Event('submit'));
            };
            suggestionsDiv.appendChild(button);
        });
        
        chatMessages.appendChild(suggestionsDiv);
    }
    
    // Adicionar sugestões após a mensagem inicial
    setTimeout(createQuickSuggestions, 500);
});

// CSS adicional para melhorar a interface
const style = document.createElement('style');
style.textContent = `
    .typing-indicator .typing-dots span {
        animation: typing 1.4s infinite;
        opacity: 0;
    }
    
    .typing-indicator .typing-dots span:nth-child(1) {
        animation-delay: 0s;
    }
    
    .typing-indicator .typing-dots span:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-indicator .typing-dots span:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes typing {
        0% { opacity: 0; }
        50% { opacity: 1; }
        100% { opacity: 0; }
    }
    
    .chat-message.user-message {
        flex-direction: row-reverse;
    }
    
    .chat-message.user-message .chat-text {
        background-color: #007bff;
        color: white;
        margin-right: 10px;
        margin-left: 0;
    }
    
    .chat-message.assistant-message .chat-text {
        background-color: #f1f1f1;
        color: #333;
        margin-left: 10px;
        margin-right: 0;
    }
    
    .chat-text {
        max-width: 70%;
        padding: 10px 15px;
        border-radius: 18px;
        line-height: 1.4;
        word-wrap: break-word;
        font-size: 14px;
    }
    
    .chat-avatar {
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        flex-shrink: 0;
        margin-top: 5px;
    }
    
    .quick-suggestions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 10px 0;
    }
    
    .suggestion-btn {
        background-color: #e9ecef;
        border: 1px solid #dee2e6;
        border-radius: 15px;
        padding: 5px 12px;
        font-size: 12px;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .suggestion-btn:hover {
        background-color: #007bff;
        color: white;
        border-color: #007bff;
    }
    
    #claude-message-input {
        resize: none;
        min-height: 40px;
        max-height: 120px;
        overflow-y: auto;
    }
`;
document.head.appendChild(style);