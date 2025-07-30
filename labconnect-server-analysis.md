# Análise Completa do Servidor LabConnect em Produção

## 📋 Resumo Executivo

O **LabConnect** é um sistema de gerenciamento de laboratórios desenvolvido em Django para a rede universitária Unopar-Anhanguera (Cogna). Este documento apresenta uma análise completa da infraestrutura em produção, arquitetura de dados e configurações de segurança.

---

## 🏗️ Arquitetura do Sistema

### Informações do Servidor
- **Sistema Operacional**: Ubuntu 24.04.2 LTS
- **Kernel**: 6.8.0-63-generic
- **Arquitetura**: x86_64
- **Processador**: Intel Celeron J1800 @ 2.41GHz (2 CPUs)
- **Memória RAM**: 7.6GB total, 6.6GB disponível
- **Armazenamento**: 98GB total, 63GB disponível

### Estrutura de Diretórios Principal

```
/var/www/labconnect/          # Aplicação principal
├── LabConnect/               # Configurações Django
├── accounts/                 # Sistema de autenticação
├── laboratories/             # Gerenciamento de laboratórios
├── inventory/                # Sistema de inventário
├── scheduling/               # Agendamento de laboratórios
├── dashboard/                # Dashboards personalizados
├── reports/                  # Sistema de relatórios
├── api/                      # API REST e assistente IA
├── whatsapp/                 # Integração WhatsApp
├── staticfiles/              # Arquivos estáticos
├── media/                    # Uploads de arquivos
├── logs/                     # Logs do sistema
└── venv/                     # Ambiente virtual Python

/home/labadm/                 # Scripts de deploy e monitoramento
├── git-deploy.sh             # Deploy automático via Git
├── start-labconnect-ngrok.sh # Inicialização com Ngrok
├── ngrok-auto-updater.sh     # Monitor automático do Ngrok
└── scripts/deploy-labconnect.sh
```

---

## 🛠️ Stack Tecnológico

### Framework e Linguagem
- **Python 3.x** com **Django 5.2**
- **PostgreSQL** como banco de dados principal
- **Redis** para cache e sessões
- **Nginx** como servidor web/proxy reverso
- **Gunicorn** como servidor WSGI

### Principais Dependências
```python
# Framework principal
Django==5.2
djangorestframework==3.16.0
django-crispy-forms==2.3
crispy-bootstrap5==2025.4

# Banco de dados
psycopg2-binary==2.9.10
asyncpg==0.30.0

# IA e Processamento de texto
docling==2.28.4
transformers==4.51.1
torch==2.6.0
easyocr==1.7.2
spacy (modelo: pt_core_news_sm)

# APIs e integrações
openai==1.71.0
requests==2.32.3
aiohttp==3.11.16

# Processamento de documentos
pandas==2.2.3
openpyxl==3.1.5
python-docx==1.1.2
pypdf2==4.30.1

# Interface e visualização
matplotlib==3.10.1
beautifulsoup4==4.13.3
```

---

## 🗄️ Arquitetura de Banco de Dados

### Esquema Principal

#### 1. **Módulo de Usuários (accounts)**
```sql
-- Modelo personalizado de usuário
User:
- email (EmailField, único) - Campo de login
- user_type: 'professor' | 'technician'
- phone_number (CharField)
- is_approved (BooleanField) - Requer aprovação
- lab_department (CharField) - Departamento para técnicos
- registration_date (DateTimeField)

-- Validação de domínios corporativos
Domínios permitidos: @cogna.com.br, @kroton.com.br
```

#### 2. **Módulo de Laboratórios (laboratories)**
```sql
Department:
- code (CharField, único) - Código do departamento
- name (CharField) - Nome do departamento
- description (TextField)
- color (CharField) - Cor em hexadecimal
- is_active (BooleanField)

Laboratory:
- name (CharField) - Nome do laboratório
- location (CharField) - Localização física
- capacity (PositiveIntegerField) - Capacidade de pessoas
- departments (ManyToManyField) - Múltiplos departamentos
- responsible_technicians (ManyToManyField) - Múltiplos técnicos
- equipment (TextField) - Equipamentos disponíveis
- is_active (BooleanField)
```

#### 3. **Módulo de Inventário (inventory)**
```sql
MaterialCategory:
- name (CharField)
- material_type: 'consumable' | 'permanent' | 'perishable'

Material:
- name (CharField)
- category (ForeignKey)
- description (TextField)
- quantity (PositiveIntegerField)
- minimum_stock (PositiveIntegerField) - Alerta de estoque baixo
- laboratory (ForeignKey)
- analyzed_data (JSONField) - Dados de análise NLP
- suggested_category (CharField) - Categoria sugerida por IA
- created_at/updated_at (DateTimeField)
```

#### 4. **Módulo de Agendamento (scheduling)**
```sql
ScheduleRequest:
- professor (ForeignKey) - Professor solicitante
- laboratory (ForeignKey) - Laboratório solicitado
- subject (CharField) - Disciplina/Assunto
- description (TextField) - Descrição da atividade
- scheduled_date (DateField) - Data do agendamento
- start_time/end_time (TimeField) - Horários
- number_of_students (IntegerField) - Número de alunos
- materials (TextField) - Materiais necessários
- status: 'pending' | 'approved' | 'rejected'
- reviewed_by (ForeignKey) - Técnico que avaliou
- guide_file (FileField) - Roteiro de aula

DraftScheduleRequest:
- Modelo para rascunhos antes da confirmação
- shift: 'morning' | 'evening' - Turnos predefinidos

FileAttachment:
- schedule_request (ForeignKey)
- file (FileField) - Anexos do agendamento
```

---

## 🔒 Configurações de Segurança

### Segurança em Produção (`production.py`)
```python
# SSL/HTTPS obrigatório
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Proteções de cabeçalho
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Proxy reverso
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# Domínios confiáveis para CSRF
CSRF_TRUSTED_ORIGINS = ['https://ee0b99dba01c.ngrok-free.app']
```

### Validação de Email Corporativo
```python
# Apenas emails corporativos são aceitos
allowed_domains = ['cogna.com.br', 'kroton.com.br']
```

### Sistema de Aprovação
- Novos usuários requerem aprovação de técnicos
- Apenas usuários aprovados podem acessar o sistema
- Superusuários são aprovados automaticamente

---

## 🤖 Integrações e APIs

### 1. **API do Assistente IA**
- **Endpoint**: `/api/assistant/`
- **Modelo**: Llama local via Ollama
- **Funcionalidades**:
  - Chat interativo com contexto do sistema
  - Respostas em tempo real (streaming)
  - Contexto baseado no tipo de usuário
  - Integração com dados do banco

### 2. **Integração WhatsApp**
- Configurável via variáveis de ambiente
- API para notificações e comunicação

### 3. **Sistema de Análise de Documentos**
- **Docling** para análise de texto
- **spaCy** para processamento de linguagem natural
- Categorização automática de materiais de inventário
- OCR para documentos escaneados

---

## 📊 Funcionalidades Principais

### Para Professores
- **Agendamento de Laboratórios**
  - Disponível apenas às quintas e sextas-feiras
  - Agendamentos para a semana seguinte
  - Upload de roteiros de aula
  - Solicitação de materiais específicos

- **Dashboard Personalizado**
  - Calendário de agendamentos
  - Status das solicitações
  - Histórico de reservas

### Para Técnicos/Laboratoristas
- **Gerenciamento de Laboratórios**
  - Aprovação/rejeição de agendamentos
  - Visualização de conflitos de horário
  - Controle de múltiplos laboratórios

- **Sistema de Inventário**
  - Catalogação de materiais por categoria
  - Alertas de estoque baixo
  - Importação em lote via Excel/CSV
  - Categorização automática por IA

- **Relatórios e Analytics**
  - Relatórios de uso dos laboratórios
  - Estatísticas de inventário
  - Gráficos e exportação em PDF/Excel

### Responsáveis por Departamento
- **Jason Inoue**: Laboratórios de Engenharias e Exatas
- **João Santangelo**: Laboratórios de Saúde
- **Cristhian Gusso**: Laboratórios de Informática

---

## 🚀 Deploy e Infraestrutura

### Sistema de Deploy Automatizado
```bash
# Script principal: /home/labadm/git-deploy.sh
- Backup automático antes do deploy
- Pull do Git (branch main)
- Atualização de dependências
- Migrações de banco de dados
- Coleta de arquivos estáticos
- Reinicialização de serviços
- Verificação de saúde pós-deploy
```

### Monitoramento com Ngrok
```bash
# Script: /home/labadm/start-labconnect-ngrok.sh
- Exposição externa via Ngrok
- Monitor automático de URL
- Health checks contínuos
- Logs detalhados
```

### Estrutura de Serviços
```systemd
# Serviço principal: labconnect.service
- Gunicorn WSGI server
- Bind: 127.0.0.1:8000
- Workers: 3 processos
- Status atual: Inativo (requer reinicialização)
```

---

## 📁 Estrutura de Logs

### Logs Principais
```
/var/www/labconnect/logs/
├── ai_analysis.log          # Logs de análise por IA
└── labconnect.log          # Logs gerais da aplicação

/home/labadm/
├── startup.log             # Logs de inicialização
├── ngrok_monitor.log       # Logs do monitor Ngrok
└── ngrok-updater.log       # Logs do atualizador Ngrok

Sistema:
├── /var/log/labconnect-deploy.log  # Logs de deploy
└── journalctl -u labconnect        # Logs do serviço systemd
```

---

## 🔧 Configurações de Automação

### Inventário Inteligente
```python
INVENTORY_AUTOMATION = {
    'ENABLED': True,
    'AUTO_CATEGORIZE': True,        # Categorização automática
    'AUTO_ASSIGN_LAB': True,        # Atribuição automática de laboratório
    'BATCH_SIZE': 100,              # Tamanho do lote para processamento
    'MAX_FILE_SIZE': 10485760,      # 10MB máximo para upload
}
```

### Análise de Documentos
```python
# Docling para processamento de documentos
DOCLING_ENABLED = True
DOCLING_MODEL = "pt_core_news_sm"
SPACY_MODEL = 'pt_core_news_sm'

# Configurações de análise
ANALYSIS_BATCH_SIZE = 50
MAX_SIMILAR_MATERIALS = 10
MIN_CONFIDENCE_THRESHOLD = 0.6
```

---

## 🔍 Regras de Negócio

### Agendamento de Laboratórios
1. **Temporalidade**: Professores só podem agendar às quintas e sextas-feiras
2. **Período**: Agendamentos apenas para a semana seguinte
3. **Conflitos**: Sistema verifica automaticamente conflitos de horário
4. **Aprovação**: Todos os agendamentos requerem aprovação de técnico responsável
5. **Turnos Disponíveis**:
   - Matutino: 08:00 - 12:00
   - Noturno: 19:00 - 22:00

### Sistema de Inventário
1. **Categorias**: Consumível, Permanente, Perecível
2. **Estoque Mínimo**: Alertas automáticos quando abaixo do limite
3. **IA Automática**: Categorização inteligente de novos materiais
4. **Importação**: Suporte a Excel, CSV e documentos PDF

---

## 📈 Status Atual do Sistema

### Serviços
- **Django Application**: ❌ Inativo (desde 28/07/2025)
- **PostgreSQL**: ✅ Ativo
- **Redis Cache**: ✅ Ativo
- **Nginx**: ✅ Ativo

### Recursos do Sistema
- **CPU**: Intel Celeron J1800 @ 65% utilização
- **Memória**: 1.1GB usado de 7.6GB total
- **Disco**: 31GB usado de 98GB total
- **Uptime**: 1 dia, 23 horas

### Últimas Atividades
- **Último Deploy**: Ativo até 28/07/2025 15:21:58
- **Duração da Sessão**: 53 minutos e 36 segundos
- **Workers Gunicorn**: 3 processos (PIDs: 2102, 2103, 2104)

---

## 🛠️ Comandos Úteis para Administração

### Gerenciamento do Serviço
```bash
# Iniciar o sistema completo
sudo systemctl start labconnect
./start-labconnect-ngrok.sh start

# Verificar status
sudo systemctl status labconnect
./start-labconnect-ngrok.sh status

# Logs em tempo real
sudo journalctl -u labconnect -f
tail -f /var/www/labconnect/logs/labconnect.log

# Deploy manual
./git-deploy.sh

# Parar todos os serviços
sudo systemctl stop labconnect
./start-labconnect-ngrok.sh stop
```

### Diagnóstico
```bash
# Relatório completo do sistema
./diagnostico-servidor.sh

# Verificar conectividade
curl -I http://localhost
curl -s http://localhost:4040/api/tunnels  # Ngrok

# Verificar banco de dados
sudo -u postgres psql -c "\l"
```

---

## 📋 Recomendações

### Segurança
1. **Atualizar certificados SSL** regularmente
2. **Monitorar logs** de tentativas de acesso
3. **Backup regular** do banco de dados PostgreSQL
4. **Rotacionar secrets** e chaves de API periodicamente

### Performance
1. **Reiniciar o serviço Django** (atualmente inativo)
2. **Monitorar uso de memória** dos workers Gunicorn
3. **Otimizar consultas** de banco de dados pesadas
4. **Implementar cache Redis** para consultas frequentes

### Manutenção
1. **Backup automático** antes de cada deploy
2. **Limpeza de logs** antigos (atualmente mantém 5 backups)
3. **Monitoramento de espaço em disco**
4. **Atualização regular** das dependências Python

---

## 📞 Contatos e Suporte

### Administradores do Sistema
- **Usuário Sistema**: `labadm`
- **Aplicação**: `/var/www/labconnect`
- **Logs**: `/home/labadm/` e `/var/www/labconnect/logs/`

### Técnicos Responsáveis
- **Jason Inoue**: Engenharias e Exatas
- **João Santangelo**: Saúde
- **Cristhian Gusso**: Informática

---

*Documento gerado automaticamente em 30/07/2025*
*Baseado na análise completa do servidor de produção LabConnect*