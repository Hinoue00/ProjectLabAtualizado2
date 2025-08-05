#!/usr/bin/env python3
"""
Script para triggerar deploy local (executar no próprio servidor)
"""
import subprocess
import os
import sys

def trigger_local_deploy():
    """
    Executa o script de deploy diretamente no servidor
    """
    deploy_script = "/home/labadm/git-deploy.sh" 
    
    print("[INFO] Executando deploy local...")
    print(f"[INFO] Script: {deploy_script}")
    
    # Verificar se estamos no ambiente correto
    if not os.path.exists(deploy_script):
        print(f"[ERROR] Script não encontrado: {deploy_script}")
        print("[INFO] Este script deve ser executado no servidor de produção")
        return False
    
    try:
        # Tornar executável
        os.chmod(deploy_script, 0o755)
        
        # Executar deploy
        print("[INFO] Executando git-deploy.sh...")
        result = subprocess.run(
            [deploy_script],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("[SUCCESS] Deploy executado com sucesso!")
            print("\n=== OUTPUT ===")
            print(result.stdout)
            return True
        else:
            print(f"[ERROR] Deploy falhou (código: {result.returncode})")
            print("\n=== STDERR ===")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("[ERROR] Deploy demorou mais que 5 minutos")
        return False
        
    except PermissionError:
        print("[ERROR] Sem permissão para executar o script")
        print("[FIX] Execute: chmod +x /home/labadm/git-deploy.sh")
        return False
        
    except Exception as e:
        print(f"[ERROR] Erro inesperado: {e}")
        return False

def check_services():
    """Verifica status dos serviços"""
    print("\n[INFO] Verificando serviços...")
    
    services = ['labconnect', 'nginx', 'postgresql']
    
    for service in services:
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service],
                capture_output=True,
                text=True
            )
            
            status = result.stdout.strip()
            if status == 'active':
                print(f"[OK] {service}: ✅ Ativo")
            else:
                print(f"[WARN] {service}: ❌ {status}")
                
        except Exception as e:
            print(f"[ERROR] Não foi possível verificar {service}: {e}")

def show_logs():
    """Mostra últimas linhas do log"""
    log_file = "/var/www/labconnect/logs/labconnect.log"
    
    if os.path.exists(log_file):
        print(f"\n[INFO] Últimas linhas do log ({log_file}):")
        try:
            result = subprocess.run(
                ['tail', '-20', log_file],
                capture_output=True,
                text=True
            )
            print(result.stdout)
        except Exception as e:
            print(f"[ERROR] Não foi possível ler o log: {e}")
    else:
        print(f"[WARN] Log não encontrado: {log_file}")

if __name__ == "__main__":
    print("[START] Deploy Manual Local")
    print("=" * 50)
    
    # Verificar se estamos no servidor
    hostname = os.uname().nodename if hasattr(os, 'uname') else 'Windows'
    print(f"[INFO] Hostname: {hostname}")
    
    if sys.platform == 'win32':
        print("[ERROR] Este script deve ser executado no servidor Linux")
        print("[INFO] Use o script test_ssh_deploy.py no Windows")
        sys.exit(1)
    
    # Executar deploy
    success = trigger_local_deploy()
    
    # Verificar serviços
    check_services()
    
    # Mostrar logs
    show_logs()
    
    print("\n" + "=" * 50)
    if success:
        print("[RESULT] ✅ Deploy concluído com sucesso!")
    else:
        print("[RESULT] ❌ Deploy falhou - verifique logs acima")