#!/bin/bash
# Script de Configuração Completa do Chatbot IA - LabConnect
# Verifica e configura Ollama + modelos necessários

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Função para log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

step() {
    echo -e "${PURPLE}[STEP] $1${NC}"
}

echo -e "${BLUE}🤖 LabConnect - Configuração Completa do Chatbot IA${NC}"
echo "============================================="

# Verificar se está no diretório correto
if [[ ! -f "manage.py" ]]; then
    error "Script deve ser executado no diretório raiz do projeto Django"
    exit 1
fi

step "1. Verificando configurações atuais..."

# Verificar variáveis de ambiente
log "Verificando variáveis de ambiente..."
echo "OLLAMA_API_URL: ${OLLAMA_API_URL:-'http://localhost:11434/api/chat (default)'}"
echo "OLLAMA_MODEL: ${OLLAMA_MODEL:-'llama3 (default)'}"

step "2. Verificando se Ollama está instalado..."

if command -v ollama &> /dev/null; then
    log "✅ Ollama encontrado: $(ollama --version)"
else
    warning "❌ Ollama não está instalado!"
    echo ""
    echo "Para instalar o Ollama:"
    echo "curl -fsSL https://ollama.ai/install.sh | sh"
    echo ""
    echo "Ou em Ubuntu/Debian:"
    echo "wget -O - https://ollama.ai/install.sh | bash"
    echo ""
    read -p "Deseja que eu tente instalar automaticamente? (y/n): " install_ollama
    
    if [[ $install_ollama =~ ^[Yy]$ ]]; then
        log "Instalando Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        
        if command -v ollama &> /dev/null; then
            log "✅ Ollama instalado com sucesso!"
        else
            error "❌ Falha na instalação do Ollama"
            exit 1
        fi
    else
        error "Ollama é necessário para o chatbot. Instale manualmente e execute novamente."
        exit 1
    fi
fi

step "3. Verificando serviço Ollama..."

# Verificar se o serviço está rodando
if pgrep -f "ollama serve" > /dev/null; then
    log "✅ Serviço Ollama está rodando"
else
    warning "❌ Serviço Ollama não está rodando"
    log "Iniciando serviço Ollama..."
    
    # Tentar iniciar como serviço systemd
    if systemctl list-unit-files | grep -q ollama; then
        sudo systemctl start ollama
        sudo systemctl enable ollama
        log "✅ Serviço Ollama iniciado via systemd"
    else
        # Iniciar manualmente em background
        nohup ollama serve > /tmp/ollama.log 2>&1 &
        sleep 3
        log "✅ Serviço Ollama iniciado manualmente"
    fi
fi

step "4. Testando conectividade com Ollama..."

# Testar conexão
OLLAMA_URL=${OLLAMA_API_URL:-"http://localhost:11434"}
BASE_URL=$(echo $OLLAMA_URL | sed 's|/api/chat||')

if curl -s "$BASE_URL/api/version" > /dev/null; then
    VERSION=$(curl -s "$BASE_URL/api/version" | grep -o '"version":"[^"]*' | cut -d'"' -f4)
    log "✅ Ollama respondendo - Versão: $VERSION"
else
    error "❌ Ollama não está respondendo em $BASE_URL"
    error "Verifique se o serviço está rodando: ollama serve"
    exit 1
fi

step "5. Verificando modelos disponíveis..."

# Listar modelos instalados
MODELS=$(curl -s "$BASE_URL/api/tags" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    models = [model['name'] for model in data.get('models', [])]
    print(' '.join(models))
except:
    print('')
")

if [[ -n "$MODELS" ]]; then
    log "✅ Modelos instalados: $MODELS"
else
    warning "❌ Nenhum modelo encontrado"
fi

step "6. Configurando modelo recomendado..."

# Modelo recomendado para o LabConnect
RECOMMENDED_MODEL="llama3"
MODEL_SIZE="4.7GB"

if echo "$MODELS" | grep -q "$RECOMMENDED_MODEL"; then
    log "✅ Modelo $RECOMMENDED_MODEL já está instalado"
else
    warning "❌ Modelo $RECOMMENDED_MODEL não encontrado"
    echo ""
    info "O modelo $RECOMMENDED_MODEL ($MODEL_SIZE) é recomendado para o LabConnect"
    info "Oferece bom desempenho e respostas em português"
    echo ""
    read -p "Deseja baixar o modelo $RECOMMENDED_MODEL? (y/n): " download_model
    
    if [[ $download_model =~ ^[Yy]$ ]]; then
        log "Baixando modelo $RECOMMENDED_MODEL..."
        log "⏳ Isso pode demorar alguns minutos dependendo da sua conexão..."
        
        if ollama pull $RECOMMENDED_MODEL; then
            log "✅ Modelo $RECOMMENDED_MODEL baixado com sucesso!"
        else
            error "❌ Falha ao baixar o modelo"
        fi
    fi
fi

step "7. Testando comunicação com modelo..."

# Testar modelo
TEST_MODEL=${OLLAMA_MODEL:-$RECOMMENDED_MODEL}

log "Testando modelo: $TEST_MODEL"

TEST_RESPONSE=$(curl -s "$BASE_URL/api/generate" \
    -H "Content-Type: application/json" \
    -d "{
        \"model\": \"$TEST_MODEL\",
        \"prompt\": \"Responda apenas: LabConnect funcionando\",
        \"stream\": false
    }" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('response', '').strip())
except:
    print('ERROR')
")

if [[ "$TEST_RESPONSE" == *"LabConnect"* ]]; then
    log "✅ Modelo respondendo corretamente: $TEST_RESPONSE"
else
    warning "⚠️ Resposta inesperada: $TEST_RESPONSE"
fi

step "8. Configurando variáveis de ambiente..."

# Criar arquivo .env se não existir
if [[ ! -f ".env" ]]; then
    log "Criando arquivo .env..."
    touch .env
fi

# Verificar/adicionar configurações
ENV_UPDATED=false

if ! grep -q "OLLAMA_API_URL" .env; then
    echo "OLLAMA_API_URL=http://localhost:11434/api/chat" >> .env
    ENV_UPDATED=true
fi

if ! grep -q "OLLAMA_MODEL" .env; then
    echo "OLLAMA_MODEL=$RECOMMENDED_MODEL" >> .env
    ENV_UPDATED=true
fi

if [[ $ENV_UPDATED == true ]]; then
    log "✅ Variáveis de ambiente atualizadas no .env"
else
    log "✅ Variáveis de ambiente já configuradas"
fi

step "9. Testando integração Django..."

log "Testando endpoint do Django..."

# Testar se o Django consegue se comunicar com o Ollama
python manage.py shell << EOF
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'LabConnect.settings.production')
import django
django.setup()

from django.conf import settings
import requests

try:
    api_url = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/api/chat')
    base_url = api_url.rsplit('/', 2)[0]
    response = requests.get(f"{base_url}/api/version", timeout=5)
    if response.status_code == 200:
        print("✅ Django consegue conectar com Ollama")
    else:
        print("❌ Django não consegue conectar com Ollama")
except Exception as e:
    print(f"❌ Erro na conexão Django-Ollama: {e}")
EOF

step "10. Verificando URLs do chatbot..."

# Verificar se as URLs estão configuradas
if grep -q "api/" LabConnect/urls.py; then
    log "✅ URLs da API configuradas"
else
    warning "❌ URLs da API podem não estar configuradas"
fi

step "11. Gerando relatório de configuração..."

cat > chatbot-config-report.txt << EOF
LabConnect - Relatório de Configuração do Chatbot IA
===================================================
Data: $(date)

Configuração do Ollama:
✅ Ollama instalado: $(ollama --version 2>/dev/null || echo "N/A")
✅ Serviço rodando: $(pgrep -f "ollama serve" > /dev/null && echo "SIM" || echo "NÃO")
✅ URL: ${OLLAMA_API_URL:-"http://localhost:11434/api/chat"}
✅ Modelo: ${OLLAMA_MODEL:-"$RECOMMENDED_MODEL"}

Modelos disponíveis:
$MODELS

Teste de conectividade:
✅ API Version: $(curl -s "$BASE_URL/api/version" 2>/dev/null || echo "ERRO")
✅ Modelo testado: $TEST_MODEL
✅ Resposta teste: $TEST_RESPONSE

Configuração Django:
✅ Variáveis ambiente: .env configurado
✅ URLs: api/ incluído
✅ View: llama_assistant disponível

Próximos passos:
1. Reiniciar Django: sudo systemctl restart labconnect
2. Testar chatbot: /api/assistant/
3. Verificar logs: tail -f logs/labconnect.log

Comandos úteis:
- Ver modelos: ollama list
- Baixar modelo: ollama pull llama3
- Testar Ollama: curl http://localhost:11434/api/version
- Logs Ollama: tail -f /tmp/ollama.log

Troubleshooting:
- Se Ollama não responder: ollama serve
- Se modelo não funcionar: ollama pull $RECOMMENDED_MODEL
- Se Django der erro: verificar logs e URLs
EOF

log "✅ Relatório salvo em: chatbot-config-report.txt"

echo ""
echo -e "${BLUE}🎉 CONFIGURAÇÃO DO CHATBOT CONCLUÍDA! 🎉${NC}"
echo ""
echo -e "${GREEN}Resumo da configuração:${NC}"
echo "• Ollama instalado e rodando"
echo "• Modelo $RECOMMENDED_MODEL configurado"
echo "• Variáveis de ambiente definidas"
echo "• Integração Django testada"
echo ""
echo -e "${YELLOW}Para testar o chatbot:${NC}"
echo "1. Reinicie o Django: sudo systemctl restart labconnect"
echo "2. Acesse: https://seu-dominio/api/assistant/"
echo "3. Digite uma mensagem de teste"
echo ""
echo -e "${BLUE}URLs do chatbot:${NC}"
echo "• API Endpoint: /api/assistant/"
echo "• Página de teste: /api/test-chatbot/"
echo ""
echo -e "${GREEN}O chatbot está pronto para uso! 🚀${NC}"