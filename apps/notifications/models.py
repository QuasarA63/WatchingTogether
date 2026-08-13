from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    Уведомление пользователя (приглашения в группы и др.).
    """
    TYPE_CHOICES = [
        ('group_invite', 'Приглашение в группу'),
        ('group_invite_accepted', 'Приглашение принято'),
        ('group_invite_declined', 'Приглашение отклонено'),
        ('group_new_message', 'Новое сообщение в группе'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Пользователь'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name='Тип уведомления'
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Заголовок'
    )
    message = models.TextField(
        blank=True,
        verbose_name='Текст'
    )
    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Ссылка',
        help_text='URL, куда ведёт клик по уведомлению'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано'
    )
    invitation = models.ForeignKey(
        'groups.GroupInvitation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='Приглашение'
    )

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.title}'
