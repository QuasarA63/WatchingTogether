from django.db import models
from django.conf import settings
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
        verbose_name='Пользователь'
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Элемент контента'
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,
        blank=True,
        verbose_name='Группа',
        help_text='Группа, в контексте которой оставлен отзыв'
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name='Оценка',
        help_text='Оценка от 1 до 10'
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Заголовок отзыва'
    )
    text = models.TextField(
        verbose_name='Текст отзыва'
    )
    is_spoiler = models.BooleanField(
        default=False,
        verbose_name='Содержит спойлеры'
    )

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
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
        verbose_name='Отзыв'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    text = models.TextField(
        verbose_name='Текст комментария'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name='Родительский комментарий'
    )

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username}: {self.text[:50]}'
