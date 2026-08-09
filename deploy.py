#!/usr/bin/env python
"""
Скрипт для деплоя на beget.ru через SSH
"""
import paramiko
import os
import sys
import tarfile
import io
from pathlib import Path

# Настройки
SSH_HOST = 'lancelot.beget.com'
SSH_PORT = 22
SSH_USER = 'larimagu'
SSH_PASSWORD = 'CucumbeR!!!000'
DOCKER_PORT = 222
REMOTE_PATH = '/home/l/larimagu/wt.larimaritgroup.ru/public_html'

# Файлы и каталоги для исключения
EXCLUDE = {
    '.git', '.gitignore', '.env', '.env.production', 'venv', '__pycache__',
    '*.pyc', '*.pyo', '*.pyd', '.pytest_cache', '.coverage', 'htmlcov',
    'db.sqlite3', 'staticfiles', 'media', 'node_modules', '.vscode', '.idea',
    'tmp', '*.log', '.DS_Store', 'Thumbs.db', 'deploy.py', 'deploy.tar.gz'
}

def should_exclude(path):
    """Проверяет, нужно ли исключить файл/каталог"""
    path_str = str(path)
    parts = Path(path_str).parts
    for part in parts:
        if part in EXCLUDE:
            return True
    for pattern in EXCLUDE:
        if '*' in pattern:
            if pattern.startswith('*') and path_str.endswith(pattern[1:]):
                return True
            if pattern.endswith('*') and path_str.startswith(pattern[:-1]):
                return True
    return False

def create_tar_archive(output_file='deploy.tar.gz'):
    """Создаёт tar.gz архив проекта"""
    print(f"Creating archive {output_file}...")
    with tarfile.open(output_file, 'w:gz') as tar:
        for item in Path('.').iterdir():
            if should_exclude(item):
                continue
            print(f"Adding: {item}")
            tar.add(item, arcname=item.name)
    print(f"Archive created: {os.path.getsize(output_file)} bytes")
    return output_file

def main():
    # Создаём архив
    archive = create_tar_archive()
    
    print("\n=== Connecting to beget ===")
    ssh1 = paramiko.SSHClient()
    ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh1.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=15)
    print("Connected to beget")
    
    # Создаём туннель к Docker
    transport = ssh1.get_transport()
    dest_addr = ('localhost', DOCKER_PORT)
    local_addr = ('127.0.0.1', 2222)
    channel = transport.open_channel('direct-tcpip', dest_addr, local_addr)
    
    print("=== Connecting to Docker ===")
    ssh2 = paramiko.SSHClient()
    ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh2.connect('localhost', port=DOCKER_PORT, username=SSH_USER, password=SSH_PASSWORD, sock=channel, timeout=15)
    print("Connected to Docker")
    
    # Загружаем архив через stdin
    print(f"\n=== Uploading archive ===")
    with open(archive, 'rb') as f:
        archive_data = f.read()
    
    stdin, stdout, stderr = ssh2.exec_command(f'cat > /tmp/deploy.tar.gz')
    stdin.write(archive_data)
    stdin.channel.shutdown_write()
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print(f"STDERR: {err}")
    
    # Распаковываем архив
    print(f"\n=== Extracting archive ===")
    commands = [
        f'cd {REMOTE_PATH} && tar -xzf /tmp/deploy.tar.gz',
        f'rm /tmp/deploy.tar.gz',
        f'cd {REMOTE_PATH} && ls -la',
    ]
    
    for cmd in commands:
        print(f"\nExecuting: {cmd}")
        stdin, stdout, stderr = ssh2.exec_command(cmd)
        print(stdout.read().decode())
        err = stderr.read().decode()
        if err:
            print(f"STDERR: {err}")
    
    ssh2.close()
    ssh1.close()
    
    # Удаляем локальный архив
    os.remove(archive)
    print("\n=== Deploy completed ===")

if __name__ == '__main__':
    main()
