# 🌐 ngrok com Domínio Fixo - LabConnect

Este documento explica como usar o ngrok com domínio fixo **labconnect.ngrok.app** no sistema LabConnect.

## 📋 Configuração

### Domínio Fixo
- **URL**: `https://labconnect.ngrok.app`
- **Porta Local**: `8000` (Django/Gunicorn)
- **Comando ngrok**: `ngrok http --url=labconnect.ngrok.app 8000`

### Arquivos do Sistema
- `start-labconnect-ngrok.sh` - Script principal de gerenciamento
- `ngrok.yml` - Arquivo de configuração (opcional)
- `current-ngrok-url.txt` - URL atual salva
- `ngrok.log` - Logs do ngrok
- `ngrok.pid` - PID do processo ngrok

## 🚀 Como Usar

### Comandos Básicos
```bash
# Iniciar tunnel
./start-labconnect-ngrok.sh start

# Verificar status  
./start-labconnect-ngrok.sh status

# Parar tunnel
./start-labconnect-ngrok.sh stop

# Reiniciar tunnel
./start-labconnect-ngrok.sh restart

# Ver logs em tempo real
./start-labconnect-ngrok.sh logs

# Mostrar ajuda
./start-labconnect-ngrok.sh help
```

### Primeiro Uso
1. **Configurar ngrok com seu token**:
   ```bash
   ngrok config add-authtoken SEU_TOKEN_AQUI
   ```

2. **Dar permissão ao script**:
   ```bash
   chmod +x start-labconnect-ngrok.sh
   ```

3. **Iniciar tunnel**:
   ```bash
   ./start-labconnect-ngrok.sh start
   ```

## 🔧 Integração com Deploy

### GitHub Actions
O arquivo `.github/workflows/deploy.yml` foi configurado para:

1. **Deploy via Webhook**: Usa o domínio fixo `https://labconnect.ngrok.app/api/deploy/`
2. **Fallback SSH**: Se o webhook falhar, usa SSH e reinicia o ngrok
3. **Verificação Automática**: Sempre verifica se o ngrok está rodando após deploy

### Fluxo de Deploy
```
GitHub Push → GitHub Actions → Webhook (labconnect.ngrok.app) → Servidor
                     ↓ (se falhar)
                SSH → Servidor → Reinicia ngrok
```

## 📊 Monitoramento

### Status do Tunnel
```bash
# Verificar se está rodando
./start-labconnect-ngrok.sh status

# Ver logs
./start-labconnect-ngrok.sh logs

# Testar conectividade
curl -I https://labconnect.ngrok.app
```

### Arquivos de Status
- `current-ngrok-url.txt` - Sempre contém `https://labconnect.ngrok.app`
- `ngrok.pid` - PID do processo ngrok
- `ngrok.log` - Logs detalhados do ngrok

## ⚙️ Configuração Avançada

### Arquivo ngrok.yml
O sistema pode usar um arquivo de configuração opcional:

```yaml
version: "2"
authtoken_from_env: true
log_level: info
log: ngrok.log

tunnels:
  labconnect:
    addr: 8000
    proto: http
    hostname: labconnect.ngrok.app
    
region: us
web_addr: false
```

### Variáveis de Ambiente
```bash
export NGROK_AUTHTOKEN="seu_token_aqui"
```

## 🔍 Troubleshooting

### Problemas Comuns

1. **"ngrok não está instalado"**
   ```bash
   # Instalar ngrok
   curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
   echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
   sudo apt update && sudo apt install ngrok
   ```

2. **"Tunnel session failed"**
   ```bash
   # Verificar token de autenticação
   ngrok config add-authtoken SEU_TOKEN
   
   # Reiniciar tunnel
   ./start-labconnect-ngrok.sh restart
   ```

3. **"Domínio não autorizado"**
   - Verificar se o domínio `labconnect.ngrok.app` está configurado na conta ngrok
   - Verificar se o plano ngrok suporta domínios customizados

### Logs e Depuração
```bash
# Ver logs completos
cat ngrok.log

# Monitorar em tempo real
tail -f ngrok.log

# Verificar processo
ps aux | grep ngrok
```

## 💡 Vantagens do Domínio Fixo

### ✅ Benefícios
- **URL Consistente**: Sempre `https://labconnect.ngrok.app`
- **Deploy Automático**: GitHub Actions funciona sem configuração manual
- **Webhooks Estáveis**: URLs não mudam entre reinicializações
- **SSL Automático**: Certificado SSL gerenciado pelo ngrok
- **Performance**: Melhor cache e DNS

### 📈 Comparação

| Recurso | ngrok Free | ngrok Fixo |
|---------|------------|------------|
| URL | Aleatória | labconnect.ngrok.app |
| Persistência | ❌ | ✅ |
| SSL | ✅ | ✅ |
| Deploy Automático | ❌ | ✅ |
| Webhooks | Instáveis | Estáveis |

## 🎯 Resultado Final

Após configurar o domínio fixo:
- ✅ URL sempre disponível em `https://labconnect.ngrok.app`
- ✅ Deploy automático via GitHub Actions funcionando
- ✅ Webhooks estáveis para notificações
- ✅ Monitoramento e logs automatizados
- ✅ Fallback automático via SSH se necessário

---

**🔗 Links Úteis**:
- [ngrok Documentation](https://ngrok.com/docs)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Django Deployment](https://docs.djangoproject.com/en/stable/howto/deployment/)