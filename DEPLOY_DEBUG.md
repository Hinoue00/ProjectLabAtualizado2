# Debug de Deploy Automático

## Checklist para o Deploy Automático Funcionar

### 1. ✅ Secrets do GitHub Actions
Verifique se estes secrets estão configurados no GitHub em `https://github.com/Hinoue00/ProjectLabAtualizado2/settings/secrets/actions`:

- `PROD_HOST` - IP ou hostname do servidor de produção
- `PROD_PORT` - Porta SSH (provavelmente 2222)
- `PROD_USER` - Usuário SSH (provavelmente labadm)
- `PROD_SSH_KEY` - Chave SSH privada para conexão

### 2. ✅ Verificações no Servidor
SSH no servidor e verificar:

```bash
# Conectar no servidor
ssh -p 2222 labadm@SEU_SERVIDOR

# Verificar se os scripts existem
ls -la /home/labadm/git-deploy.sh
ls -la /home/labadm/start-labconnect-ngrok.sh

# Verificar permissões
chmod +x /home/labadm/git-deploy.sh
chmod +x /home/labadm/start-labconnect-ngrok.sh

# Testar o script manualmente
cd /home/labadm
./git-deploy.sh
```

### 3. ✅ Verificar Status do Workflow
1. Acesse: `https://github.com/Hinoue00/ProjectLabAtualizado2/actions`
2. Veja se o workflow aparece na lista
3. Clique no workflow mais recente para ver os logs
4. Verifique se a etapa de "Deploy" está sendo executada

### 4. ✅ Trigger Conditions
O deploy só funciona quando:
- Push é feito na branch `main`
- Os testes passam
- É um evento de `push` (não `pull_request`)

### 5. ✅ Teste Manual
Para testar se o deploy funciona:

```bash
# Fazer uma mudança simples
echo "# Deploy Test" >> README.md
git add README.md
git commit -m "test: Deploy automation test"
git push origin main
```

### 6. ⚠️ Possíveis Problemas Comuns

#### Problema: Action não executa
- **Causa**: Workflow está desabilitado
- **Solução**: Vá em Actions → Enable workflow

#### Problema: SSH falha
- **Causa**: Chave SSH incorreta ou servidor inacessível
- **Solução**: Testar SSH manualmente

#### Problema: Script não encontrado
- **Causa**: Caminho incorreto no servidor
- **Solução**: Verificar se `/home/labadm/git-deploy.sh` existe

#### Problema: Permissões negadas
- **Causa**: Script não tem permissão de execução
- **Solução**: `chmod +x git-deploy.sh`

### 7. 🔧 Melhorias Adicionadas

1. **Debug detalhado**: Agora o workflow mostra informações de debug
2. **Timeouts**: Configurados timeouts para evitar travamentos
3. **Verificações robustas**: Verificar se arquivos existem antes de executar
4. **Status detalhado**: Mostrar status final dos serviços

### 8. 📋 Próximos Passos

1. Commit e push desta mudança
2. Verificar se o workflow executa
3. Analisar os logs do GitHub Actions
4. Se falhar, verificar cada item do checklist