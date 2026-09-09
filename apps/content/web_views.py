from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from datetime import date, datetime, timedelta, timezone
from .models import Category, Genre, ContentItem, UserContentItem, Person, ContentItemPerson
from . import services


def _parse_air_date(date_str):
    """Парсинг даты выхода из ISO-строки в объект date."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return None


def _collect_episodes(seasons):
    """
    Собрать эпизоды со всех сезонов в плоский список.

    Возвращает список словарей:
    [{season, episode, name, air_date}, ...]
    Только эпизоды с известной датой выхода.
    """
    episodes = []
    for season in seasons:
        season_num = season.metadata.get('season_number')
        for ep in season.metadata.get('episodes', []) or []:
            air_date = _parse_air_date(ep.get('air_date'))
            if not air_date:
                continue
            episodes.append({
                'season': season_num,
                'episode': ep.get('number'),
                'name': ep.get('name', ''),
                'air_date': air_date,
            })
    return episodes


def _find_next_episode(seasons, today=None):
    """
    Ближайшая ещё не вышедшая серия (дата выхода в будущем).

    Возвращает словарь {season, episode, name, air_date}
    или None, если анонсированных серий нет.
    """
    today = today or date.today()
    upcoming = [e for e in _collect_episodes(seasons) if e['air_date'] > today]
    if not upcoming:
        return None
    return min(upcoming, key=lambda e: e['air_date'])


def item_new_updates(item, max_age_days=30):
    """
    Свежие сведения о новых сериях и сезонах объекта.

    Возвращает (new_episodes, new_seasons) из metadata объекта,
    если сведения ещё актуальны (не старше max_age_days), иначе ([], []).
    """
    meta = item.metadata or {}
    new_episodes = meta.get('new_episodes') or []
    new_seasons = meta.get('new_seasons') or []
    if not (new_episodes or new_seasons):
        return [], []
    updates_at = meta.get('new_updates_at')
    if updates_at:
        try:
            dt = datetime.fromisoformat(updates_at)
        except (ValueError, TypeError):
            dt = None
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - dt > timedelta(days=max_age_days):
                return [], []

    # Приводим air_date к объектам date для форматирования в шаблонах
    display_episodes = []
    for ep in new_episodes:
        ep = dict(ep)
        try:
            ep['air_date'] = date.fromisoformat(ep.get('air_date', ''))
        except (ValueError, TypeError):
            pass
        display_episodes.append(ep)
    return display_episodes, new_seasons


def released_episode_keys(seasons, today=None):
    """
    Ключи (season, episode) эпизодов, уже вышедших (air_date <= сегодня).

    seasons — список словарей из services.get_seasons.
    """
    today = today or date.today()
    keys = set()
    for season in seasons:
        season_num = season.get('number')
        for ep in season.get('episodes', []) or []:
            air_date = _parse_air_date(ep.get('air_date'))
            if air_date and air_date <= today:
                keys.add((season_num, ep.get('number')))
    return keys


def season_numbers(seasons):
    """Номера сезонов из списка словарей services.get_seasons."""
    return {s.get('number') for s in seasons}


# Транслитерация кириллицы для slug
TRANSLIT_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
    'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
    'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
    'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def transliterate(text):
    """Транслитерация кириллицы в латиницу."""
    return ''.join(TRANSLIT_MAP.get(c, c) for c in text.lower())


def make_slug(name):
    """Создать slug из названия с поддержкой кириллицы."""
    slug = slugify(name)
    if not slug:
        # Для кириллицы используем транслитерацию
        slug = slugify(transliterate(name))
    return slug or f'genre-{Genre.objects.count() + 1}'


def content_list(request):
    """
    Каталог контента с фильтрами по категории, жанру и поиском.
    Показывает только родительские объекты (без вложенных сезонов).
    """
    items = ContentItem.objects.filter(
        is_active=True,
        parent__isnull=True,
    ).select_related('category').prefetch_related(
        'genres'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    )

    category_slug = request.GET.get('category', '')
    genre_slug = request.GET.get('genre', '')
    search = request.GET.get('q', '')
    ended = request.GET.get('ended', '')

    if category_slug:
        items = items.filter(category__slug=category_slug)
    if genre_slug:
        items = items.filter(genres__slug=genre_slug)
    if ended == 'ended':
        items = items.filter(metadata__ended=True)
    elif ended == 'ongoing':
        items = items.filter(metadata__ended=False)
    if search:
        items = items.filter(title__icontains=search)

    items = items.order_by('-created_at').distinct()

    paginator = Paginator(items, 12)
    page_number = request.GET.get('page')
    items_page = paginator.get_page(page_number)

    categories = Category.objects.all()
    genres = Genre.objects.all()

    context = {
        'items_page': items_page,
        'categories': categories,
        'genres': genres,
        'current_category': category_slug,
        'current_genre': genre_slug,
        'current_ended': ended,
        'search': search,
    }
    return render(request, 'pages/content_list.html', context)


def content_detail(request, pk):
    """
    Страница контента с отзывами.
    Для сериалов показывает список сезонов с отзывами на каждый.
    """
    item = get_object_or_404(
        ContentItem.objects.select_related('category', 'parent').prefetch_related(
            'genres', 'persons__person'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            reviews_count=Count('reviews')
        ),
        pk=pk
    )
    reviews = item.reviews.select_related('user', 'group').order_by('-created_at')

    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)

    user_review = None
    if request.user.is_authenticated:
        user_review = item.reviews.filter(user=request.user).first()

    # Группировка персон по ролям для шаблона
    persons_by_role = {}
    for cp in item.persons.select_related('person').order_by('role', 'person__name'):
        role_display = cp.get_role_display()
        if role_display not in persons_by_role:
            persons_by_role[role_display] = []
        persons_by_role[role_display].append(cp.person.name)

    # Сезоны (дочерние объекты) с аннотацией рейтингов
    seasons = item.children.filter(is_active=True).annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews'),
    ).order_by('metadata__season_number')

    # Даты выхода сезонов (из метаданных эпизодов)
    season_air_dates = {}
    today = date.today()
    for season in seasons:
        episodes = season.metadata.get('episodes', [])
        dates = []
        total_episodes = len(episodes)
        for ep in episodes:
            d = _parse_air_date(ep.get('air_date'))
            if d:
                dates.append(d)
        if dates:
            # Сезон незавершён, если:
            # 1. Не у всех эпизодов есть даты, ИЛИ
            # 2. Дата последнего эпизода в будущем
            is_ongoing = len(dates) < total_episodes or max(dates) > today
            season_air_dates[season.pk] = {
                'first': min(dates),
                'last': max(dates),
                'is_ongoing': is_ongoing,
            }

    # Отзывы пользователя на сезоны (если авторизован)
    user_season_reviews = {}
    if request.user.is_authenticated and seasons:
        from apps.reviews.models import Review
        season_ids = [s.id for s in seasons]
        user_reviews_qs = Review.objects.filter(
            user=request.user,
            content_item_id__in=season_ids,
        )
        user_season_reviews = {r.content_item_id: r for r in user_reviews_qs}

    # Эпизоды с датами (если это сезон)
    episodes_with_dates = []
    if item.is_season:
        for ep in item.metadata.get('episodes', []):
            air_date = _parse_air_date(ep.get('air_date'))
            episodes_with_dates.append({
                'number': ep.get('number'),
                'name': ep.get('name', ''),
                'air_date': air_date,
                'is_upcoming': bool(air_date and air_date > today),
                'description': ep.get('description', ''),
            })
        episodes_with_dates.sort(key=lambda e: e['number'] or 0)

    # Ближайшая ещё не вышедшая серия (только для сериала с сезонами)
    next_episode = None
    if seasons and not item.is_season:
        next_episode = _find_next_episode(seasons, today)
        if next_episode:
            days_left = (next_episode['air_date'] - today).days
            next_episode['days_left'] = days_left
            next_episode['days_label'] = ngettext(
                'через %(days)d день',
                'через %(days)d дней',
                days_left,
            ) % {'days': days_left}

    # Свежие сведения о новых сериях и сезонах (для сериала)
    new_episodes, new_seasons = item_new_updates(item) if not item.is_season else ([], [])
    new_episode_seasons = {e.get('season') for e in new_episodes}
    new_season_numbers = set(new_seasons)
    season_badges = {}
    for season in seasons:
        season_num = season.metadata.get('season_number')
        if season_num in new_season_numbers:
            season_badges[season.pk] = 'Новый сезон'
        elif season_num in new_episode_seasons:
            season_badges[season.pk] = 'Новая серия'

    context = {
        'item': item,
        'reviews_page': reviews_page,
        'user_review': user_review,
        'persons_by_role': persons_by_role,
        'seasons': seasons,
        'user_season_reviews': user_season_reviews,
        'season_air_dates': season_air_dates,
        'episodes_with_dates': episodes_with_dates,
        'next_episode': next_episode,
        'new_episodes': new_episodes,
        'new_seasons': new_seasons,
        'new_episode_seasons': new_episode_seasons,
        'new_season_numbers': new_season_numbers,
        'season_badges': season_badges,
    }
    return render(request, 'pages/content_detail.html', context)


@login_required
def content_refresh_dates(request, pk):
    """
    Обновить даты выхода серий и сезонов сериала с Кинопоиска (POST).
    """
    item = get_object_or_404(ContentItem, pk=pk, is_active=True)

    if request.method != 'POST':
        return redirect('content_detail', pk=pk)

    if item.is_season or item.category.slug != 'series' or not item.external_id:
        messages.error(request, _('Даты выхода можно обновлять только для сериала.'))
        return redirect('content_detail', pk=pk)

    if not services.is_configured():
        messages.error(request, _('Кинопоиск API не настроен: задайте KINOPOISK_API_KEY.'))
        return redirect('content_detail', pk=pk)

    seasons_ok = _import_seasons(item, item.external_id)
    _refresh_ended_flag(item)
    if seasons_ok:
        messages.success(request, _('Даты выхода серий и статус сериала обновлены.'))
    else:
        messages.error(request, _('Не удалось обновить даты. Попробуйте позже.'))

    return redirect('content_detail', pk=pk)


@login_required
def my_content_list(request):
    """
    Вкладка «Мои объекты»: список объектов пользователя
    с фильтрами по категории, жанру, статусу и личными комментариями.
    """
    entries = UserContentItem.objects.filter(
        user=request.user,
        content_item__is_active=True,
        content_item__parent__isnull=True,
    ).select_related('content_item', 'content_item__category').prefetch_related(
        'content_item__genres'
    )

    category_slug = request.GET.get('category', '')
    if category_slug:
        entries = entries.filter(content_item__category__slug=category_slug)

    genre_slug = request.GET.get('genre', '')
    if genre_slug:
        entries = entries.filter(content_item__genres__slug=genre_slug)

    status_filter = request.GET.get('status', '')
    if status_filter:
        entries = entries.filter(status=status_filter)

    ended = request.GET.get('ended', '')
    if ended == 'ended':
        entries = entries.filter(content_item__metadata__ended=True)
    elif ended == 'ongoing':
        entries = entries.filter(content_item__metadata__ended=False)

    search = request.GET.get('q', '')
    if search:
        entries = entries.filter(content_item__title__icontains=search)

    entries = entries.order_by('-created_at').distinct()

    paginator = Paginator(entries, 12)
    page_number = request.GET.get('page')
    entries_page = paginator.get_page(page_number)

    # Средние оценки по сезонам для объектов со статусом «Смотрю»/«Отложил»
    season_ratings = {}
    # Даты выхода серий для объектов со статусом «Смотрю»/«Отложил»
    episode_dates = {}
    status_items = [
        e.content_item for e in entries_page
        if e.status in (UserContentItem.Status.WATCHING, UserContentItem.Status.ON_HOLD)
    ]
    if status_items:
        seasons_qs = ContentItem.objects.filter(
            parent__in=status_items,
            is_active=True,
        ).annotate(
            avg_rating=Avg('reviews__rating'),
        ).order_by('metadata__season_number')
        for season in seasons_qs:
            if season.avg_rating is not None:
                season_ratings.setdefault(season.parent_id, []).append({
                    'number': season.metadata.get('season_number'),
                    'avg': round(season.avg_rating),  # 1-10, целое
                })

            # Собираем даты выхода эпизодов
            episodes = season.metadata.get('episodes', [])
            dates = []
            for ep in episodes:
                d = _parse_air_date(ep.get('air_date'))
                if d:
                    dates.append({
                        'season': season.metadata.get('season_number'),
                        'episode': ep.get('number'),
                        'name': ep.get('name', ''),
                        'air_date': d,
                    })
            if dates:
                episode_dates.setdefault(season.parent_id, []).extend(dates)

    # Для каждого сериала найдём последнюю вышедшую серию
    today = date.today()
    latest_episodes = {}
    for parent_id, eps in episode_dates.items():
        # Сортируем по дате (от новых к старым)
        eps.sort(key=lambda e: e['air_date'], reverse=True)
        # Берём последнюю вышедшую (дата <= сегодня)
        for ep in eps:
            if ep['air_date'] <= today:
                latest_episodes[parent_id] = ep
                break
        # Если все даты в будущем — берём ближайшую
        if parent_id not in latest_episodes and eps:
            eps.sort(key=lambda e: e['air_date'])
            latest_episodes[parent_id] = eps[0]

    # Для каждого сериала найдём ближайшую ещё не вышедшую серию
    next_episodes = {}
    for parent_id, eps in episode_dates.items():
        upcoming = [e for e in eps if e['air_date'] > today]
        if upcoming:
            next_episodes[parent_id] = min(upcoming, key=lambda e: e['air_date'])

    # Свежие сведения о новых сериях и сезонах для каждого объекта
    new_updates = {}
    for entry in entries_page:
        eps, seasons = item_new_updates(entry.content_item)
        if eps or seasons:
            new_updates[entry.content_item.pk] = {
                'episodes': eps,
                'seasons': seasons,
                'episode_seasons': {e.get('season') for e in eps},
                'season_numbers': set(seasons),
            }

    categories = Category.objects.all()
    genres = Genre.objects.all()
    status_choices = UserContentItem.Status.choices

    context = {
        'entries_page': entries_page,
        'categories': categories,
        'genres': genres,
        'status_choices': status_choices,
        'current_category': category_slug,
        'current_genre': genre_slug,
        'current_status': status_filter,
        'current_ended': ended,
        'search': search,
        'search_configured': services.is_configured(),
        'season_ratings': season_ratings,
        'latest_episodes': latest_episodes,
        'next_episodes': next_episodes,
        'new_updates': new_updates,
    }
    return render(request, 'pages/my_content_list.html', context)


@login_required
def my_content_search(request):
    """
    Поиск объекта по названию во внешней базе (Кинопоиск).
    """
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '')
    results = []
    search_error = None

    if query:
        try:
            results = services.search(query, category_slug or None)
        except services.KinopoiskError as exc:
            search_error = str(exc)

    categories = Category.objects.all()

    context = {
        'query': query,
        'categories': categories,
        'current_category': category_slug,
        'results': results,
        'search_error': search_error,
        'search_configured': services.is_configured(),
    }
    return render(request, 'pages/my_content_search.html', context)


def _category_for_media_type(media_type):
    """Категория БД, соответствующая типу объекта (movie/tv)."""
    slug = 'movies' if media_type == 'movie' else 'series'
    return Category.objects.filter(slug=slug).first()


def _get_or_create_genres(genre_names):
    """Получить или создать жанры по списку названий."""
    genres = []
    for name in genre_names:
        name = name.strip()
        if not name:
            continue
        # Сначала ищем по имени (уникальное поле)
        genre = Genre.objects.filter(name=name).first()
        if genre is None:
            slug = make_slug(name)
            # Проверяем уникальность slug
            base_slug = slug
            counter = 1
            while Genre.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            genre = Genre.objects.create(name=name, slug=slug)
        genres.append(genre)
    return genres


def _get_or_create_persons(persons_data):
    """
    Получить или создать персоны и привязать их к элементу контента.

    Принимает список словарей из services._parse_persons:
    [{external_id, name, photo, role}, ...]
    """
    results = []
    for p_data in persons_data:
        name = p_data.get('name', '').strip()
        if not name:
            continue

        # Ищем по external_id, если есть, иначе по имени
        person = None
        ext_id = p_data.get('external_id', '')
        if ext_id:
            person = Person.objects.filter(external_id=ext_id).first()
        if person is None:
            person = Person.objects.filter(name=name).first()
        if person is None:
            person = Person.objects.create(
                name=name,
                external_id=ext_id,
                photo=p_data.get('photo', ''),
            )

        role = p_data.get('role', '')
        if role:
            _, created = ContentItemPerson.objects.get_or_create(
                content_item=p_data['_content_item'],
                person=person,
                role=role,
            )
            results.append(person)
    return results


def _import_seasons(series_item, external_id, seasons_data=None):
    """
    Импортировать сезоны сериала с Кинопоиска.

    Создаёт дочерние ContentItem для каждого сезона и обновляет
    даты выхода у уже существующих. Возвращает True при успехе.

    Аргумент seasons_data позволяет передать уже полученный список
    сезонов (чтобы не делать повторный запрос к API).
    """
    import logging
    logger = logging.getLogger(__name__)

    if seasons_data is None:
        try:
            seasons = services.get_seasons(external_id)
        except services.KinopoiskError as exc:
            logger.warning('Не удалось получить сезоны для %s: %s', external_id, exc)
            return False
    else:
        seasons = seasons_data

    for season_data in seasons:
        season_num = season_data['number']
        season_title = f'{series_item.title}. {season_data["name"]}'

        # Проверяем, не создан ли уже этот сезон
        existing = series_item.children.filter(
            metadata__season_number=season_num,
        ).first()
        if existing:
            # Обновляем даты выхода эпизодов (планируемые даты меняются со временем)
            changed = False
            if existing.metadata.get('episodes') != season_data['episodes']:
                existing.metadata['episodes'] = season_data['episodes']
                changed = True
            if existing.metadata.get('episodes_count') != season_data['episodes_count']:
                existing.metadata['episodes_count'] = season_data['episodes_count']
                changed = True
            if changed:
                existing.save(update_fields=['metadata', 'updated_at'])
                logger.info('Обновлены даты сезона %s для «%s»', season_num, series_item.title)
            continue

        ContentItem.objects.create(
            parent=series_item,
            category=series_item.category,
            title=season_title,
            original_title=season_data.get('en_name', ''),
            description='',
            year=series_item.year,
            external_id=f'{external_id}_s{season_num}',
            metadata={
                'source': 'kinopoisk',
                'media_type': 'season',
                'season_number': season_num,
                'episodes_count': season_data['episodes_count'],
                'episodes': season_data['episodes'],
            },
        )
        logger.info('Создан сезон %s для «%s»', season_num, series_item.title)

    return True


def _refresh_ended_flag(item):
    """
    Обновить признак завершённости сериала с Кинопоиска.

    Записывает в metadata['ended'] True/False и metadata['ended_year'].
    Возвращает True при успехе.
    """
    if not item.external_id:
        return False
    try:
        details = services.get_details(item.external_id, 'tv')
    except services.KinopoiskError:
        return False
    item.metadata['ended'] = bool(details.get('is_ended'))
    item.metadata['ended_year'] = details.get('ended_year')
    item.save(update_fields=['metadata', 'updated_at'])
    return True


@login_required
def my_content_add(request):
    """
    Добавление найденного объекта в БД и в список пользователя (POST).
    """
    if request.method != 'POST':
        return redirect('my_content_search')

    external_id = request.POST.get('external_id', '').strip()
    media_type = request.POST.get('media_type', '').strip()
    comment = request.POST.get('comment', '').strip()

    if not external_id or media_type not in ('movie', 'tv'):
        messages.error(request, _('Некорректные данные объекта.'))
        return redirect('my_content_search')

    # Логирование для отладки
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f'Adding content: external_id={external_id}, media_type={media_type}')

    category = _category_for_media_type(media_type)
    if category is None:
        messages.error(request, _('Категория для этого типа контента не найдена в БД.'))
        return redirect('my_content_search')

    # Если объект уже есть в нашей БД — просто привязываем к пользователю
    content_item = ContentItem.objects.filter(
        external_id=external_id,
        category=category,
    ).first()

    if content_item is None:
        try:
            logger.info(f'Fetching details for external_id={external_id}')
            details = services.get_details(external_id, media_type)
            logger.info(f'Got details: title={details.get("title")}, year={details.get("year")}, persons={len(details.get("persons", []))}')
        except services.KinopoiskError as exc:
            messages.error(request, str(exc))
            return redirect('my_content_search')

        content_item = ContentItem.objects.create(
            category=category,
            title=details['title'],
            original_title=details['original_title'],
            description=details['overview'],
            year=details['year'],
            external_id=details['external_id'],
            external_rating=details['rating'],
            metadata={
                'source': 'kinopoisk',
                'media_type': media_type,
                'poster_url': details['poster_url'],
                'genres': details['genres'],
                'countries': details['countries'],
                'rating': details['rating'],
                'tagline': details['tagline'],
                'ended': details.get('is_ended', False),
                'ended_year': details.get('ended_year'),
            },
        )
        # Привязываем жанры из внешней базы
        genres = _get_or_create_genres(details.get('genres', []))
        content_item.genres.set(genres)

        # Привязываем персон (режиссёры, актёры и т.д.)
        persons_data = details.get('persons', [])
        for p in persons_data:
            p['_content_item'] = content_item
        _get_or_create_persons(persons_data)

        # Для сериалов — подтягиваем сезоны с Кинопоиска
        if media_type == 'tv':
            _import_seasons(content_item, external_id)
    elif not content_item.is_active:
        # Восстанавливаем ранее удалённый объект
        content_item.is_active = True
        content_item.save(update_fields=['is_active', 'updated_at'])

        # Если у сериала ещё нет сезонов — подтягиваем
        if media_type == 'tv' and not content_item.children.exists():
            _import_seasons(content_item, external_id)

    entry, created = UserContentItem.objects.get_or_create(
        user=request.user,
        content_item=content_item,
        defaults={'comment': comment},
    )
    if not created and comment:
        entry.comment = comment
        entry.save(update_fields=['comment', 'updated_at'])

    if created:
        messages.success(request, _('«%(title)s» добавлен в ваши объекты!') % {'title': content_item.title})
    else:
        messages.info(request, _('«%(title)s» уже есть в ваших объектах.') % {'title': content_item.title})
    return redirect('my_content_list')


@login_required
def my_content_edit_comment(request, pk):
    """
    Редактирование комментария к объекту (POST).
    Сохраняет текст и признак публичности.
    """
    entry = get_object_or_404(UserContentItem, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.comment = request.POST.get('comment', '').strip()
        entry.is_public = request.POST.get('is_public') == 'on'
        entry.save(update_fields=['comment', 'is_public', 'updated_at'])
        messages.success(request, _('Комментарий обновлён.'))
    return redirect('my_content_list')


@login_required
def my_content_edit_status(request, pk):
    """
    Изменение статуса просмотра объекта (POST).
    При статусе «Смотрю» или «Посмотрел» сохраняет личную оценку.
    """
    entry = get_object_or_404(UserContentItem, pk=pk, user=request.user)
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        if new_status in dict(UserContentItem.Status.choices):
            entry.status = new_status
            # При статусе «Смотрю»/«Посмотрел» сохраняем личную оценку
            if new_status in (UserContentItem.Status.WATCHING, UserContentItem.Status.COMPLETED):
                personal_rating = request.POST.get('personal_rating', '')
                if personal_rating and personal_rating.isdigit():
                    rating = int(personal_rating)
                    if 1 <= rating <= 10:
                        entry.personal_rating = rating
            entry.save(update_fields=['status', 'personal_rating', 'updated_at'])
            messages.success(request, _('Статус изменён на «%(status)s».') % {'status': entry.get_status_display()})
    return redirect('my_content_list')


@login_required
def my_content_remove(request, pk):
    """
    Удаление объекта из списка пользователя (POST).

    Сам объект помечается is_active=False (мягкое удаление),
    если к нему не привязаны другие пользователи и отзывы.
    """
    entry = get_object_or_404(UserContentItem, pk=pk, user=request.user)
    if request.method == 'POST':
        content_item = entry.content_item
        title = content_item.title
        entry.delete()

        has_other_entries = content_item.user_entries.exists()
        has_reviews = content_item.reviews.exists()
        if not has_other_entries and not has_reviews:
            content_item.is_active = False
            content_item.save(update_fields=['is_active', 'updated_at'])

        messages.info(request, _('«%(title)s» удалён из ваших объектов.') % {'title': title})
    return redirect('my_content_list')
