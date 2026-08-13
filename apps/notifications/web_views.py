from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notification_list(request):
    """
    Список уведомлений текущего пользователя.
    """
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('invitation', 'invitation__group', 'invitation__from_user')

    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    notifications_page = paginator.get_page(page_number)

    return render(request, 'pages/notification_list.html', {
        'notifications_page': notifications_page,
    })


@login_required
def notification_open(request, pk):
    """
    Открыть уведомление: пометить прочитанным и перейти по ссылке.
    """
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read', 'updated_at'])
    if notification.link:
        return redirect(notification.link)
    return redirect('notification_list')


@login_required
@require_POST
def notification_mark_all_read(request):
    """
    Пометить все уведомления прочитанными.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notification_list')
