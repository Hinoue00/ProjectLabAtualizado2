# api/views.py
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db import models
import json
import logging
import requests
from django.conf import settings

# Configure o logging
logger = logging.getLogger(__name__)

@login_required
@csrf_exempt
def llama_assistant(request):
    """
    API endpoint para interagir com o assistente IA via Llama local com streaming.
    """
    # Verificar se o chatbot está habilitado
    if not getattr(settings, 'CHATBOT_ENABLED', False):
        return JsonResponse({'error': 'Chatbot is currently disabled'}, status=503)
        
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        
        if not user_message:
            return JsonResponse({'error': 'No message provided'}, status=400)

        # Obter dados em tempo real do banco de dados
        real_time_context = get_real_time_context(user_message, request.user)

        # Obter contexto baseado na pergunta
        topical_context = get_context_for_query(user_message)

        # Combinar os contextos
        combined_context = real_time_context + "\n" + topical_context
        
        # Template para o sistema
        system_prompt = """
            Você é o assistente virtual oficial do sistema LabConnect para gerenciamento de laboratórios da Faculdade Unopar-Anhanguera.

            SOBRE O SISTEMA LABCONNECT:
            - O sistema otimiza o trabalho de laboratoristas e professores da rede universitária
            - Os laboratoristas podem ver agendamentos, gerenciar inventários, analisar gráficos e relatórios
            - Os professores agendam laboratórios, verificam disponibilidade e requisitam materiais
            - Apenas às quintas e sextas-feiras os professores podem agendar laboratórios para a semana seguinte

            LABORATORISTAS RESPONSÁVEIS:
            - Jason Inoue: Responsável pelos laboratórios de engenharias e exatas
            - João Santangelo: Responsável pelos laboratórios de saúde
            - Cristhian Gusso: Responsável pelos laboratórios de informática

            FUNCIONALIDADES PRINCIPAIS:
            1. Sistema de Login/Registro com aprovação de laboratoristas
            2. Dashboard personalizado para cada tipo de usuário
            3. Agendamento de laboratórios com regras temporais específicas
            4. Gerenciamento de inventário com categorização de materiais
            5. Sistema de aprovação de agendamentos pelos laboratoristas
            6. Geração de relatórios com gráficos e estatísticas
            7. Calendário interativo de reservas e disponibilidade

            Responda de forma útil, amigável e precisa, porém resumida, mantendo sempre o tom institucional e educativo.
        """
        
        # Retornar uma resposta de streaming usando o Llama local
        response = StreamingHttpResponse(
            get_local_llama_streaming_response(user_message, system_prompt, combined_context),
            content_type='application/json'
        )
        return response
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return JsonResponse({'error': 'Error processing request'}, status=500)

def get_context_for_query(user_query):
    """Recupera informações relevantes do sistema baseadas na consulta do usuário"""
    context = ""
    
    # Palavras-chave para buscar no banco de dados
    query_lower = user_query.lower()
    
    # Verificar o que está sendo perguntado e adicionar contexto específico
    if "agendamento" in query_lower or "agendar" in query_lower or "reserva" in query_lower:
        # Adicionar informações sobre agendamento
        context += """
        REGRAS DE AGENDAMENTO:
        - Os professores só podem agendar laboratórios às quintas e sextas-feiras
        - Os agendamentos são apenas para a semana seguinte (segunda a sexta)
        - O professor deve fornecer: laboratório, data, horário, disciplina, número de alunos e materiais necessários
        - Todos os agendamentos precisam ser aprovados por um laboratorista responsável
        """
    
    if "material" in query_lower or "inventário" in query_lower or "estoque" in query_lower:
        # Adicionar informações sobre inventário
        context += """
        SISTEMA DE INVENTÁRIO:
        - Os materiais são categorizados como: Consumíveis, Permanentes e Perecíveis
        - O sistema alerta quando um item está abaixo do estoque mínimo
        - Cada laboratório possui seu próprio inventário
        - A importação em lote pode ser feita via arquivos Excel ou CSV
        """
    
    if "relatório" in query_lower or "gráfico" in query_lower or "estatística" in query_lower:
        # Adicionar informações sobre relatórios
        context += """
        RELATÓRIOS DISPONÍVEIS:
        - Relatórios de agendamentos (por período, laboratório ou professor)
        - Relatórios de inventário (materiais em estoque, consumo, alertas)
        - Relatórios de atividade de usuários
        - Todos os relatórios podem ser exportados em PDF, Excel ou CSV
        - Gráficos podem ser incluídos nos relatórios PDF
        """
    
    return context
    
def get_local_llama_streaming_response(user_message, system_prompt, context=""):
    """
    Função geradora que retorna chunks de resposta do Llama local via Ollama (streaming).
    """
    # URL da API Ollama
    api_url = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/api/chat')
    
    # Construir a mensagem com o sistema e a entrada do usuário
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    
    # Adicione contexto se fornecido
    if context:
        messages.append({"role": "system", "content": f"Contexto atual: {context}"})
        
    # Adicione a mensagem do usuário
    messages.append({"role": "user", "content": user_message})
    
    # Dados para enviar ao Ollama
    data = {
        "model": getattr(settings, 'OLLAMA_MODEL', 'labconnect-assistant'),
        "messages": messages,
        "stream": True,     # Ativar streaming
    }
    
    # Cabeçalhos para a API
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Fazer requisição ao Ollama com streaming
        with requests.post(api_url, json=data, headers=headers, stream=True) as response:
            response.raise_for_status()  # Levantar exceção para erros HTTP
            
            accumulated_text = ""
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    
                    # Decodificar o JSON
                    try:
                        chunk = json.loads(line_text)
                        if 'message' in chunk:
                            content = chunk['message'].get('content', '')
                            if content:
                                accumulated_text += content
                                yield json.dumps({"chunk": content, "full": accumulated_text}) + '\n'
                    except json.JSONDecodeError:
                        logger.error(f"Erro ao decodificar JSON: {line_text}")
                        continue
    
    except Exception as e:
        logger.error(f"Erro na comunicação com Ollama local: {str(e)}")
        yield json.dumps({"error": str(e)}) + '\n'

def get_real_time_context(user_query, user):
    """Obtém dados relevantes do banco de dados baseado na consulta"""
    context = ""
    query_lower = user_query.lower()
    
    # Fornecer dados de laboratório
    if "laboratório" in query_lower or "laboratórios" in query_lower:
        try:
            from laboratories.models import Laboratory
            labs = Laboratory.objects.all()[:5]  # Limitar para 5 para não sobrecarregar
            
            lab_info = "Laboratórios disponíveis:\n"
            for lab in labs:
                lab_info += f"- {lab.name}: {lab.location}, capacidade para {lab.capacity} pessoas\n"
            
            context += lab_info
        except Exception as e:
            logger.error(f"Erro ao obter laboratórios: {str(e)}")
    
    # Fornecer dados de materiais com baixo estoque (se o usuário for técnico)
    if (user.user_type == 'technician') and ("estoque" in query_lower or "material" in query_lower):
        try:
            from inventory.models import Material
            low_stock = Material.objects.filter(quantity__lt=models.F('minimum_stock'))[:5]
            
            if low_stock:
                stock_info = "Materiais com estoque baixo:\n"
                for material in low_stock:
                    stock_info += f"- {material.name}: {material.quantity}/{material.minimum_stock} (disponível/mínimo)\n"
                
                context += stock_info
        except Exception as e:
            logger.error(f"Erro ao obter materiais: {str(e)}")
    
    # Fornecer dados de agendamentos pendentes (para técnicos)
    if (user.user_type == 'technician') and ("pendente" in query_lower or "agendamento" in query_lower):
        try:
            from scheduling.models import ScheduleRequest
            pending = ScheduleRequest.objects.filter(status='pending').count()
            
            context += f"Existem {pending} solicitações de agendamento pendentes de aprovação.\n"
        except Exception as e:
            logger.error(f"Erro ao obter agendamentos: {str(e)}")
    
    return context

@login_required
@csrf_exempt
def assistant_feedback(request):
    """API para feedback do assistente"""
    # Verificar se o chatbot está habilitado
    if not getattr(settings, 'CHATBOT_ENABLED', False):
        return JsonResponse({'error': 'Chatbot is currently disabled'}, status=503)
        
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            feedback_value = data.get('value')
            user_question = data.get('question')
            ai_response = data.get('response')
            
            # Salvar no banco de dados
            from api.models import AIFeedback
            feedback = AIFeedback.objects.create(
                user=request.user,
                question=user_question,
                response=ai_response,
                is_helpful=(feedback_value == 'good')
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@login_required
def assistant_page(request):
    """View para a página do assistente Llama"""
    # Verificar se o chatbot está habilitado
    if not getattr(settings, 'CHATBOT_ENABLED', False):
        return JsonResponse({'error': 'Chatbot is currently disabled'}, status=503)
        
    # Obter o contexto da página atual (opcional)
    current_path = request.path
    context_info = ""
    
    if "laboratories" in current_path:
        context_info = "O usuário está visualizando informações de laboratório"
    elif "inventory" in current_path:
        context_info = "O usuário está gerenciando inventário"
    elif "scheduling" in current_path:
        context_info = "O usuário está trabalhando com agendamento de laboratório"
    
    # Verificar se Ollama está disponível
    ollama_available = False
    try:
        ollama_url = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/api/chat')
        base_url = ollama_url.rsplit('/', 2)[0]  # Remove '/api/chat'
        requests.get(f"{base_url}/api/version", timeout=1)
        ollama_available = True
    except:
        ollama_available = False
    
    return render(request, 'assistant_page.html', {
        'context_info': context_info,
        'ollama_available': ollama_available
    })

@login_required
def test_chatbot_page(request):
    """Página de teste do chatbot"""
    # Verificar se o chatbot está habilitado
    if not getattr(settings, 'CHATBOT_ENABLED', False):
        return JsonResponse({'error': 'Chatbot is currently disabled'}, status=503)
    return render(request, 'test_chatbot.html')

# Função auxiliar para obter o token CSRF (se necessário)
def get_csrf_token(request):
    from django.middleware.csrf import get_token
    return get_token(request)