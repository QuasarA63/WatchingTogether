#!/usr/bin/env python
"""
Настройка окружения на сервере beget.ru
"""
import paramiko
from decouple import Config, RepositoryEnv

config = Config(RepositoryEnv('.env.production'))

SSH_HOST = config('SSH_HOST')
SSH_PORT = config('SSH_PORT', default=22, cast=int)
SSH_USER = config('SSH_USER')
SSH_PASSWORD = config('SSH_PASSWORD')
DOCKER_PORT = config('DOCKER_PORT', default=222, cast=int)
REMOTE_PATH = config('REMOTE_PATH')

def exec_cmd(ssh, cmd, show_output=True):
    """Выполняет команду и возвращает результат"""
    print(f"\n>>> {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if show_output:
        if out:
            print(out.encode('cp1251', errors='replace').decode('cp1251'))
        if err:
            print(f"STDERR: {err.encode('cp1251', errors='replace').decode('cp1251')}")
    return out, err

def main():
    print("=== Connecting to beget ===")
    ssh1 = paramiko.SSHClient()
    ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh1.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASSWORD, timeout=15)
    
    transport = ssh1.get_transport()
    channel = transport.open_channel('direct-tcpip', ('localhost', DOCKER_PORT), ('127.0.0.1', 2222))
    
    print("=== Connecting to Docker ===")
    ssh2 = paramiko.SSHClient()
    ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh2.connect('localhost', port=DOCKER_PORT, username=SSH_USER, password=SSH_PASSWORD, sock=channel, timeout=15)
    
    # Проверяем Python
    exec_cmd(ssh2, 'python3 --version')
    exec_cmd(ssh2, 'which python3')
    
    # Создаём .env для production
    print("\n=== Creating .env ===")
    env_content = f'''DEBUG=False
SECRET_KEY=django-insecure-wt-production-key-change-me-later
ALLOWED_HOSTS=wt.larimaritgroup.ru

DB_ENGINE={config('DB_ENGINE', default='mysql')}
DB_NAME={config('DB_NAME')}
DB_USER={config('DB_USER')}
DB_PASSWORD={config('DB_PASSWORD')}
DB_HOST={config('DB_HOST', default='localhost')}
DB_PORT={config('DB_PORT', default='3306')}

JWT_ACCESS_TOKEN_LIFETIME=3600
JWT_REFRESH_TOKEN_LIFETIME=86400
'''
    cmd = f"cat > {REMOTE_PATH}/.env << 'ENVEOF'\n{env_content}\nENVEOF"
    exec_cmd(ssh2, cmd)
    
    # Создаём виртуальное окружение
    print("\n=== Creating virtual environment ===")
    exec_cmd(ssh2, f'cd {REMOTE_PATH} && python3 -m venv --copies venv || python3 -m venv --clear venv')
    
    # Устанавливаем зависимости
    print("\n=== Installing dependencies ===")
    exec_cmd(ssh2, f'cd {REMOTE_PATH} && source venv/bin/activate && pip install --upgrade pip')
    exec_cmd(ssh2, f'cd {REMOTE_PATH} && source venv/bin/activate && pip install django==5.2.* djangorestframework djangorestframework-simplejwt drf-spectacular mysqlclient pillow python-decouple django-cors-headers gunicorn whitenoise sentry-sdk')
    
    # Применяем миграции
    print("\n=== Running migrations ===")
    exec_cmd(ssh2, f'cd {REMOTE_PATH} && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.production python manage.py migrate')
    
    # Создаём суперпользователя
    print("\n=== Creating superuser ===")
    exec_cmd(ssh2, f'''cd {REMOTE_PATH} && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.production python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@wt.larimaritgroup.ru', 'admin123'); print('Superuser OK')"''')
    
    # Создаём базовые категории
    print("\n=== Creating categories ===")
    exec_cmd(ssh2, f'''cd {REMOTE_PATH} && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.production python manage.py shell -c "from apps.content.models import Category; Category.objects.get_or_create(name='Movies', slug='movies', defaults={{'icon': 'bi-film'}}); Category.objects.get_or_create(name='Series', slug='series', defaults={{'icon': 'bi-tv'}}); Category.objects.get_or_create(name='Music', slug='music', defaults={{'icon': 'bi-music-note-beamed'}}); print('Categories:', Category.objects.count())"''')
    
    # Собираем статику
    print("\n=== Collecting static files ===")
    exec_cmd(ssh2, f'cd {REMOTE_PATH} && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --noinput')
    
    # Создаём tmp/restart.txt для Passenger
    print("\n=== Setting up Passenger ===")
    exec_cmd(ssh2, f'cd {REMOTE_PATH} && mkdir -p tmp && touch tmp/restart.txt')
    
    # Проверяем конфигурацию
    print("\n=== Checking configuration ===")
    exec_cmd(ssh2, f'cd {REMOTE_PATH} && source venv/bin/activate && DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check')
    
    ssh2.close()
    ssh1.close()
    print("\n=== Setup completed ===")

if __name__ == '__main__':
    main()
