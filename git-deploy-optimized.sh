#!/bin/bash
# git-deploy-optimized.sh - Faster deploy script with performance optimizations

PROJECT_DIR="/var/www/labconnect"
LOG_FILE="/var/log/labconnect-deploy.log"

log_deploy() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo "$1"
}

# Track timing
start_time=$(date +%s)

log_deploy "🚀 INICIANDO AUTO-DEPLOY OTIMIZADO"
log_deploy "======================================="

# 1. Pre-flight checks
log_deploy "🔍 Verificando estado atual..."
cd "$PROJECT_DIR"

# Check if we actually need to update
CURRENT_COMMIT=$(git rev-parse HEAD)
git fetch origin main
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$CURRENT_COMMIT" = "$REMOTE_COMMIT" ]; then
    log_deploy "✅ Já está atualizado. Deploy desnecessário."
    exit 0
fi

# 2. Minimize downtime - only stop service right before restart
log_deploy "📥 Fazendo pull do Git preservando mudanças locais..."

# Stash mudanças locais temporariamente (se houver)
STASH_CREATED=false
if ! git diff-index --quiet HEAD --; then
    log_deploy "💾 Salvando mudanças locais temporariamente..."
    git stash push -m "Auto-stash before deploy $(date)"
    STASH_CREATED=true
fi

# Fazer pull da branch main
git pull origin main

if [ $? -ne 0 ]; then
    log_deploy "❌ ERRO: Falha no git pull"
    if [ "$STASH_CREATED" = true ]; then
        git stash pop
        log_deploy "🔄 Mudanças locais restauradas"
    fi
    exit 1
fi

# Restaurar mudanças locais após o pull bem-sucedido
if [ "$STASH_CREATED" = true ]; then
    log_deploy "🔄 Restaurando mudanças locais..."
    git stash pop
    if [ $? -ne 0 ]; then
        log_deploy "⚠️ AVISO: Possível conflito ao restaurar mudanças locais"
    fi
fi

# 3. Ativar ambiente virtual
source venv/bin/activate

# 4. OTIMIZAÇÃO: Só instalar dependências se requirements.txt mudou
log_deploy "📦 Verificando dependências..."
if git diff HEAD~1 HEAD --name-only | grep -q "requirements"; then
    log_deploy "📦 Requirements mudou - atualizando dependências..."
    pip install -r requirements.txt --upgrade
    
    # Verificar se spacy model existe
    if ! python -c "import spacy; spacy.load('pt_core_news_sm')" 2>/dev/null; then
        log_deploy "📥 Instalando modelo spaCy..."
        python -m spacy download pt_core_news_sm
    fi
else
    log_deploy "✅ Requirements inalterado - pulando instalação"
fi

# 5. OTIMIZAÇÃO: Só executar migrações se models.py mudou
log_deploy "🗃️ Verificando migrações..."
if git diff HEAD~1 HEAD --name-only | grep -E "(models\.py|migrations/)" | head -1; then
    log_deploy "🗃️ Models mudaram - executando migrações..."
    python manage.py migrate --settings=LabConnect.settings.production
else
    log_deploy "✅ Models inalterados - pulando migrações"
fi

# 6. OTIMIZAÇÃO: Coletar estáticos sem --clear (mais rápido)
log_deploy "📁 Verificando arquivos estáticos..."
if git diff HEAD~1 HEAD --name-only | grep -E "(static/|templates/|\.css|\.js)" | head -1; then
    log_deploy "📁 Arquivos estáticos mudaram - coletando..."
    python manage.py collectstatic --noinput --settings=LabConnect.settings.production
else
    log_deploy "✅ Estáticos inalterados - pulando coleta"
fi

# 7. Django check (rápido)
log_deploy "✅ Verificando Django..."
python manage.py check --settings=LabConnect.settings.production

if [ $? -ne 0 ]; then
    log_deploy "❌ ERRO: Django check falhou"
    exit 1
fi

# 8. OTIMIZAÇÃO: Minimizar downtime - parar/iniciar serviço rapidamente
log_deploy "🔄 Reiniciando serviços (downtime mínimo)..."
sudo systemctl reload labconnect || sudo systemctl restart labconnect

# 9. Ajustar permissões apenas se necessário
if [ "$STASH_CREATED" = true ] || git diff HEAD~1 HEAD --name-only | grep -q "\.py$"; then
    log_deploy "🔐 Ajustando permissões..."
    sudo chown -R $USER:$USER "$PROJECT_DIR"
    sudo chmod -R 755 "$PROJECT_DIR"
fi

# 10. Criar diretórios necessários (rápido)
mkdir -p logs
touch logs/ai_analysis.log

# 11. Reload nginx (mais rápido que restart)
sudo systemctl reload nginx

# 12. Quick health check (sem delay desnecessário)
log_deploy "🏥 Verificando saúde da aplicação..."
sleep 3

if curl -s -I http://localhost | grep -q "HTTP"; then
    log_deploy "✅ Django funcionando!"
else
    log_deploy "❌ ERRO: Django não está respondendo"
fi

# Calculate deploy time
end_time=$(date +%s)
deploy_time=$((end_time - start_time))

log_deploy "🎉 AUTO-DEPLOY CONCLUÍDO EM ${deploy_time}s!"
log_deploy "======================================="

# Notificar via webhook (opcional)
curl -s -X POST "http://localhost:4040/api/deploy-notification" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"success\",\"timestamp\":\"$(date)\",\"project\":\"labconnect\",\"duration\":\"${deploy_time}s\"}" \
    2>/dev/null || true