# 🤖 LabConnect - Verificação Rápida do Chatbot

## 🔍 **Comandos para Verificar no Servidor**

### **1. Verificar se Ollama está instalado**
```bash
ollama --version
# Esperado: ollama version is 0.x.x
```

### **2. Verificar se serviço está rodando**
```bash
pgrep -f "ollama serve"
# Esperado: número do processo

# Ou verificar porta
netstat -tlnp | grep 11434
# Esperado: linha mostrando porta 11434 LISTEN
```

### **3. Testar conectividade Ollama**
```bash
curl http://localhost:11434/api/version
# Esperado: {"version":"0.x.x"}

curl http://localhost:11434/api/tags
# Esperado: lista de modelos instalados
```

### **4. Verificar modelos instalados**
```bash
ollama list
# Esperado: lista com llama3 ou outros modelos
```

### **5. Testar modelo específico**
```bash
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "prompt": "Diga apenas: LabConnect funcionando",
    "stream": false
  }'
```

### **6. Verificar variáveis de ambiente Django**
```bash
cd /var/www/labconnect
grep -E "OLLAMA|ollama" .env
# Esperado: 
# OLLAMA_API_URL=http://localhost:11434/api/chat
# OLLAMA_MODEL=llama3
```

### **7. Testar endpoint Django**
```bash
# Testar se endpoint responde
curl -X GET https://seu-dominio/api/assistant/
# Ou localhost se testando local:
curl -X GET http://localhost:8000/api/assistant/
```

---

## 🛠️ **Comandos de Correção**

### **Se Ollama não estiver instalado:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### **Se serviço não estiver rodando:**
```bash
# Tentar como serviço
sudo systemctl start ollama
sudo systemctl enable ollama

# Ou iniciar manualmente
nohup ollama serve > /tmp/ollama.log 2>&1 &
```

### **Se modelo não estiver instalado:**
```bash
ollama pull llama3
# Ou modelo menor para teste:
ollama pull phi
```

### **Se variáveis não estiverem configuradas:**
```bash
echo "OLLAMA_API_URL=http://localhost:11434/api/chat" >> .env
echo "OLLAMA_MODEL=llama3" >> .env
```

---

## 🔧 **Script Automático**

### **Executar verificação completa:**
```bash
cd /var/www/labconnect
./setup-chatbot-ia.sh
```

### **Verificação manual rápida:**
```bash
# 1. Ollama OK?
ollama --version && echo "✅ Ollama instalado"

# 2. Serviço OK?
pgrep -f "ollama serve" && echo "✅ Serviço rodando"

# 3. API OK?
curl -s http://localhost:11434/api/version && echo "✅ API respondendo"

# 4. Modelo OK?
ollama list | grep -q llama3 && echo "✅ Modelo llama3 instalado"

# 5. Django OK?
python manage.py shell -c "
from django.conf import settings
print('✅ OLLAMA_API_URL:', getattr(settings, 'OLLAMA_API_URL', 'NÃO CONFIGURADO'))
print('✅ OLLAMA_MODEL:', getattr(settings, 'OLLAMA_MODEL', 'NÃO CONFIGURADO'))
"
```

---

## 📊 **Status Esperado (Tudo OK)**

```bash
✅ Ollama: ollama version is 0.1.x
✅ Serviço: processo rodando na porta 11434
✅ API: {"version":"0.1.x"}
✅ Modelo: llama3 disponível
✅ Django: variáveis configuradas
✅ Endpoint: /api/assistant/ respondendo
```

---

## 🚨 **Troubleshooting Comum**

| Problema | Comando de Verificação | Solução |
|----------|----------------------|---------|
| Ollama não instalado | `ollama --version` | `curl -fsSL https://ollama.ai/install.sh \| sh` |
| Serviço parado | `pgrep -f "ollama serve"` | `ollama serve &` |
| Porta ocupada | `netstat -tlnp \| grep 11434` | Matar processo ou mudar porta |
| Modelo não encontrado | `ollama list` | `ollama pull llama3` |
| Django não conecta | Logs do Django | Verificar URL e firewall |

---

## 📝 **Logs Importantes**

```bash
# Logs do Ollama
tail -f /tmp/ollama.log

# Logs do Django
tail -f /var/www/labconnect/logs/labconnect.log

# Logs do sistema
journalctl -u ollama -f
```

---

## 🎯 **Teste Final**

Após configurar tudo, teste com:

```bash
curl -X POST http://localhost:8000/api/assistant/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: seu-token" \
  -d '{"message": "Olá, você está funcionando?"}'
```

Se retornar resposta em streaming, **está funcionando!** 🎉