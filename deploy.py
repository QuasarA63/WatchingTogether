#!/usr/bin/env python
"""
Деплой на beget.ru через git pull
"""
import paramiko
from decouple import Config, RepositoryEnv

config = Config(RepositoryEnv('.env.production'))

SSH_HOST = config('SSH_HOST')
SSH_PORT = config('SSH_PORT', default=22, cast=int)
SSH_USER = config('SSH_USER')
SSH_PASSWORD = config('SSH_PASSWORD')
REMOTE_PATH = config('REMOTE_PATH')

def exec_cmd(ssh, cmd):
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out:
        print(out.encode('cp1251', errors='replace').decode('cp1251'))
    if err:
        print(f"STDERR: {err.encode('cp1251', errors='replace').decode('cp1251')}")
    return out, err

def main():
    print("=== Connecting to server ===")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=15)
    
    # Сохраняем .env
    print("\n=== Backing up .env ===")
    exec_cmd(ssh, f'cd {REMOTE_PATH} && cp .env .env.backup 2>/dev/null || echo "No .env to backup"')
    
    # Получаем обновления из git
    print("\n=== Pulling from git ===")
    exec_cmd(ssh, f'cd {REMOTE_PATH} && git fetch origin')
    exec_cmd(ssh, f'cd {REMOTE_PATH} && git reset --hard origin/main')
    
    # Восстанавливаем .env
    print("\n=== Restoring .env ===")
    exec_cmd(ssh, f'cd {REMOTE_PATH} && cp .env.backup .env 2>/dev/null || echo "Restored .env"')
    exec_cmd(ssh, f'cd {REMOTE_PATH} && rm .env.backup 2>/dev/null')
    
    # Показываем последние коммиты
    print("\n=== Recent commits ===")
    exec_cmd(ssh, f'cd {REMOTE_PATH} && git log --oneline -5')
    
    # Применяем миграции (если есть новые)
    print("\n=== Running migrations ===")
    exec_cmd(ssh, f'cd {REMOTE_PATH} && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.production python manage.py migrate')
    
    # Собираем статику
    print("\n=== Collecting static files ===")
    exec_cmd(ssh, f'cd {REMOTE_PATH} && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --noinput')
    
    # Перезапускаем Passenger
    print("\n=== Restarting Passenger ===")
    exec_cmd(ssh, f'cd {REMOTE_PATH} && touch tmp/restart.txt')
    
    # Проверяем конфигурацию
    print("\n=== Checking configuration ===")
    exec_cmd(ssh, f'cd {REMOTE_PATH} && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check')
    
    ssh.close()
    print("\n=== Deploy completed ===")

if __name__ == '__main__':
    main()
