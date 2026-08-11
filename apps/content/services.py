"""
Сервисный слой для работы с внешними базами контента.

Основной провайдер — TMDB (The Movie Database, themoviedb.org):
бесплатный API с русской локализацией, постерами и метаданными
для фильмов и сериалов. Ключ получается на themoviedb.org/settings/api
и задаётся в .env как TMDB_API_KEY.
"""

import logging

import requests
from decouple import config

logger = logging.getLogger(__name__)

TMDB_API_KEY = config('TMDB_API_KEY', default='')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p/w500'

# Соответствие slug категорий типам поиска TMDB
CATEGORY_SLUG_TO_SEARCH_TYPE = {
    'movies': 'movie',
    'series': 'tv',
}


class TMDBError(Exception):
    """Ошибка при обращении к TMDB API."""


def is_configured():
    """Проверка, настроен ли API-ключ TMDB."""
    return bool(TMDB_API_KEY)


def _get(endpoint, params=None):
    """Выполнить GET-запрос к TMDB API."""
    if not is_configured():
        raise TMDBError('TMDB API не настроен: задайте TMDB_API_KEY в .env')

    url = f'{TMDB_BASE_URL}{endpoint}'
    default_params = {'api_key': TMDB_API_KEY, 'language': 'ru-RU'}
    if params:
        default_params.update(params)

    try:
        response = requests.get(url, params=default_params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.warning('Ошибка запроса к TMDB: %s', exc)
        raise TMDBError(f'Ошибка при обращении к TMDB: {exc}') from exc


def _poster_url(poster_path):
    """Полный URL постера или None."""
    if poster_path:
        return f'{TMDB_IMAGE_BASE_URL}{poster_path}'
    return None


def _parse_year(date_string):
    """Извлечь год из строки даты 'YYYY-MM-DD'."""
    if date_string and len(date_string) >= 4:
        try:
            return int(date_string[:4])
        except ValueError:
            return None
    return None


def search(query, category_slug=None):
    """
    Поиск контента в TMDB по названию.

    Возвращает список словарей с нормализованными полями:
    external_id, media_type, title, original_title, year, overview, poster_url.
    """
    results = []

    if category_slug and category_slug in CATEGORY_SLUG_TO_SEARCH_TYPE:
        media_type = CATEGORY_SLUG_TO_SEARCH_TYPE[category_slug]
        data = _get(f'/search/{media_type}', {'query': query, 'include_adult': 'false'})
        for item in data.get('results', []):
            parsed = _parse_item(item, media_type)
            if parsed:
                results.append(parsed)
    else:
        data = _get('/search/multi', {'query': query, 'include_adult': 'false'})
        for item in data.get('results', []):
            media_type = item.get('media_type')
            if media_type not in ('movie', 'tv'):
                continue
            parsed = _parse_item(item, media_type)
            if parsed:
                results.append(parsed)

    return results


def _parse_item(item, media_type):
    """Нормализация элемента результата поиска TMDB."""
    if media_type == 'movie':
        title = item.get('title') or ''
        original_title = item.get('original_title') or ''
        year = _parse_year(item.get('release_date'))
    else:  # tv
        title = item.get('name') or ''
        original_title = item.get('original_name') or ''
        year = _parse_year(item.get('first_air_date'))

    if not title:
        return None

    return {
        'external_id': str(item.get('id', '')),
        'media_type': media_type,
        'title': title,
        'original_title': original_title,
        'year': year,
        'overview': item.get('overview') or '',
        'poster_url': _poster_url(item.get('poster_path')),
        'rating': item.get('vote_average'),
    }


def get_details(external_id, media_type):
    """
    Получить детальную информацию об объекте TMDB.

    Возвращает нормализованный словарь с полными данными,
    включая жанры и страны.
    """
    data = _get(f'/{media_type}/{external_id}')

    if media_type == 'movie':
        title = data.get('title') or ''
        original_title = data.get('original_title') or ''
        year = _parse_year(data.get('release_date'))
    else:
        title = data.get('name') or ''
        original_title = data.get('original_name') or ''
        year = _parse_year(data.get('first_air_date'))

    genres = [g.get('name') for g in data.get('genres', []) if g.get('name')]
    countries = [
        c.get('name') for c in data.get('production_countries', []) if c.get('name')
    ]

    return {
        'external_id': str(data.get('id', external_id)),
        'media_type': media_type,
        'title': title,
        'original_title': original_title,
        'year': year,
        'overview': data.get('overview') or '',
        'poster_url': _poster_url(data.get('poster_path')),
        'genres': genres,
        'countries': countries,
        'rating': data.get('vote_average'),
        'tagline': data.get('tagline') or '',
    }
