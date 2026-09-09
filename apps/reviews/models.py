from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.content.models import ContentItem
from apps.groups.models import Group


class Review(TimeStampedModel):
    """
    Отзыв на контент.
    """
    RATING_CHOICES = [(i, str(i)) for i in range(1, 11)]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Пользователь')
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Элемент контента')
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True,
        verbose_name=_('Группа'),
        help_text=_('Группа, в контексте которой оставлен отзыв')
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name=_('Оценка'),
        help_text=_('Оценка от 1 до 10')
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Заголовок отзыва')
    )
    text = models.TextField(
        blank=True,
        verbose_name=_('Текст отзыва')
    )
    is_spoiler = models.BooleanField(
        default=False,
        verbose_name=_('Содержит спойлеры')
    )

    class Meta:
        verbose_name = _('Отзыв')
        verbose_name_plural = _('Отзывы')
        ordering = ['-created_at']
        unique_together = ['user', 'content_item', 'group']
        indexes = [
            models.Index(fields=['content_item', 'group']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f'{self.user.username} о {self.content_item.title} ({self.rating}/10)'


class Comment(TimeStampedModel):
    """
    Комментарий к отзыву.
    """
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Отзыв')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь')
    )
    text = models.TextField(
        verbose_name=_('Текст комментария')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('Родительский комментарий')
    )

    class Meta:
        verbose_name = _('Комментарий')
        verbose_name_plural = _('Комментарии')
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username}: {self.text[:50]}'
