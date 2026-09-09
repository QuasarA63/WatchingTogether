from django.conf import settings
from django.utils.translation import get_language


def turnstile_context(request):
    """
    Добавляет Turnstile site key в контекст шаблонов.
    """
    return {
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY if settings.TURNSTILE_ENABLED else '',
    }


def language_switch_context(request):
    """
    Текущий путь без языкового префикса (для корректного переключения языка).
    """
    path = request.get_full_path()
    language_code = get_language()
    language_prefix = f'/{language_code}/'
    if path.startswith(language_prefix):
        path = path[len(language_prefix) - 1:]
    return {
        'language_switch_next': path,
    }
