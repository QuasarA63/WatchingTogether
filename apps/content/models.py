from django.conf import settings
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


class Genre(TimeStampedModel):
    """
    Жанр контента (для фильмов и сериалов) или стиль (для музыки).
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        unique=True,
        verbose_name='Slug'
    )

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'
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
    genres = models.ManyToManyField(
        Genre,
        blank=True,
        related_name='items',
        verbose_name='Жанры'
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
    external_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name='Внешний рейтинг',
        help_text='Рейтинг из внешних источников (Кинопоиск, TMDB)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен',
        help_text='Неактивные объекты скрыты из каталога (мягкое удаление)'
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

    @property
    def average_rating(self):
        """Средняя оценка по отзывам пользователей."""
        reviews = self.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 1)


class UserContentItem(TimeStampedModel):
    """
    Личный объект пользователя: привязка элемента контента
    к пользователю с личным комментарием и статусом просмотра.
    """

    class Status(models.TextChoices):
        PLANNED = 'planned', 'В планах'
        WATCHING = 'watching', 'Смотрю'
        ON_HOLD = 'on_hold', 'Отложил'
        COMPLETED = 'completed', 'Посмотрел'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_items',
        verbose_name='Пользователь'
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='user_entries',
        verbose_name='Элемент контента'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name='Статус просмотра'
    )
    personal_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(i, i) for i in range(1, 6)],
        verbose_name='Личная оценка',
        help_text='Оценка от 1 до 5 звёзд'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Личный комментарий'
    )

    class Meta:
        verbose_name = 'Объект пользователя'
        verbose_name_plural = 'Объекты пользователей'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_item'],
                name='unique_user_content_item'
            )
        ]

    def __str__(self):
        return f'{self.user} — {self.content_item}'
