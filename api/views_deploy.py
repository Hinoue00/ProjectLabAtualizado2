import subprocess
import os
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
import hmac
import hashlib

logger = logging.getLogger(__name__)

# Token fixo para deploy (você pode mudar depois)
DEPLOY_TOKEN = "lab-deploy-2024-secure-token-xyz123"

@csrf_exempt
@require_http_methods(["POST"])
def deploy_webhook(request):
    """
    Endpoint para receber webhook do GitHub Actions e executar deploy
    """
    try:
        # Verificar token de autorização
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Token de autorização inválido'}, status=401)
        
        token = auth_header.replace('Bearer ', '')
        if token != DEPLOY_TOKEN:
            return JsonResponse({'error': 'Token não autorizado'}, status=401)
        
        # Parse do JSON
        data = json.loads(request.body)
        commit = data.get('commit', 'unknown')
        branch = data.get('branch', 'unknown')
        
        logger.info(f"🚀 Deploy iniciado - Commit: {commit}, Branch: {branch}")
        
        # Executar script de deploy
        deploy_script = "/home/labadm/git-deploy.sh"
        
        if not os.path.exists(deploy_script):
            logger.error(f"❌ Script de deploy não encontrado: {deploy_script}")
            return JsonResponse({'error': 'Script de deploy não encontrado'}, status=500)
        
        # Executar deploy
        result = subprocess.run(
            [deploy_script], 
            capture_output=True, 
            text=True, 
            timeout=300
        )
        
        if result.returncode == 0:
            logger.info("✅ Deploy executado com sucesso")
            return JsonResponse({
                'status': 'success',
                'message': 'Deploy executado com sucesso',
                'commit': commit,
                'output': result.stdout
            })
        else:
            logger.error(f"❌ Erro no deploy: {result.stderr}")
            return JsonResponse({
                'status': 'error',
                'message': 'Erro na execução do deploy',
                'error': result.stderr
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except subprocess.TimeoutExpired:
        return JsonResponse({'error': 'Deploy timeout (>5min)'}, status=500)
    except Exception as e:
        logger.error(f"❌ Erro inesperado no deploy: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def deploy_status(request):
    """
    Endpoint para verificar status do deploy
    """
    return JsonResponse({
        'status': 'ready',
        'message': 'Deploy webhook está funcionando',
        'token_required': True
    })