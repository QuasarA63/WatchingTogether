"""
Сервисный слой для работы с внешними базами контента.

Основной провайдер — Кинопоиск API (api.kinopoisk.dev):
большая база фильмов и сериалов мира с русскими названиями
и описаниями. Токен получается через @kinopoiskdev_bot
и задаётся в .env как KINOPOISK_API_KEY.

Примечание: TMDB (themoviedb.org) не используется, т.к. домен
заблокирован на уровне DNS как у части провайдеров, так и на
хостинге beget.ru.
"""

import logging

import requests
from decouple import config

logger = logging.getLogger(__name__)

KINOPOISK_API_KEY = config('KINOPOISK_API_KEY', default='')
KINOPOISK_BASE_URL = 'https://api.kinopoisk.dev'

# Соответствие slug категорий типам Кинопоиска
CATEGORY_SLUG_TO_TYPE = {
    'movies': 'movie',
    'series': 'tv-series',
}

# Типы Кинопоиска, которые считаем сериалами
SERIES_TYPES = {'tv-series', 'animated-series', 'anime'}
# Типы, которые считаем фильмами
MOVIE_TYPES = {'movie', 'cartoon', 'animated-film'}


class KinopoiskError(Exception):
    """Ошибка при обращении к Кинопоиск API."""


def is_configured():
    """Проверка, настроен ли API-ключ Кинопоиска."""
    return bool(KINOPOISK_API_KEY)


def _get(endpoint, params=None):
    """Выполнить GET-запрос к Кинопоиск API."""
    if not is_configured():
        raise KinopoiskError('Кинопоиск API не настроен: задайте KINOPOISK_API_KEY в .env')

    url = f'{KINOPOISK_BASE_URL}{endpoint}'
    headers = {'X-API-KEY': KINOPOISK_API_KEY}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.warning('Ошибка запроса к Кинопоиску: %s', exc)
        raise KinopoiskError(f'Ошибка при обращении к Кинопоиску: {exc}') from exc


def _media_type_for(kp_type):
    """Привести тип Кинопоиска к нашему media_type (movie/tv)."""
    if kp_type in SERIES_TYPES:
        return 'tv'
    return 'movie'


def _parse_item(item):
    """Нормализация элемента результата поиска Кинопоиска."""
    title = item.get('name') or item.get('alternativeName') or item.get('enName') or ''
    if not title:
        return None

    poster = item.get('poster') or {}
    rating = item.get('rating') or {}

    return {
        'external_id': str(item.get('id', '')),
        'media_type': _media_type_for(item.get('type')),
        'kp_type': item.get('type'),
        'title': title,
        'original_title': item.get('alternativeName') or item.get('enName') or '',
        'year': item.get('year'),
        'overview': item.get('shortDescription') or item.get('description') or '',
        'poster_url': poster.get('previewUrl') or poster.get('url'),
        'rating': rating.get('kp') or rating.get('imdb'),
    }


def search(query, category_slug=None):
    """
    Поиск контента в Кинопоиске по названию.

    Возвращает список словарей с нормализованными полями:
    external_id, media_type, title, original_title, year, overview, poster_url.

    Примечание: endpoint /movie/search не поддерживает фильтр по типу
    на стороне API, поэтому фильтрация по категории выполняется здесь.
    """
    params = {'page': 1, 'limit': 20, 'query': query}

    data = _get('/v1.4/movie/search', params)

    # Какой media_type соответствует выбранной категории
    wanted_media_type = None
    if category_slug and category_slug in CATEGORY_SLUG_TO_TYPE:
        wanted = CATEGORY_SLUG_TO_TYPE[category_slug]
        wanted_media_type = 'tv' if wanted in SERIES_TYPES else 'movie'

    results = []
    for item in data.get('docs', []):
        parsed = _parse_item(item)
        if not parsed:
            continue
        if wanted_media_type and parsed['media_type'] != wanted_media_type:
            continue
        results.append(parsed)
    return results


def get_details(external_id, media_type=None):
    """
    Получить детальную информацию об объекте Кинопоиска по ID.

    Возвращает нормализованный словарь с полными данными,
    включая жанры и страны.
    """
    data = _get(f'/v1.4/movie/{external_id}')

    title = data.get('name') or data.get('alternativeName') or data.get('enName') or ''
    poster = data.get('poster') or {}
    rating = data.get('rating') or {}

    genres = [g.get('name') for g in data.get('genres', []) if g.get('name')]
    countries = [c.get('name') for c in data.get('countries', []) if c.get('name')]

    return {
        'external_id': str(data.get('id', external_id)),
        'media_type': _media_type_for(data.get('type')),
        'kp_type': data.get('type'),
        'title': title,
        'original_title': data.get('alternativeName') or data.get('enName') or '',
        'year': data.get('year'),
        'overview': data.get('description') or data.get('shortDescription') or '',
        'poster_url': poster.get('url') or poster.get('previewUrl'),
        'genres': genres,
        'countries': countries,
        'rating': rating.get('kp') or rating.get('imdb'),
        'tagline': '',
    }
