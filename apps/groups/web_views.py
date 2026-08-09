from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Group, GroupMembership
from .forms import GroupForm


def group_list(request):
    """
    Список всех публичных групп.
    """
    groups = Group.objects.filter(is_private=False).prefetch_related('members')
    search = request.GET.get('q', '')
    if search:
        groups = groups.filter(name__icontains=search)

    paginator = Paginator(groups, 12)
    page_number = request.GET.get('page')
    groups_page = paginator.get_page(page_number)

    context = {
        'groups_page': groups_page,
        'search': search,
    }
    return render(request, 'pages/group_list.html', context)


def group_detail(request, pk):
    """
    Страница группы с отзывами участников.
    """
    group = get_object_or_404(Group, pk=pk)
    is_member = request.user.is_authenticated and group.members.filter(pk=request.user.pk).exists()
    reviews = group.reviews.select_related('user', 'content_item').order_by('-created_at')

    paginator = Paginator(reviews, 10)
    page_number = request.GET.get('page')
    reviews_page = paginator.get_page(page_number)

    context = {
        'group': group,
        'is_member': is_member,
        'reviews_page': reviews_page,
        'members_count': group.members.count(),
    }
    return render(request, 'pages/group_detail.html', context)


@login_required
def group_create(request):
    """
    Создание новой группы.
    """
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.owner = request.user
            group.save()
            GroupMembership.objects.create(
                user=request.user,
                group=group,
                role='owner'
            )
            messages.success(request, f'Группа "{group.name}" создана!')
            return redirect('group_detail', pk=group.pk)
    else:
        form = GroupForm()

    return render(request, 'pages/group_form.html', {'form': form, 'title': 'Создание группы'})


@login_required
def group_join(request, pk):
    """
    Вступление в группу.
    """
    group = get_object_or_404(Group, pk=pk)
    if not group.members.filter(pk=request.user.pk).exists():
        GroupMembership.objects.create(user=request.user, group=group, role='member')
        messages.success(request, f'Вы вступили в группу "{group.name}"!')
    return redirect('group_detail', pk=pk)


@login_required
def group_leave(request, pk):
    """
    Выход из группы.
    """
    group = get_object_or_404(Group, pk=pk)
    membership = GroupMembership.objects.filter(user=request.user, group=group).first()
    if membership and membership.role != 'owner':
        membership.delete()
        messages.info(request, f'Вы покинули группу "{group.name}".')
    elif membership and membership.role == 'owner':
        messages.warning(request, 'Владелец не может покинуть группу.')
    return redirect('group_detail', pk=pk)
