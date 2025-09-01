# Sistema Unificado de Cores - LabConnect

## 🎨 Visão Geral

Este sistema unifica todas as variáveis de cores do frontend em um único arquivo (`unified-variables.css`), eliminando duplicações e inconsistências. Agora existe uma única fonte de verdade para cores, espaçamentos, tipografia e outros tokens de design.

## 📁 Estrutura de Arquivos

### ✅ ARQUIVOS PRINCIPAIS (USAR)
- `unified-variables.css` - **Sistema principal de variáveis**
- `dashboard-base-optimized.css` - Dashboard otimizado
- `floating_chat.css` - Chat otimizado com variáveis unificadas

### ❌ ARQUIVOS LEGADOS (NÃO USAR MAIS)
- `variables.css` - Substituído pelo unified-variables.css
- `materials-dark-mode.css` - Funcionalidade absorvida pelo sistema unificado
- `dark-theme-override.css` - Não mais necessário
- `dashboard-base.css` - Substituído pela versão otimizada

## 🎯 Sistema de Variáveis

### Cores Primárias
```css
--primary-blue: #4a6fa5;           /* Cor principal do sistema */
--primary-blue-light: rgba(74, 111, 165, 0.1);
--primary-blue-dark: #3a5a95;
```

### Cores Neutras (Light Mode)
```css
--neutral-white: #ffffff;
--neutral-gray-50: #f8f9fa;
--neutral-gray-100: #f1f3f4;
/* ... até neutral-gray-900 e neutral-black */
```

### Cores Neutras (Dark Mode)
```css
--dark-bg-primary: #1a1d23;
--dark-bg-secondary: #212529;
--dark-text-primary: #e2e8f0;
--dark-text-secondary: #a0aec0;
```

### Cores de Status
```css
--status-success: #198754;
--status-warning: #ffc107;
--status-danger: #dc3545;
--status-info: #0dcaf0;
```

### Sistema de Mapeamento Inteligente
O sistema mapeia automaticamente as cores baseado no tema:

```css
/* Light Mode */
--bg-primary: var(--neutral-white);
--text-primary: var(--neutral-gray-800);

/* Dark Mode - Remapeamento Automático */
[data-theme="dark"] {
    --bg-primary: var(--dark-bg-primary);
    --text-primary: var(--dark-text-primary);
}
```

## 🚀 Como Usar

### ✅ CORRETO
```css
.minha-classe {
    background-color: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-primary);
    padding: var(--space-md);
    border-radius: var(--radius-md);
}
```

### ❌ EVITAR
```css
.minha-classe {
    background-color: #ffffff; /* Hardcoded */
    color: #2c3e50; /* Hardcoded */
    border: 1px solid #dee2e6; /* Hardcoded */
}
```

## 📋 Tokens Disponíveis

### Espaçamentos
```css
--space-xs: 0.25rem;    /* 4px */
--space-sm: 0.5rem;     /* 8px */
--space-md: 1rem;       /* 16px */
--space-lg: 1.5rem;     /* 24px */
--space-xl: 2rem;       /* 32px */
--space-xxl: 3rem;      /* 48px */
```

### Tipografia
```css
--font-size-xs: 0.75rem;
--font-size-sm: 0.875rem;
--font-size-base: 1rem;
--font-size-lg: 1.125rem;
--font-size-xl: 1.25rem;
--font-size-2xl: 1.5rem;
```

### Border Radius
```css
--radius-sm: 0.25rem;
--radius-md: 0.375rem;
--radius-lg: 0.5rem;
--radius-xl: 1rem;
```

### Sombras
```css
--shadow-sm: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
--shadow-md: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
--shadow-lg: 0 1rem 3rem rgba(0, 0, 0, 0.175);
--shadow-focus: 0 0 0 0.2rem rgba(74, 111, 165, 0.25);
```

### Transições
```css
--transition-fast: 0.15s ease;
--transition-normal: 0.2s ease;
--transition-slow: 0.3s ease;
```

## 🌙 Tema Escuro Automático

O sistema automaticamente aplica as cores corretas baseado no atributo `data-theme="dark"` no elemento HTML. **Não é mais necessário escrever overrides manuais para dark mode.**

### Antes (Problemático)
```css
.card {
    background-color: #ffffff;
}

[data-theme="dark"] .card {
    background-color: #212529 !important;
}
```

### Agora (Automático)
```css
.card {
    background-color: var(--bg-card);
    /* Automaticamente muda para dark quando [data-theme="dark"] */
}
```

## 💡 Benefícios

1. **Consistência**: Uma única fonte de verdade para todas as cores
2. **Manutenibilidade**: Mudanças em um local se aplicam em todo o sistema
3. **Performance**: Menos CSS duplicado
4. **Automação**: Dark mode funciona automaticamente
5. **Escalabilidade**: Fácil adicionar novos tokens
6. **Compatibilidade**: Mantém compatibilidade com Bootstrap

## 🔧 Implementação

### No Template Base
```html
<!-- UNIFIED COLOR SYSTEM (replaces all individual color files) -->
<link rel="stylesheet" href="{% static 'css/unified-variables.css' %}">

<!-- Arquivos otimizados -->
<link rel="stylesheet" href="{% static 'css/dashboard-base-optimized.css' %}">
```

### Em Novos Componentes
```css
.novo-componente {
    background-color: var(--bg-card);
    border: 1px solid var(--border-primary);
    color: var(--text-primary);
    padding: var(--space-md);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
    transition: var(--transition-normal);
}

.novo-componente:hover {
    box-shadow: var(--shadow-md);
}
```

## 🎨 Customização de Cores

Para alterar as cores do sistema, edite apenas o arquivo `unified-variables.css`:

```css
:root {
    /* Altere apenas aqui para mudar em todo o sistema */
    --primary-blue: #2563eb; /* Nova cor primária */
    --status-success: #10b981; /* Nova cor de sucesso */
}
```

## ⚠️ Migração de Arquivos Antigos

### Arquivos a Migrar
1. Procurar por `#` seguido de valores hex em CSS
2. Substituir por variáveis correspondentes
3. Remover overrides de dark mode (agora automático)
4. Testar em ambos os temas

### Script de Migração (Sugestão)
```bash
# Encontrar hardcoded colors
grep -r "background-color: #" staticfiles/css/
grep -r "color: #" staticfiles/css/

# Substituir por variáveis
# background-color: #ffffff → background-color: var(--bg-card)
# color: #2c3e50 → color: var(--text-primary)
```

## 🧪 Testes

Para testar o sistema:

1. Carregar página em tema claro
2. Alternar para tema escuro via JavaScript: `document.documentElement.setAttribute('data-theme', 'dark')`
3. Verificar se todas as cores mudaram adequadamente
4. Verificar consistência visual
5. Testar responsividade

## 📖 Guia Rápido de Variáveis

| Uso | Variável | Descrição |
|-----|----------|-----------|
| Fundo principal | `--bg-primary` | Fundo da página/body |
| Fundo de cards | `--bg-card` | Cards, modais, dropdowns |
| Fundo de inputs | `--bg-input` | Campos de formulário |
| Texto principal | `--text-primary` | Textos principais |
| Texto secundário | `--text-secondary` | Textos menos importantes |
| Texto acinzentado | `--text-muted` | Placeholders, hints |
| Bordas | `--border-primary` | Bordas padrão |
| Bordas sutis | `--border-secondary` | Bordas mais claras |
| Hover | `--bg-hover` | Estados de hover |
| Cor primária | `--primary-blue` | Botões, links, destaque |

---

**🎯 Objetivo**: Sistema de cores mais simples, consistente e fácil de manter para todo o LabConnect frontend.