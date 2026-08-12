from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from apps.reviews.models import Review
from apps.content.models import ContentItem, UserContentItem
from apps.groups.models import Group
from apps.users.forms import RegisterForm, AccountForm


def home(request):
    """
    Главная страница: последние отзывы, популярный контент
    и объекты с публичными комментариями.
    """
    latest_reviews = Review.objects.select_related(
        'user', 'content_item', 'group'
    ).order_by('-created_at')[:10]

    popular_content = ContentItem.objects.prefetch_related(
        'reviews'
    ).order_by('-created_at')[:8]

    # Объекты с публичными комментариями (для всех, включая неавторизованных)
    public_entries = UserContentItem.objects.filter(
        is_public=True,
        comment__gt='',
        content_item__is_active=True,
    ).select_related('user', 'content_item', 'content_item__category').order_by('-updated_at')[:10]

    context = {
        'latest_reviews': latest_reviews,
        'popular_content': popular_content,
        'public_entries': public_entries,
    }
    return render(request, 'pages/home.html', context)


def register_view(request):
    """
    Страница регистрации.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}! Регистрация прошла успешно.')
            return redirect('home')
    else:
        form = RegisterForm()

    return render(request, 'pages/register.html', {'form': form})


def logout_view(request):
    """
    Выход из системы (GET и POST).
    """
    logout(request)
    messages.info(request, 'Вы вышли из системы.')
    return redirect('home')


@login_required
def profile_view(request):
    """
    Страница профиля текущего пользователя.
    """
    user_reviews = Review.objects.filter(
        user=request.user
    ).select_related('content_item', 'group').order_by('-created_at')

    paginator = Paginator(user_reviews, 10)
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)

    user_groups = request.user.member_groups.all()

    context = {
        'reviews_page': reviews_page,
        'user_groups': user_groups,
    }
    return render(request, 'pages/profile.html', context)


@login_required
def profile_edit_view(request):
    """
    Редактирование профиля пользователя (логин, email, пароль, личные данные, аватар).
    """
    if request.method == 'POST':
        form = AccountForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            user = form.save()
            # Если пароль был изменён, обновляем сессию, чтобы не разлогинило
            if form.cleaned_data.get('new_password'):
                update_session_auth_hash(request, user)
                messages.success(request, 'Пароль успешно изменён.')
            else:
                messages.success(request, 'Профиль обновлён.')
            return redirect('profile')
    else:
        form = AccountForm(instance=request.user)

    return render(request, 'pages/profile_edit.html', {'form': form})
