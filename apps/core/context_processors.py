from django.conf import settings


def turnstile_context(request):
    """
    Добавляет Turnstile site key в контекст шаблонов.
    """
    return {
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY if settings.TURNSTILE_ENABLED else '',
    }
