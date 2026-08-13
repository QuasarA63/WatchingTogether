from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Group, GroupMembership, GroupInvitation, GroupMessage
from .forms import GroupForm, GroupInviteForm, GroupMessageForm
from apps.content.models import ContentItem, UserContentItem
from apps.notifications.models import Notification

User = get_user_model()


def _get_membership(user, group):
    """Членство пользователя в группе или None."""
    if not user.is_authenticated:
        return None
    return GroupMembership.objects.filter(user=user, group=group).first()


def _notify_invitation(invitation):
    """Создать уведомление о приглашении в группу."""
    Notification.objects.create(
        user=invitation.to_user,
        notification_type='group_invite',
        title=f'Приглашение в группу «{invitation.group.name}»',
        message=(
            f'{invitation.from_user.username} приглашает вас в группу '
            f'«{invitation.group.name}».'
            + (f'\n{invitation.message}' if invitation.message else '')
        ),
        link='/notifications/',
        invitation=invitation,
    )


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
    Страница группы: отзывы, обсуждения объектов, участники.
    """
    group = get_object_or_404(Group, pk=pk)
    membership = _get_membership(request.user, group)
    is_member = membership is not None
    can_invite = is_member and membership.role in ('owner', 'admin')
    tab = request.GET.get('tab', 'reviews')

    context = {
        'group': group,
        'is_member': is_member,
        'can_invite': can_invite,
        'tab': tab,
        'members_count': group.members.count(),
    }

    if tab == 'discussions':
        # Объекты, которые участники группы добавили себе, с количеством комментариев
        discussions = (
            UserContentItem.objects
            .filter(user__member_groups=group)
            .values('content_item')
            .annotate(entries_count=Count('id'))
            .order_by('-entries_count')
        )
        content_items = ContentItem.objects.filter(
            pk__in=[d['content_item'] for d in discussions]
        )
        items_by_pk = {item.pk: item for item in content_items}
        discussion_list = [
            {
                'content_item': items_by_pk[d['content_item']],
                'entries_count': d['entries_count'],
            }
            for d in discussions if d['content_item'] in items_by_pk
        ]
        paginator = Paginator(discussion_list, 10)
        context['discussions_page'] = paginator.get_page(request.GET.get('page'))
    elif tab == 'members':
        memberships = (
            GroupMembership.objects
            .filter(group=group)
            .select_related('user')
            .order_by('joined_at')
        )
        paginator = Paginator(memberships, 20)
        context['memberships_page'] = paginator.get_page(request.GET.get('page'))
    else:
        reviews = group.reviews.select_related('user', 'content_item').order_by('-created_at')
        paginator = Paginator(reviews, 10)
        context['reviews_page'] = paginator.get_page(request.GET.get('page'))

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
@require_POST
def group_join(request, pk):
    """
    Вступление в группу. В приватную — только по приглашению.
    """
    group = get_object_or_404(Group, pk=pk)
    if group.members.filter(pk=request.user.pk).exists():
        return redirect('group_detail', pk=pk)
    if group.is_private:
        messages.warning(request, 'Вступление в приватную группу возможно только по приглашению.')
        return redirect('group_detail', pk=pk)
    GroupMembership.objects.create(user=request.user, group=group, role='member')
    messages.success(request, f'Вы вступили в группу "{group.name}"!')
    return redirect('group_detail', pk=pk)


@login_required
@require_POST
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


@login_required
def group_invite(request, pk):
    """
    Приглашение пользователя в группу (владелец/админ).
    """
    group = get_object_or_404(Group, pk=pk)
    membership = _get_membership(request.user, group)
    if not membership or membership.role not in ('owner', 'admin'):
        messages.error(request, 'Приглашать могут только владелец или администратор группы.')
        return redirect('group_detail', pk=pk)

    # Кандидаты: не участники группы и без активного приглашения
    candidates = User.objects.exclude(
        Q(member_groups=group) |
        Q(received_group_invitations__group=group, received_group_invitations__status='pending')
    ).order_by('username')

    search = request.GET.get('q', '')
    if search:
        candidates = candidates.filter(username__icontains=search)

    if request.method == 'POST':
        form = GroupInviteForm(request.POST, users_queryset=candidates)
        if form.is_valid():
            invitation = GroupInvitation.objects.create(
                group=group,
                from_user=request.user,
                to_user=form.cleaned_data['user'],
                message=form.cleaned_data['message'],
            )
            _notify_invitation(invitation)
            messages.success(
                request,
                f'Приглашение отправлено пользователю {invitation.to_user.username}.'
            )
            return redirect('group_detail', pk=pk)
    else:
        form = GroupInviteForm(users_queryset=candidates)

    return render(request, 'pages/group_invite.html', {
        'group': group,
        'form': form,
        'search': search,
    })


@login_required
@require_POST
def invitation_accept(request, pk):
    """
    Принять приглашение в группу.
    """
    invitation = get_object_or_404(GroupInvitation, pk=pk, to_user=request.user)
    if invitation.status != 'pending':
        messages.info(request, 'Это приглашение уже обработано.')
        return redirect('notification_list')

    invitation.status = 'accepted'
    invitation.save(update_fields=['status', 'updated_at'])
    GroupMembership.objects.get_or_create(
        user=request.user, group=invitation.group, defaults={'role': 'member'}
    )
    Notification.objects.filter(invitation=invitation, user=request.user).update(is_read=True)
    Notification.objects.create(
        user=invitation.from_user,
        notification_type='group_invite_accepted',
        title=f'{request.user.username} принял приглашение',
        message=f'{request.user.username} вступил в группу «{invitation.group.name}».',
        link=f'/groups/{invitation.group.pk}/',
    )
    messages.success(request, f'Вы вступили в группу "{invitation.group.name}"!')
    return redirect('group_detail', pk=invitation.group.pk)


@login_required
@require_POST
def invitation_decline(request, pk):
    """
    Отклонить приглашение в группу.
    """
    invitation = get_object_or_404(GroupInvitation, pk=pk, to_user=request.user)
    if invitation.status != 'pending':
        messages.info(request, 'Это приглашение уже обработано.')
        return redirect('notification_list')

    invitation.status = 'declined'
    invitation.save(update_fields=['status', 'updated_at'])
    Notification.objects.filter(invitation=invitation, user=request.user).update(is_read=True)
    Notification.objects.create(
        user=invitation.from_user,
        notification_type='group_invite_declined',
        title=f'{request.user.username} отклонил приглашение',
        message=f'{request.user.username} отклонил приглашение в группу «{invitation.group.name}».',
        link=f'/groups/{invitation.group.pk}/',
    )
    messages.info(request, f'Вы отклонили приглашение в группу "{invitation.group.name}".')
    return redirect('notification_list')


def group_content_detail(request, pk, content_pk):
    """
    Обсуждение объекта внутри группы: комментарии участников и отзывы.
    """
    group = get_object_or_404(Group, pk=pk)
    content_item = get_object_or_404(ContentItem, pk=content_pk)
    membership = _get_membership(request.user, group)

    entries = (
        UserContentItem.objects
        .filter(content_item=content_item, user__member_groups=group)
        .select_related('user')
        .order_by('created_at')
    )
    reviews = (
        group.reviews
        .filter(content_item=content_item)
        .select_related('user')
        .order_by('created_at')
    )
    already_have = (
        request.user.is_authenticated
        and UserContentItem.objects.filter(user=request.user, content_item=content_item).exists()
    )

    return render(request, 'pages/group_content_detail.html', {
        'group': group,
        'content_item': content_item,
        'entries': entries,
        'reviews': reviews,
        'is_member': membership is not None,
        'already_have': already_have,
    })


@login_required
@require_POST
def group_content_take(request, pk, content_pk):
    """
    «Взять себе»: добавить объект группы в свои объекты.
    """
    group = get_object_or_404(Group, pk=pk)
    content_item = get_object_or_404(ContentItem, pk=content_pk)
    if not _get_membership(request.user, group):
        messages.error(request, 'Брать объекты могут только участники группы.')
        return redirect('group_content_detail', pk=pk, content_pk=content_pk)

    _, created = UserContentItem.objects.get_or_create(
        user=request.user,
        content_item=content_item,
        defaults={'status': UserContentItem.Status.PLANNED},
    )
    if created:
        messages.success(request, f'«{content_item.title}» добавлен в ваши объекты.')
    else:
        messages.info(request, f'«{content_item.title}» уже есть в ваших объектах.')
    return redirect('group_content_detail', pk=pk, content_pk=content_pk)


@login_required
def group_chat(request, pk):
    """
    Страница группового чата (только для участников).
    """
    group = get_object_or_404(Group, pk=pk)
    if not _get_membership(request.user, group):
        messages.warning(request, 'Чат доступен только участникам группы.')
        return redirect('group_detail', pk=pk)

    chat_messages = (
        GroupMessage.objects
        .filter(group=group)
        .select_related('user')
        .order_by('-created_at')[:50]
    )
    chat_messages = list(reversed(chat_messages))

    return render(request, 'pages/group_chat.html', {
        'group': group,
        'chat_messages': chat_messages,
        'form': GroupMessageForm(),
    })


@login_required
def group_chat_messages(request, pk):
    """
    JSON-эндпоинт чата: GET — новые сообщения (?after_id=N), POST — отправить.
    """
    group = get_object_or_404(Group, pk=pk)
    if not _get_membership(request.user, group):
        return JsonResponse({'detail': 'Чат доступен только участникам группы.'}, status=403)

    if request.method == 'POST':
        form = GroupMessageForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'detail': 'Пустое или слишком длинное сообщение.'}, status=400)
        message = GroupMessage.objects.create(
            group=group, user=request.user, text=form.cleaned_data['text']
        )
        return JsonResponse({'message': _serialize_message(message)}, status=201)

    try:
        after_id = int(request.GET.get('after_id', 0))
    except ValueError:
        after_id = 0
    new_messages = (
        GroupMessage.objects
        .filter(group=group, id__gt=after_id)
        .select_related('user')
        .order_by('id')[:100]
    )
    return JsonResponse({'messages': [_serialize_message(m) for m in new_messages]})


def _serialize_message(message):
    """Сериализация сообщения чата в JSON-совместимый dict."""
    avatar_url = message.user.avatar.url if message.user.avatar else ''
    return {
        'id': message.id,
        'username': message.user.username,
        'avatar_url': avatar_url,
        'text': message.text,
        'created_at': message.created_at.strftime('%d.%m.%Y %H:%M'),
    }
