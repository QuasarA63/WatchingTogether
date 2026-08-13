from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Сериализатор уведомления.
    """
    invitation_status = serializers.CharField(
        source='invitation.status', read_only=True, default=None
    )

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'link',
            'is_read', 'invitation', 'invitation_status', 'created_at'
        ]
        read_only_fields = fields
