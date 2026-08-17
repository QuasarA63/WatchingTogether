"""
Утилита для серверной верификации Cloudflare Turnstile токенов.
https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
"""

import requests
from django.conf import settings


VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def verify_turnstile(token: str, remote_ip: str = None) -> bool:
    """
    Проверяет Turnstile-токен на стороне сервера.

    Возвращает True, если проверка пройдена или Turnstile отключён.
    """
    if not settings.TURNSTILE_ENABLED:
        return True

    if not token:
        return False

    data = {
        'secret': settings.TURNSTILE_SECRET_KEY,
        'response': token,
    }
    if remote_ip:
        data['remoteip'] = remote_ip

    try:
        resp = requests.post(VERIFY_URL, data=data, timeout=10)
        result = resp.json()
        return result.get('success', False)
    except Exception:
        return False
