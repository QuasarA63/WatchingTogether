from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    Уведомление пользователя (приглашения в группы и др.).
    """
    TYPE_CHOICES = [
        ('group_invite', _('Приглашение в группу')),
        ('group_invite_accepted', _('Приглашение принято')),
        ('group_invite_declined', _('Приглашение отклонено')),
        ('group_new_message', _('Новое сообщение в группе')),
        ('new_episode', _('Новая серия')),
        ('new_season', _('Новый сезон')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Пользователь')
    )
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        verbose_name=_('Тип уведомления')
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_('Заголовок')
    )
    message = models.TextField(
        blank=True,
        verbose_name=_('Текст')
    )
    link = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Ссылка'),
        help_text=_('URL, куда ведёт клик по уведомлению')
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Прочитано')
    )
    invitation = models.ForeignKey(
        'groups.GroupInvitation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_('Приглашение')
    )

    class Meta:
        verbose_name = _('Уведомление')
        verbose_name_plural = _('Уведомления')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f'{self.user.username}: {self.title}'
