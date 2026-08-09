"""
Passenger WSGI entry point для beget.ru
"""
import os
import sys

# Путь к проекту
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# Путь к виртуальному окружению
VENV_PATH = os.path.join(PROJECT_ROOT, 'venv')
sys.path.insert(0, os.path.join(VENV_PATH, 'lib', 'python3.10', 'site-packages'))

# Устанавливаем production настройки
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
