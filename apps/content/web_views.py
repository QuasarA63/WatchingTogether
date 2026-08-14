from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.utils.text import slugify
from .models import Category, Genre, ContentItem, UserContentItem, Person, ContentItemPerson
from . import services


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

    if category_slug:
        items = items.filter(category__slug=category_slug)
    if genre_slug:
        items = items.filter(genres__slug=genre_slug)
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

    context = {
        'item': item,
        'reviews_page': reviews_page,
        'user_review': user_review,
        'persons_by_role': persons_by_role,
        'seasons': seasons,
        'user_season_reviews': user_season_reviews,
    }
    return render(request, 'pages/content_detail.html', context)


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

    entries = entries.order_by('-created_at').distinct()

    paginator = Paginator(entries, 12)
    page_number = request.GET.get('page')
    entries_page = paginator.get_page(page_number)

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
        'search_configured': services.is_configured(),
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


def _import_seasons(series_item, external_id):
    """
    Импортировать сезоны сериала с Кинопоиска.

    Создаёт дочерние ContentItem для каждого сезона.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        seasons = services.get_seasons(external_id)
    except services.KinopoiskError as exc:
        logger.warning('Не удалось получить сезоны для %s: %s', external_id, exc)
        return

    for season_data in seasons:
        season_num = season_data['number']
        season_title = f'{series_item.title}. {season_data["name"]}'

        # Проверяем, не создан ли уже этот сезон
        existing = series_item.children.filter(
            metadata__season_number=season_num,
        ).first()
        if existing:
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
        messages.error(request, 'Некорректные данные объекта.')
        return redirect('my_content_search')

    # Логирование для отладки
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f'Adding content: external_id={external_id}, media_type={media_type}')

    category = _category_for_media_type(media_type)
    if category is None:
        messages.error(request, 'Категория для этого типа контента не найдена в БД.')
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
        messages.success(request, f'«{content_item.title}» добавлен в ваши объекты!')
    else:
        messages.info(request, f'«{content_item.title}» уже есть в ваших объектах.')
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
        messages.success(request, 'Комментарий обновлён.')
    return redirect('my_content_list')


@login_required
def my_content_edit_status(request, pk):
    """
    Изменение статуса просмотра объекта (POST).
    При статусе «Посмотрел» сохраняет личную оценку.
    """
    entry = get_object_or_404(UserContentItem, pk=pk, user=request.user)
    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        if new_status in dict(UserContentItem.Status.choices):
            entry.status = new_status
            # При статусе «Посмотрел» сохраняем личную оценку
            if new_status == UserContentItem.Status.COMPLETED:
                personal_rating = request.POST.get('personal_rating', '')
                if personal_rating and personal_rating.isdigit():
                    rating = int(personal_rating)
                    if 1 <= rating <= 5:
                        entry.personal_rating = rating
            entry.save(update_fields=['status', 'personal_rating', 'updated_at'])
            messages.success(request, f'Статус изменён на «{entry.get_status_display()}».')
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

        messages.info(request, f'«{title}» удалён из ваших объектов.')
    return redirect('my_content_list')
