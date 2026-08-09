from django.db import models
from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    """
    Категория контента (фильмы, сериалы, музыка и т.д.).
    """
    name = models.CharField(
        max_length=100,
        verbose_name='Название'
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='Slug'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Иконка',
        help_text='CSS класс иконки (например, bi-film)'
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class ContentItem(TimeStampedModel):
    """
    Элемент контента (фильм, сериал, альбом и т.д.).
    """
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Категория'
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Название'
    )
    original_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Оригинальное название'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Год выпуска'
    )
    poster = models.ImageField(
        upload_to='posters/',
        blank=True,
        verbose_name='Постер'
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Внешний ID',
        help_text='ID из внешних API (Kinopoisk, TMDB и т.д.)'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Метаданные',
        help_text='Дополнительные данные в формате JSON'
    )

    class Meta:
        verbose_name = 'Элемент контента'
        verbose_name_plural = 'Элементы контента'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'title']),
            models.Index(fields=['external_id']),
        ]

    def __str__(self):
        return f'{self.title} ({self.year})' if self.year else self.title
