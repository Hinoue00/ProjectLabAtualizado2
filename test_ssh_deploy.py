#!/usr/bin/env python3
"""
Script para testar deploy via SSH (fallback quando webhook falha)
"""
import subprocess
import sys

def test_ssh_deploy():
    """
    Testa o deploy via SSH usando os mesmos parâmetros do GitHub Actions
    """
    
    # Configurações (você precisa ajustar estes valores)
    SSH_HOST = "SEU_SERVIDOR_IP"  # Substitua pelo IP real
    SSH_PORT = "2222"
    SSH_USER = "labadm"
    
    print("[INFO] IMPORTANTE: Este script precisa da chave SSH privada configurada")
    print(f"[INFO] Testando conexão SSH: {SSH_USER}@{SSH_HOST}:{SSH_PORT}")
    
    # Comando SSH que o GitHub Actions executaria
    ssh_command = [
        "ssh",
        "-p", SSH_PORT,
        "-o", "StrictHostKeyChecking=no",
        "-o", "UserKnownHostsFile=/dev/null",
        f"{SSH_USER}@{SSH_HOST}",
        """
        set -e
        echo "🚀 Iniciando deploy automático via SSH..."
        echo "📅 Data/Hora: $(date)"
        echo "👤 Usuário: $(whoami)"
        echo "📂 Diretório atual: $(pwd)"
        
        # Ir para o diretório correto
        cd /home/labadm
        echo "📂 Mudando para: $(pwd)"
        
        # Verificar se o script existe
        if [ ! -f "./git-deploy.sh" ]; then
            echo "❌ Erro: git-deploy.sh não encontrado!"
            ls -la
            exit 1
        fi
        
        # Tornar o script executável
        chmod +x ./git-deploy.sh
        
        # Executar o script de deploy
        echo "🔧 Executando git-deploy.sh..."
        ./git-deploy.sh
        
        echo "✅ Deploy concluído!"
        
        # Verificar status do serviço
        echo "🔍 Verificando status do serviço..."
        if sudo systemctl is-active --quiet labconnect; then
            echo "✅ Serviço LabConnect está ativo"
        else
            echo "⚠️ Serviço inativo. Reiniciando..."
            sudo systemctl start labconnect
            sleep 5
        fi
        
        echo "🎉 Deploy finalizado!"
        """
    ]
    
    try:
        print("[INFO] Executando comando SSH...")
        result = subprocess.run(
            ssh_command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutos timeout
        )
        
        if result.returncode == 0:
            print("[SUCCESS] Deploy via SSH executado com sucesso!")
            print("\n=== OUTPUT ===")
            print(result.stdout)
        else:
            print(f"[ERROR] Deploy via SSH falhou (código: {result.returncode})")
            print("\n=== STDERR ===")
            print(result.stderr)
            
    except subprocess.TimeoutExpired:
        print("[ERROR] Timeout - Deploy demorou mais que 5 minutos")
        
    except FileNotFoundError:
        print("[ERROR] Comando SSH não encontrado. Instale OpenSSH Client:")
        print("  Windows: https://docs.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse")
        
    except Exception as e:
        print(f"[ERROR] Erro inesperado: {e}")

def show_instructions():
    """Mostra instruções de configuração"""
    print("""
=== INSTRUÇÕES PARA USAR ESTE SCRIPT ===

1. CONFIGURAR IP DO SERVIDOR:
   - Substitua 'SEU_SERVIDOR_IP' pelo IP real do servidor
   - Se usar domínio, substitua pelo nome do domínio

2. CONFIGURAR CHAVE SSH:
   - Você precisa da chave SSH privada configurada
   - No Windows, coloque em: C:\\Users\\SEU_USUARIO\\.ssh\\id_rsa
   - Ou use: ssh-add caminho_para_chave_privada

3. TESTAR CONEXÃO ANTES:
   ssh -p 2222 labadm@SEU_SERVIDOR_IP

4. EXECUTAR ESTE SCRIPT:
   python test_ssh_deploy.py

=== SE DER ERRO DE PERMISSÃO ===
- Verifique se a chave SSH tem as permissões corretas
- No Windows: icacls arquivo_chave /inheritance:r /grant:r "%username%":"(R)"

=== SECRETS NECESSÁRIOS NO GITHUB ===
Para o deploy automático funcionar, configure estes secrets:
- PROD_HOST: IP ou domínio do servidor
- PROD_PORT: 2222 (porta SSH)
- PROD_USER: labadm
- PROD_SSH_KEY: conteúdo da chave SSH privada
- NGROK_WEBHOOK_URL: https://b84dcf83e918.ngrok-free.app
- DEPLOY_TOKEN: lab-deploy-2024-secure-token-xyz123
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_instructions()
    else:
        print("[START] Teste de deploy via SSH")
        print("=" * 50)
        
        if "SEU_SERVIDOR_IP" in open(__file__).read():
            print("[WARN] Você precisa configurar o IP do servidor primeiro!")
            print("[INFO] Execute: python test_ssh_deploy.py --help")
        else:
            test_ssh_deploy()
        
        print("\n" + "=" * 50)
        print("[INFO] Para mais informações: python test_ssh_deploy.py --help")