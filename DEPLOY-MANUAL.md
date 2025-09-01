# 🚀 Deploy Manual no Servidor de Produção

Guia para fazer deploy manual no servidor quando o GitHub Actions não funcionar ou você quiser fazer um deploy imediato.

## 📋 Informações do Servidor

Baseado no CLAUDE.md e código atual:
- **Host**: Configurado no secret `PROD_HOST`
- **Porta SSH**: `2222` (configurada no secret `PROD_PORT`)
- **Usuário**: `labadm` (configurado no secret `PROD_USER`)
- **Diretório do projeto**: `/var/www/labconnect`
- **Script de deploy**: `/home/labadm/git-deploy.sh`

## 🔑 Acesso SSH

### Comando básico SSH:
```bash
ssh -p 2222 labadm@SEU_IP_DO_SERVIDOR
```

Substitua `SEU_IP_DO_SERVIDOR` pelo IP real do servidor.

## 🔄 Deploy Manual - Método 1 (Usar script existente)

### Passo 1: Conectar no servidor
```bash
ssh -p 2222 labadm@SEU_IP_DO_SERVIDOR
```

### Passo 2: Ir para o diretório home
```bash
cd /home/labadm
```

### Passo 3: Executar script de deploy
```bash
chmod +x git-deploy.sh
./git-deploy.sh
```

### Passo 4: Iniciar ngrok
```bash
cd /var/www/labconnect
chmod +x start-labconnect-ngrok.sh
./start-labconnect-ngrok.sh restart
```

## 🔧 Deploy Manual - Método 2 (Comandos individuais)

### Conectar no servidor:
```bash
ssh -p 2222 labadm@SEU_IP_DO_SERVIDOR
```

### Ir para diretório do projeto:
```bash
cd /var/www/labconnect
```

### Fazer backup (opcional mas recomendado):
```bash
sudo cp -r /var/www/labconnect /var/www/labconnect_backup_$(date +%Y%m%d_%H%M%S)
```

### Fazer pull das alterações:
```bash
git fetch origin
git pull origin main
```

### Aplicar migrações do banco (se houver):
```bash
python manage.py migrate --settings=LabConnect.settings.production
```

### Coletar arquivos estáticos:
```bash
python manage.py collectstatic --noinput --settings=LabConnect.settings.production
```

### Reiniciar serviços:
```bash
sudo systemctl restart labconnect
sudo systemctl status labconnect
```

### Iniciar/reiniciar ngrok:
```bash
./start-labconnect-ngrok.sh restart
./start-labconnect-ngrok.sh status
```

## 🌐 Configurar ngrok (se primeira vez)

### Se o ngrok não estiver configurado:
```bash
# Instalar ngrok (se não estiver instalado)
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Configurar token (substitua SEU_TOKEN pelo token real)
ngrok config add-authtoken SEU_TOKEN_NGROK

# Iniciar tunnel
cd /var/www/labconnect
./start-labconnect-ngrok.sh start
```

## ✅ Verificar se Deploy funcionou

### 1. Verificar serviço Django:
```bash
sudo systemctl status labconnect
```

### 2. Verificar processo Gunicorn:
```bash
ps aux | grep gunicorn
```

### 3. Verificar ngrok:
```bash
./start-labconnect-ngrok.sh status
curl -I https://labconnect.ngrok.app
```

### 4. Verificar logs:
```bash
# Logs do Django
tail -f /var/www/labconnect/logs/labconnect.log

# Logs do ngrok
./start-labconnect-ngrok.sh logs
```

## 🆘 Troubleshooting

### Se o pull falhar:
```bash
# Verificar status do git
git status

# Resetar alterações locais se necessário
git reset --hard HEAD
git pull origin main
```

### Se o serviço não reiniciar:
```bash
# Ver logs do systemd
sudo journalctl -u labconnect -f

# Reiniciar forçado
sudo systemctl stop labconnect
sudo systemctl start labconnect
```

### Se ngrok não iniciar:
```bash
# Verificar se há processos ngrok rodando
ps aux | grep ngrok
pkill -f ngrok

# Tentar iniciar novamente
./start-labconnect-ngrok.sh start
```

## 📝 Deploy Completo - Comando Único

### Script rápido para deploy completo:
```bash
ssh -p 2222 labadm@SEU_IP_DO_SERVIDOR << 'EOF'
cd /var/www/labconnect
git pull origin main
python manage.py migrate --settings=LabConnect.settings.production
python manage.py collectstatic --noinput --settings=LabConnect.settings.production
sudo systemctl restart labconnect
./start-labconnect-ngrok.sh restart
echo "Deploy manual concluído!"
./start-labconnect-ngrok.sh status
sudo systemctl status labconnect
EOF
```

## 🔄 Para usar o script git-deploy.sh:

O servidor já tem um script de deploy em `/home/labadm/git-deploy.sh`. Para usar:

```bash
ssh -p 2222 labadm@SEU_IP_DO_SERVIDOR
cd /home/labadm
./git-deploy.sh
```

Este script automaticamente:
- ✅ Faz o pull do git
- ✅ Aplica migrações
- ✅ Coleta arquivos estáticos  
- ✅ Reinicia o serviço
- ✅ Faz backup

## 📱 Verificação Final

Após o deploy, verifique:
1. **Django**: `https://labconnect.ngrok.app` carrega?
2. **Admin**: `https://labconnect.ngrok.app/admin/` funciona?
3. **API**: `https://labconnect.ngrok.app/api/deploy/status/` responde?

## 🎯 Resultado Esperado

Após deploy manual bem-sucedido:
- ✅ Código atualizado no servidor
- ✅ Banco de dados migrado
- ✅ Arquivos estáticos coletados
- ✅ Serviço Django rodando
- ✅ ngrok ativo com domínio fixo
- ✅ Sistema acessível via https://labconnect.ngrok.app