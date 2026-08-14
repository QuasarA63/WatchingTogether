from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Получить значение из словаря по ключу."""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def times(number):
    """Вернуть range от 1 до number включительно (для циклов в шаблоне)."""
    return range(1, int(number) + 1)
