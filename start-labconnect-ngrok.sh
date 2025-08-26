#!/bin/bash
# Script para gerenciar o ngrok tunnel com domínio fixo do LabConnect
# Domínio fixo: labconnect.ngrok.app

# Configurações
NGROK_DOMAIN="labconnect.ngrok.app"
SERVICE_PORT="8000"
NGROK_PID_FILE="./ngrok.pid"
NGROK_LOG_FILE="./ngrok.log"
CURRENT_URL_FILE="./current-ngrok-url.txt"
NGROK_CONFIG_FILE="./ngrok.yml"

# Função para logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Função para verificar se o ngrok está instalado
check_ngrok() {
    if ! command -v ngrok &> /dev/null; then
        log "❌ ngrok não está instalado. Instale em: https://ngrok.com/download"
        exit 1
    fi
    
    local version=$(ngrok version | head -n1 || echo "unknown")
    log "✅ ngrok disponível: $version"
}

# Função para iniciar o ngrok com domínio fixo
start_ngrok() {
    log "🚀 Iniciando ngrok com domínio fixo..."
    check_ngrok
    
    # Verificar se já está rodando
    if [[ -f "$NGROK_PID_FILE" ]]; then
        local pid=$(cat "$NGROK_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "⚠️ ngrok já está rodando (PID: $pid)"
            return 0
        else
            log "🧹 Removendo arquivo PID obsoleto"
            rm -f "$NGROK_PID_FILE"
        fi
    fi
    
    # Iniciar ngrok em background com domínio fixo
    log "🌐 Iniciando tunnel: https://$NGROK_DOMAIN → localhost:$SERVICE_PORT"
    
    # Verificar se existe arquivo de configuração
    if [[ -f "$NGROK_CONFIG_FILE" ]]; then
        log "📋 Usando arquivo de configuração: $NGROK_CONFIG_FILE"
        nohup ngrok start --config="$NGROK_CONFIG_FILE" labconnect > /dev/null 2>&1 &
    else
        log "📋 Usando comando direto (sem arquivo de configuração)"
        nohup ngrok http --url="$NGROK_DOMAIN" "$SERVICE_PORT" \
            --log="$NGROK_LOG_FILE" \
            --log-level=info \
            > /dev/null 2>&1 &
    fi
    
    local ngrok_pid=$!
    echo "$ngrok_pid" > "$NGROK_PID_FILE"
    
    # Aguardar um pouco para o ngrok inicializar
    sleep 5
    
    # Verificar se o processo está rodando
    if kill -0 "$ngrok_pid" 2>/dev/null; then
        # Salvar URL fixa no arquivo
        echo "https://$NGROK_DOMAIN" > "$CURRENT_URL_FILE"
        
        log "✅ ngrok iniciado com sucesso!"
        log "🌐 URL fixa: https://$NGROK_DOMAIN"
        log "📂 Logs disponíveis em: $NGROK_LOG_FILE"
        log "🆔 PID: $ngrok_pid"
        
        return 0
    else
        log "❌ Erro ao iniciar ngrok"
        rm -f "$NGROK_PID_FILE"
        return 1
    fi
}

# Função para parar o ngrok
stop_ngrok() {
    log "🛑 Parando ngrok..."
    
    if [[ -f "$NGROK_PID_FILE" ]]; then
        local pid=$(cat "$NGROK_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            sleep 3
            
            # Force kill se necessário
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid"
            fi
            
            log "✅ ngrok parado (PID: $pid)"
        else
            log "⚠️ ngrok não estava rodando"
        fi
        
        rm -f "$NGROK_PID_FILE"
    else
        log "⚠️ Arquivo PID não encontrado"
    fi
    
    # Limpar outros arquivos
    rm -f "$CURRENT_URL_FILE"
    
    # Verificar se ainda há processos ngrok rodando
    pkill -f "ngrok" || true
}

# Função para verificar status
status_ngrok() {
    log "📊 Verificando status do ngrok..."
    
    if [[ -f "$NGROK_PID_FILE" ]]; then
        local pid=$(cat "$NGROK_PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "✅ ngrok está rodando (PID: $pid)"
            
            if [[ -f "$CURRENT_URL_FILE" ]]; then
                local current_url=$(cat "$CURRENT_URL_FILE")
                log "🌐 URL atual: $current_url"
                
                # Testar conectividade
                if curl -I "$current_url" 2>/dev/null | grep -q "HTTP"; then
                    log "✅ Tunnel acessível e funcionando"
                else
                    log "⚠️ Tunnel pode estar com problemas de conectividade"
                fi
            fi
            
            return 0
        else
            log "❌ ngrok não está rodando (arquivo PID obsoleto)"
            rm -f "$NGROK_PID_FILE"
            return 1
        fi
    else
        log "❌ ngrok não está rodando"
        return 1
    fi
}

# Função para mostrar logs
logs_ngrok() {
    log "📄 Mostrando logs do ngrok..."
    
    if [[ -f "$NGROK_LOG_FILE" ]]; then
        tail -f "$NGROK_LOG_FILE"
    else
        log "⚠️ Arquivo de log não encontrado: $NGROK_LOG_FILE"
    fi
}

# Função para reiniciar
restart_ngrok() {
    log "🔄 Reiniciando ngrok..."
    stop_ngrok
    sleep 2
    start_ngrok
}

# Função para mostrar ajuda
show_help() {
    echo "=========================================="
    echo "  ngrok LabConnect - Domínio Fixo"
    echo "=========================================="
    echo "  Domínio: https://$NGROK_DOMAIN"
    echo "  Porta local: $SERVICE_PORT"
    echo ""
    echo "Comandos disponíveis:"
    echo "  start    - Iniciar ngrok tunnel"
    echo "  stop     - Parar ngrok tunnel"  
    echo "  restart  - Reiniciar ngrok tunnel"
    echo "  status   - Verificar status"
    echo "  logs     - Mostrar logs em tempo real"
    echo "  help     - Mostrar esta ajuda"
    echo ""
    echo "Uso: ./start-labconnect-ngrok.sh [comando]"
    echo "=========================================="
}

# Função principal
main() {
    case "${1:-help}" in
        "start")
            start_ngrok
            ;;
        "stop")
            stop_ngrok
            ;;
        "restart")
            restart_ngrok
            ;;
        "status")
            status_ngrok
            ;;
        "logs")
            logs_ngrok
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Executar função principal
main "$@"