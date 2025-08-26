# 🔐 Configuração dos GitHub Secrets

Para que o deploy automático funcione com o domínio fixo ngrok, você precisa configurar os seguintes secrets no GitHub:

## 📋 Secrets Necessários

### 1. DEPLOY_TOKEN
- **Valor**: `lab-deploy-2024-secure-token-xyz123`
- **Descrição**: Token para autenticação do webhook de deploy
- **Usado em**: GitHub Actions → ngrok webhook

### 2. PROD_HOST (Para SSH Fallback)
- **Valor**: IP do seu servidor de produção
- **Exemplo**: `192.168.1.100` ou `seu-servidor.com`
- **Descrição**: Host do servidor para SSH fallback

### 3. PROD_PORT (Para SSH Fallback)  
- **Valor**: `2222` (ou a porta SSH do seu servidor)
- **Descrição**: Porta SSH do servidor

### 4. PROD_USER (Para SSH Fallback)
- **Valor**: `labadm` (ou o usuário SSH do seu servidor)
- **Descrição**: Usuário SSH para acesso ao servidor

### 5. PROD_SSH_KEY (Para SSH Fallback)
- **Valor**: Chave SSH privada completa
- **Formato**:
```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAFwAAAAdzc2gtcn
[... resto da chave ...]
-----END OPENSSH PRIVATE KEY-----
```

## 🛠️ Como Configurar no GitHub

### Passo 1: Acessar Configurações
1. Acesse seu repositório no GitHub
2. Clique em **Settings** (Configurações)
3. No menu lateral, clique em **Secrets and variables** → **Actions**

### Passo 2: Adicionar Secrets
Para cada secret:
1. Clique em **New repository secret**
2. Digite o nome do secret (ex: `DEPLOY_TOKEN`)
3. Cole o valor correspondente
4. Clique em **Add secret**

### Passo 3: Verificar Configuração
Após adicionar todos os secrets, você verá:
- ✅ DEPLOY_TOKEN
- ✅ PROD_HOST
- ✅ PROD_PORT  
- ✅ PROD_USER
- ✅ PROD_SSH_KEY

## 🔍 Verificação dos Secrets

O GitHub Actions inclui verificação automática:
```yaml
- name: Debug secrets availability
  run: |
    echo "🔐 Verificando secrets:"
    echo "DEPLOY_TOKEN existe: ${{ secrets.DEPLOY_TOKEN != '' }}"
    echo "PROD_HOST existe: ${{ secrets.PROD_HOST != '' }}"
    echo "PROD_PORT existe: ${{ secrets.PROD_PORT != '' }}"
    echo "PROD_USER existe: ${{ secrets.PROD_USER != '' }}"
    echo "PROD_SSH_KEY existe: ${{ secrets.PROD_SSH_KEY != '' }}"
```

## 🚀 Fluxo de Deploy

### Cenário 1: Webhook Funciona
```
GitHub Push → GitHub Actions → https://labconnect.ngrok.app/api/deploy/ → Servidor
```

### Cenário 2: Fallback SSH  
```
GitHub Push → GitHub Actions → Webhook Falha → SSH Deploy → Reinicia ngrok
```

## ⚠️ Importante

1. **Token de Deploy**: O valor `lab-deploy-2024-secure-token-xyz123` deve corresponder exatamente ao definido em `api/views_deploy.py:15`

2. **Domínio ngrok**: Certifique-se que `labconnect.ngrok.app` está configurado na sua conta ngrok

3. **SSH Key**: A chave SSH deve ter permissões corretas no servidor:
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

4. **Firewall**: Porta SSH deve estar liberada no servidor

## 🧪 Teste Manual

Você pode testar o webhook manualmente:
```bash
curl -X POST "https://labconnect.ngrok.app/api/deploy/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer lab-deploy-2024-secure-token-xyz123" \
  -d '{"commit": "test", "branch": "refs/heads/main"}'
```

## 📊 Status dos Secrets

Após configurar, o GitHub Actions mostrará na execução:
```
🔐 Verificando secrets:
DEPLOY_TOKEN existe: true
PROD_HOST existe: true  
PROD_PORT existe: true
PROD_USER existe: true
PROD_SSH_KEY existe: true
```

Se algum mostrar `false`, o secret não foi configurado corretamente.