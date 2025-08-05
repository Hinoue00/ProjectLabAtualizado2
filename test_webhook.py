#!/usr/bin/env python3
"""
Script para testar o webhook de deploy
"""
import requests
import json
import urllib3

# Suprimir avisos de SSL para ngrok
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurações
WEBHOOK_URL = "https://b84dcf83e918.ngrok-free.app/api/deploy/"
DEPLOY_TOKEN = "lab-deploy-2024-secure-token-xyz123"

def test_webhook():
    """Testa se o webhook está funcionando"""
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {DEPLOY_TOKEN}'
    }
    
    data = {
        'commit': 'test-commit-123',
        'branch': 'refs/heads/main'
    }
    
    try:
        print(f"[INFO] Testando webhook: {WEBHOOK_URL}")
        response = requests.post(WEBHOOK_URL, headers=headers, json=data, timeout=10, verify=False)
        
        print(f"[INFO] Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[SUCCESS] Webhook funcionando!")
            print(f"[INFO] Resposta: {response.json()}")
        else:
            print(f"[ERROR] Webhook falhou: {response.status_code}")
            print(f"[INFO] Erro: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Erro de conexão: {e}")
        print("[INFO] Possíveis causas:")
        print("  - URL incorreta")
        print("  - Servidor offline")
        print("  - Ngrok não está rodando")

def test_status():
    """Testa o endpoint de status"""
    status_url = WEBHOOK_URL.replace('/deploy/', '/deploy/status/')
    
    try:
        print(f"[INFO] Testando status: {status_url}")
        response = requests.get(status_url, timeout=10, verify=False)
        
        print(f"[INFO] Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[SUCCESS] Status endpoint funcionando!")
            print(f"[INFO] Resposta: {response.json()}")
        else:
            print(f"[ERROR] Status endpoint falhou: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Erro de conexão: {e}")

if __name__ == "__main__":
    print("[START] Testando sistema de webhook de deploy")
    print("=" * 50)
    
    print("\n1. Testando endpoint de status...")
    test_status()
    
    print("\n2. Testando webhook de deploy...")
    test_webhook()
    
    print("\n" + "=" * 50)
    print("[INFO] Teste concluído!")
    print("[NEXT] Verifique os resultados acima.")