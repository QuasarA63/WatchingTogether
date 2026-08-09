from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from .models import Category, ContentItem


def content_list(request):
    """
    Каталог контента с фильтрами по категории и поиском.
    """
    items = ContentItem.objects.select_related('category').annotate(
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
