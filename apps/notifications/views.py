from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet уведомлений текущего пользователя.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Пометить уведомление прочитанным."""
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read', 'updated_at'])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Пометить все уведомления прочитанными."""
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'marked': updated})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Количество непрочитанных уведомлений."""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})
