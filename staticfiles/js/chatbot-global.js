// static/js/chatbot-global.js
class LabConnectChatbot {
    constructor() {
        this.isOpen = false;
        this.isMinimized = false;
        this.messages = [];
        this.storageKey = 'labconnect_chatbot_state';
        
        this.init();
        this.loadState();
        this.bindEvents();
    }
    
    init() {
        this.toggle = document.getElementById('chatbot-toggle');
        this.modal = document.getElementById('chatbot-modal');
        this.messages_container = document.getElementById('chatbot-messages');
        this.form = document.getElementById('chatbot-form');
        this.input = document.getElementById('chatbot-input');
        this.minimizeBtn = document.getElementById('chatbot-minimize');
        this.closeBtn = document.getElementById('chatbot-close');
        this.badge = document.getElementById('chatbot-badge');
        
        if (!this.toggle || !this.modal) {
            console.error('Elementos do chatbot não encontrados');
            return;
        }
    }
    
    bindEvents() {
        // Toggle do chatbot
        this.toggle.addEventListener('click', () => {
            this.toggleChat();
        });
        
        // Minimizar
        this.minimizeBtn.addEventListener('click', () => {
            this.minimizeChat();
        });
        
        // Fechar
        this.closeBtn.addEventListener('click', () => {
            this.closeChat();
        });
        
        // Enviar mensagem
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Enter para enviar
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Duplo clique no header para minimizar/maximizar
        const header = document.querySelector('.chatbot-header');
        header.addEventListener('dblclick', () => {
            this.isMinimized ? this.maximizeChat() : this.minimizeChat();
        });
        
        // Salvar estado quando a página é fechada
        window.addEventListener('beforeunload', () => {
            this.saveState();
        });
        
        // Carregar estado quando a página é carregada
        window.addEventListener('load', () => {
            this.loadState();
        });
    }
    
    toggleChat() {
        if (this.isOpen) {
            this.closeChat();
        } else {
            this.openChat();
        }
    }
    
    openChat() {
        this.isOpen = true;
        this.isMinimized = false;
        this.modal.classList.add('show');
        this.modal.classList.remove('minimized');
        this.toggle.classList.add('has-chat');
        this.input.focus();
        this.hideNotification();
        this.saveState();
    }
    
    closeChat() {
        this.isOpen = false;
        this.isMinimized = false;
        this.modal.classList.remove('show', 'minimized');
        this.toggle.classList.remove('has-chat');
        this.saveState();
    }
    
    minimizeChat() {
        this.isMinimized = true;
        this.modal.classList.add('minimized');
        this.saveState();
    }
    
    maximizeChat() {
        this.isMinimized = false;
        this.modal.classList.remove('minimized');
        this.input.focus();
        this.saveState();
    }
    
    addMessage(text, isUser = false) {
        const messageData = {
            text: text,
            isUser: isUser,
            timestamp: new Date().toISOString()
        };
        
        this.messages.push(messageData);
        this.renderMessage(messageData);
        this.saveState();
        
        // Scroll para o final
        this.messages_container.scrollTop = this.messages_container.scrollHeight;
        
        // Mostrar notificação se o chat estiver fechado
        if (!this.isOpen && !isUser) {
            this.showNotification();
        }
    }
    
    renderMessage(messageData) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${messageData.isUser ? 'user-message' : 'assistant-message'}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = messageData.isUser ? '👤' : '🤖';
        
        const text = document.createElement('div');
        text.className = 'chat-text';
        text.innerHTML = messageData.text.replace(/\n/g, '<br>');
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(text);
        
        this.messages_container.appendChild(messageDiv);
        
        return messageDiv;
    }
    
    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message assistant-message';
        typingDiv.id = 'typing-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'chat-avatar';
        avatar.textContent = '🤖';
        
        const text = document.createElement('div');
        text.className = 'chat-text typing-indicator';
        text.innerHTML = 'Digitando<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(text);
        
        this.messages_container.appendChild(typingDiv);
        this.messages_container.scrollTop = this.messages_container.scrollHeight;
        
        return typingDiv;
    }
    
    removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
    
    async sendMessage() {
        const message = this.input.value.trim();
        if (!message) return;
        
        // Adicionar mensagem do usuário
        this.addMessage(message, true);
        
        // Limpar input
        this.input.value = '';
        
        // Mostrar indicador de digitação
        this.showTypingIndicator();
        
        try {
            const response = await fetch('/api/assistant/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken')
                },
                body: JSON.stringify({
                    message: message,
                    context: this.getPageContext()
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Processar resposta em streaming
            await this.processStreamingResponse(response);
            
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            this.removeTypingIndicator();
            this.addMessage('Desculpe, ocorreu um erro ao processar sua mensagem. Verifique se o serviço está funcionando.', false);
        }
    }
    
    async processStreamingResponse(response) {
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
                
                for (let i = 0; i < lines.length - 1; i++) {
                    const line = lines[i].trim();
                    if (line) {
                        try {
                            const data = JSON.parse(line);
                            if (data.chunk) {
                                currentMessage += data.chunk;
                                
                                if (!messageElement) {
                                    this.removeTypingIndicator();
                                    const messageData = {
                                        text: currentMessage,
                                        isUser: false,
                                        timestamp: new Date().toISOString()
                                    };
                                    messageElement = this.renderMessage(messageData);
                                    this.messages.push(messageData);
                                }
                                
                                // Atualizar conteúdo
                                const textElement = messageElement.querySelector('.chat-text');
                                if (textElement) {
                                    textElement.innerHTML = currentMessage.replace(/\n/g, '<br>');
                                }
                                
                                // Scroll para o final
                                this.messages_container.scrollTop = this.messages_container.scrollHeight;
                            }
                        } catch (e) {
                            console.error('Erro ao processar linha:', line, e);
                        }
                    }
                }
                
                buffer = lines[lines.length - 1];
            }
            
            // Atualizar a mensagem final no array
            if (messageElement && this.messages.length > 0) {
                this.messages[this.messages.length - 1].text = currentMessage;
                this.saveState();
            }
            
        } catch (error) {
            console.error('Erro no streaming:', error);
            this.removeTypingIndicator();
            this.addMessage('Erro ao processar resposta em tempo real.', false);
        }
    }
    
    getPageContext() {
        const path = window.location.pathname;
        let context = `Usuário está na página: ${path}`;
        
        if (path.includes('dashboard')) {
            context += ' - Dashboard';
        } else if (path.includes('laboratories')) {
            context += ' - Laboratórios';
        } else if (path.includes('inventory')) {
            context += ' - Inventário';
        } else if (path.includes('scheduling')) {
            context += ' - Agendamentos';
        } else if (path.includes('reports')) {
            context += ' - Relatórios';
        }
        
        return context;
    }
    
    showNotification() {
        this.badge.style.display = 'flex';
        this.badge.textContent = '1';
        
        // Piscar o botão
        this.toggle.style.animation = 'pulse 1s infinite';
    }
    
    hideNotification() {
        this.badge.style.display = 'none';
        this.toggle.style.animation = '';
    }
    
    saveState() {
        const state = {
            isOpen: this.isOpen,
            isMinimized: this.isMinimized,
            messages: this.messages.slice(-20), // Manter apenas as últimas 20 mensagens
            timestamp: new Date().toISOString()
        };
        
        try {
            localStorage.setItem(this.storageKey, JSON.stringify(state));
        } catch (e) {
            console.error('Erro ao salvar estado do chatbot:', e);
        }
    }
    
    loadState() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (!saved) return;
            
            const state = JSON.parse(saved);
            
            // Verificar se o estado não é muito antigo (mais de 1 dia)
            const stateAge = new Date() - new Date(state.timestamp);
            if (stateAge > 24 * 60 * 60 * 1000) {
                this.clearState();
                return;
            }
            
            this.messages = state.messages || [];
            
            // Renderizar mensagens salvas
            this.messages_container.innerHTML = '';
            this.messages.forEach(message => {
                this.renderMessage(message);
            });
            
            // Restaurar estado visual
            if (state.isOpen) {
                this.openChat();
                if (state.isMinimized) {
                    this.minimizeChat();
                }
            }
            
        } catch (e) {
            console.error('Erro ao carregar estado do chatbot:', e);
            this.clearState();
        }
    }
    
    clearState() {
        try {
            localStorage.removeItem(this.storageKey);
        } catch (e) {
            console.error('Erro ao limpar estado:', e);
        }
    }
    
    getCookie(name) {
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
}

// Inicializar o chatbot quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    window.labConnectChatbot = new LabConnectChatbot();
});

// Funcionalidades adicionais
document.addEventListener('DOMContentLoaded', function() {
    // Adicionar atalho de teclado (Ctrl + /)
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === '/') {
            e.preventDefault();
            window.labConnectChatbot.toggleChat();
        }
    });
    
    // Fechar com Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && window.labConnectChatbot.isOpen) {
            window.labConnectChatbot.closeChat();
        }
    });
});