from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from .models import Category, ContentItem, UserContentItem
from . import services


def content_list(request):
    """
    Каталог контента с фильтрами по категории и поиском.
    """
    items = ContentItem.objects.filter(is_active=True).select_related('category').annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    )

    category_slug = request.GET.get('category', '')
    search = request.GET.get('q', '')

    if category_slug:
        items = items.filter(category__slug=category_slug)
    if search:
        items = items.filter(title__icontains=search)

    items = items.order_by('-created_at')

    paginator = Paginator(items, 12)
    page_number = request.GET.get('page')
    items_page = paginator.get_page(page_number)

    categories = Category.objects.all()

    context = {
        'items_page': items_page,
        'categories': categories,
        'current_category': category_slug,
        'search': search,
    }
    return render(request, 'pages/content_list.html', context)


def content_detail(request, pk):
    """
    Страница контента с отзывами.
    """
    item = get_object_or_404(
        ContentItem.objects.select_related('category').annotate(
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

    context = {
        'item': item,
        'reviews_page': reviews_page,
        'user_review': user_review,
    }
    return render(request, 'pages/content_detail.html', context)


@login_required
def my_content_list(request):
    """
    Вкладка «Мои объекты»: список объектов пользователя
    с фильтром по категории и личными комментариями.
    """
    entries = UserContentItem.objects.filter(
        user=request.user,
        content_item__is_active=True,
    ).select_related('content_item', 'content_item__category')

    category_slug = request.GET.get('category', '')
    if category_slug:
        entries = entries.filter(content_item__category__slug=category_slug)

    entries = entries.order_by('-created_at')

    paginator = Paginator(entries, 12)
    page_number = request.GET.get('page')
    entries_page = paginator.get_page(page_number)

    categories = Category.objects.all()

    context = {
        'entries_page': entries_page,
        'categories': categories,
        'current_category': category_slug,
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
            details = services.get_details(external_id, media_type)
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
    elif not content_item.is_active:
        # Восстанавливаем ранее удалённый объект
        content_item.is_active = True
        content_item.save(update_fields=['is_active', 'updated_at'])

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
    Редактирование личного комментария к объекту (POST).
    """
    entry = get_object_or_404(UserContentItem, pk=pk, user=request.user)
    if request.method == 'POST':
        entry.comment = request.POST.get('comment', '').strip()
        entry.save(update_fields=['comment', 'updated_at'])
        messages.success(request, 'Комментарий обновлён.')
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
