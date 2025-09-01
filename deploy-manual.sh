#!/bin/bash
# Script para deploy manual no servidor de produção
# Uso: ./deploy-manual.sh [host] [port] [user]

# Configurações padrão
DEFAULT_HOST="SEU_IP_AQUI"  # Substitua pelo IP real do servidor
DEFAULT_PORT="2222"
DEFAULT_USER="labadm"

# Usar parâmetros ou valores padrão
HOST="${1:-$DEFAULT_HOST}"
PORT="${2:-$DEFAULT_PORT}"
USER="${3:-$DEFAULT_USER}"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para logging
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Verificar se os parâmetros estão corretos
if [[ "$HOST" == "SEU_IP_AQUI" ]]; then
    error "Configure o IP do servidor no script ou passe como parâmetro:"
    echo "  ./deploy-manual.sh IP_DO_SERVIDOR [porta] [usuario]"
    echo "  Exemplo: ./deploy-manual.sh 192.168.1.100 2222 labadm"
    exit 1
fi

# Função principal de deploy
deploy_manual() {
    log "🚀 Iniciando deploy manual no servidor..."
    log "🌐 Host: $HOST:$PORT"
    log "👤 Usuário: $USER"
    
    # Comandos para executar no servidor
    DEPLOY_COMMANDS=$(cat << 'EOF'
set -e  # Exit on any error

echo "📂 Navegando para diretório do projeto..."
cd /var/www/labconnect

echo "🔍 Verificando status atual do git..."
git status

echo "📥 Fazendo pull das alterações..."
git fetch origin
git pull origin main

echo "🗄️ Aplicando migrações do banco de dados..."
python manage.py migrate --settings=LabConnect.settings.production

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --settings=LabConnect.settings.production

echo "🔄 Reiniciando serviço Django..."
sudo systemctl restart labconnect

echo "⏳ Aguardando serviço inicializar..."
sleep 5

echo "🌐 Configurando ngrok com domínio fixo..."
if [ -f "./start-labconnect-ngrok.sh" ]; then
    chmod +x ./start-labconnect-ngrok.sh
    ./start-labconnect-ngrok.sh restart
    sleep 3
    ./start-labconnect-ngrok.sh status
else
    echo "⚠️ Script do ngrok não encontrado"
fi

echo "📊 Verificando status final..."
echo "--- Status do serviço Django ---"
sudo systemctl status labconnect --no-pager -l || echo "❌ Erro ao obter status do Django"

echo "--- Processos LabConnect ---"
ps aux | grep -v grep | grep -i labconnect || echo "⚠️ Nenhum processo encontrado"

echo "--- Teste de conectividade ngrok ---"
curl -I https://labconnect.ngrok.app || echo "⚠️ ngrok pode estar offline"

echo ""
echo "🎉 Deploy manual concluído!"
echo "🌐 Acesse: https://labconnect.ngrok.app"
EOF
    )

    # Executar comandos no servidor via SSH
    log "🔐 Conectando via SSH e executando deploy..."
    
    ssh -p "$PORT" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$USER@$HOST" "$DEPLOY_COMMANDS"
    
    if [ $? -eq 0 ]; then
        success "Deploy manual executado com sucesso!"
        log "🌐 Acesse: https://labconnect.ngrok.app"
        log "🔧 Admin: https://labconnect.ngrok.app/admin/"
    else
        error "Falha no deploy manual"
        exit 1
    fi
}

# Função para testar conexão SSH
test_connection() {
    log "🔍 Testando conexão SSH..."
    
    ssh -p "$PORT" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$USER@$HOST" "echo 'Conexão SSH OK'; whoami; pwd"
    
    if [ $? -eq 0 ]; then
        success "Conexão SSH estabelecida com sucesso!"
        return 0
    else
        error "Falha na conexão SSH"
        echo "Verifique:"
        echo "  - IP do servidor: $HOST"
        echo "  - Porta SSH: $PORT"  
        echo "  - Usuário: $USER"
        echo "  - Chave SSH configurada"
        return 1
    fi
}

# Função para mostrar ajuda
show_help() {
    echo "==============================================="
    echo "  Deploy Manual - LabConnect"
    echo "==============================================="
    echo ""
    echo "Uso:"
    echo "  ./deploy-manual.sh [host] [porta] [usuario]"
    echo ""
    echo "Exemplos:"
    echo "  ./deploy-manual.sh                           # Usar configurações padrão"
    echo "  ./deploy-manual.sh 192.168.1.100           # Especificar apenas o host"
    echo "  ./deploy-manual.sh 192.168.1.100 2222      # Host e porta"
    echo "  ./deploy-manual.sh 192.168.1.100 2222 admin # Host, porta e usuário"
    echo ""
    echo "Comandos:"
    echo "  deploy    - Executar deploy completo (padrão)"
    echo "  test      - Testar conexão SSH"
    echo "  help      - Mostrar esta ajuda"
    echo ""
    echo "Configuração atual:"
    echo "  Host: $HOST"
    echo "  Porta: $PORT"
    echo "  Usuário: $USER"
    echo "==============================================="
}

# Processar argumentos
case "${4:-deploy}" in
    "test")
        test_connection
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    "deploy"|"")
        if test_connection; then
            deploy_manual
        fi
        ;;
    *)
        warning "Comando desconhecido: $4"
        show_help
        exit 1
        ;;
esac