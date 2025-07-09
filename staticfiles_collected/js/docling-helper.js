// static/js/docling-helper.js
class DoclingHelper {
    constructor() {
        this.initialized = false;
        this.initElements();
    }
    
    initElements() {
        // Encontrar todos os elementos que usam docling
        this.analyzeFields = document.querySelectorAll('.docling-analyze');
        
        if (this.analyzeFields.length > 0) {
            this.initialized = true;
            this.setupEventListeners();
        }
    }
    
    setupEventListeners() {
        this.analyzeFields.forEach(field => {
            field.addEventListener('input', this.debounce(event => {
                this.handleFieldInput(event.target);
            }, 500));
        });
    }
    
    handleFieldInput(field) {
        const text = field.value;
        if (text.length < 10) return; // Texto muito curto
        
        const targetId = field.dataset.target;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        
        // Fazer requisição para analisar
        fetch('/inventory/api/analyze-description/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                description: text
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error('Erro na análise:', data.error);
                return;
            }
            
            // Atualizar interface com base nos resultados
            this.updateSuggestions(data, targetId);
        })
        .catch(error => {
            console.error('Erro ao analisar texto:', error);
        });
    }
    
    updateSuggestions(data, targetId) {
        // Mostrar sugestões na interface
        const suggestionsBox = document.getElementById('docling-suggestions');
        if (!suggestionsBox) return;
        
        // Mostrar a caixa de sugestões
        suggestionsBox.style.display = 'block';
        
        // Atualizar a categoria sugerida
        const categorySpan = document.getElementById('category-suggestion');
        if (categorySpan) {
            categorySpan.textContent = data.suggested_category_display;
        }
        
        // Atualizar as palavras-chave
        const keywordsContainer = document.getElementById('keywords-container');
        if (keywordsContainer) {
            keywordsContainer.innerHTML = '';
            data.keywords.forEach(keyword => {
                const chip = document.createElement('span');
                chip.className = 'suggestion-chip';
                chip.textContent = keyword;
                keywordsContainer.appendChild(chip);
            });
        }
        
        // Se tiver um ID de categoria, selecionar automaticamente
        if (targetId === 'category' && data.suggested_category_id) {
            const categorySelect = document.getElementById('id_category');
            if (categorySelect) {
                categorySelect.value = data.suggested_category_id;
            }
        }
    }
    
    debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
}

// Inicializar quando o documento estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    window.doclingHelper = new DoclingHelper();
});