// static/js/floating_chat.js - versão atualizada completa
document.addEventListener('DOMContentLoaded', function() {
    // Elementos do chat
    const chatContainer = document.getElementById('rafa-chat-container');
    const chatToggle = document.getElementById('rafa-chat-toggle');
    const minimizeBtn = document.getElementById('rafa-minimize-btn');
    const closeBtn = document.getElementById('rafa-close-btn');
    const chatForm = document.getElementById('rafa-chat-form');
    const messageInput = document.getElementById('rafa-message-input');
    const messagesContainer = document.getElementById('rafa-chat-messages');
    const contextInput = document.getElementById('rafa-context-input');
    
    // Função para limpar o histórico do chat
    function clearChatHistory() {
        localStorage.removeItem('rafaChatMessages');
        messagesContainer.innerHTML = `
            <div class="rafa-message assistant-message">
                <div class="rafa-avatar">🤖</div>
                <div class="rafa-text">
                    Olá, eu sou seu assistente virtual. Como posso ajudar você hoje?
                </div>
            </div>
        `;
    }
    
    // Verificar se há mensagens salvas no localStorage
    const savedMessages = localStorage.getItem('rafaChatMessages');
    if (savedMessages) {
        messagesContainer.innerHTML = savedMessages;
        // Rolar para a última mensagem
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Abrir/fechar o chat
    chatToggle.addEventListener('click', function() {
        // Verificar se o chat estava fechado (não apenas minimizado)
        const wasClosed = chatContainer.classList.contains('closed');
        
        chatContainer.classList.toggle('closed');
        chatContainer.classList.remove('minimized');
        chatToggle.style.display = 'none';
        
        // Se o chat estava fechado (não apenas minimizado), então mostramos a mensagem inicial
        if (wasClosed) {
            // O chat foi realmente fechado, então resetamos
            clearChatHistory();
        }
    });
    
    // Minimizar o chat
    minimizeBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        chatContainer.classList.toggle('minimized');
    });
    
    // Fechar o chat com confirmação
    closeBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        
        // Perguntar ao usuário se ele realmente deseja fechar o chat
        if (confirm('Fechar o chat irá apagar todo o histórico da conversa. Tem certeza que deseja fechar?')) {
            chatContainer.classList.add('closed');
            chatToggle.style.display = 'flex';
            
            // Limpar o histórico do chat quando fechado
            clearChatHistory();
        }
        // Se o usuário clicar em "Cancelar", o chat permanecerá aberto com o histórico
    });
    
    // Enviar mensagem
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;
        
        // Adicionar mensagem do usuário
        addMessage(message, 'user');
        
        // Limpar o input
        messageInput.value = '';
        
        // Mostrar indicador de digitação
        showTypingIndicator();
        
        // Enviar para a API
        sendMessageToAPI(message);
    });
    
    // Função para adicionar uma mensagem ao chat
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `rafa-message ${sender}-message`;
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'rafa-avatar';
        avatarDiv.textContent = sender === 'user' ? '👤' : '🤖';
        
        const textDiv = document.createElement('div');
        textDiv.className = 'rafa-text';
        textDiv.textContent = text;
        
        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(textDiv);
        
        messagesContainer.appendChild(messageDiv);
        
        // Rolar para a última mensagem
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        // Salvar mensagens no localStorage apenas se o chat não estiver minimizado ou fechado
        if (!chatContainer.classList.contains('closed')) {
            localStorage.setItem('rafaChatMessages', messagesContainer.innerHTML);
        }
    }
    
    // Mostrar indicador de digitação
    function showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'rafa-message assistant-message typing-indicator-container';
        typingDiv.innerHTML = `
            <div class="rafa-avatar">🤖</div>
            <div class="rafa-text">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return typingDiv;
    }
    
    // Remover indicador de digitação
    function removeTypingIndicator() {
        const typingIndicator = messagesContainer.querySelector('.typing-indicator-container');
        if (typingIndicator) {
            messagesContainer.removeChild(typingIndicator);
        }
    }
    
    // Enviar mensagem para a API
    function sendMessageToAPI(message) {
        const context = contextInput.value;
        
        fetch('/api/assistant/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ message, context })
        })
        .then(response => {
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let accumulatedResponse = '';
            
            return readStream(reader, decoder, accumulatedResponse);
        })
        .catch(error => {
            console.error('Error:', error);
            removeTypingIndicator();
            addMessage('Desculpe, ocorreu um erro na comunicação. Por favor, tente novamente mais tarde.', 'assistant');
        });
    }
    
    // Processar stream de resposta
    function readStream(reader, decoder, accumulatedResponse) {
        reader.read().then(({ done, value }) => {
            if (done) {
                removeTypingIndicator();
                return;
            }
            
            // Decodificar o chunk recebido
            const chunk = decoder.decode(value, { stream: true });
            
            // Processar cada linha do chunk
            const lines = chunk.split('\n');
            lines.forEach(line => {
                if (line.trim() === '') return;
                
                try {
                    const data = JSON.parse(line);
                    
                    if (data.chunk) {
                        // Se é a primeira parte da resposta
                        if (!accumulatedResponse) {
                            removeTypingIndicator();
                            accumulatedResponse = data.chunk;
                            addMessage(data.chunk, 'assistant');
                        } else {
                            // Atualizar a última mensagem
                            const lastMessage = messagesContainer.lastElementChild;
                            const textDiv = lastMessage.querySelector('.rafa-text');
                            textDiv.textContent = data.full;
                            accumulatedResponse = data.full;
                            
                            // Salvar mensagens no localStorage
                            if (!chatContainer.classList.contains('closed')) {
                                localStorage.setItem('rafaChatMessages', messagesContainer.innerHTML);
                            }
                        }
                    }
                } catch (e) {
                    console.error('Error parsing JSON:', e);
                }
            });
            
            // Continuar lendo o stream
            readStream(reader, decoder, accumulatedResponse);
        });
    }
    
    // Função para obter o cookie CSRF
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

    function showFeedbackButtons(messageId) {
        const lastMessage = messagesContainer.lastElementChild;
        const feedbackDiv = document.createElement('div');
        feedbackDiv.className = 'rafa-feedback';
        feedbackDiv.innerHTML = `
            <p>Esta resposta foi útil?</p>
            <button class="rafa-feedback-btn" data-value="good" data-id="${messageId}">
                <i class="bi bi-hand-thumbs-up"></i>
            </button>
            <button class="rafa-feedback-btn" data-value="bad" data-id="${messageId}">
                <i class="bi bi-hand-thumbs-down"></i>
            </button>
        `;
        
        lastMessage.appendChild(feedbackDiv);
        
        // Adicionar event listeners
        const feedbackBtns = feedbackDiv.querySelectorAll('.rafa-feedback-btn');
        feedbackBtns.forEach(btn => {
            btn.addEventListener('click', function() {
                const value = this.dataset.value;
                const id = this.dataset.id;
                sendFeedback(id, value, user_message, accumulated_response);
                
                // Mudar UI para mostrar que o feedback foi recebido
                feedbackDiv.innerHTML = `<p>Obrigado pelo seu feedback!</p>`;
                setTimeout(() => {
                    feedbackDiv.style.display = 'none';
                }, 2000);
            });
        });
    }
    
    // Ocultar botão de toggle inicialmente se o chat estiver aberto
    if (!chatContainer.classList.contains('closed')) {
        chatToggle.style.display = 'none';
    }
});