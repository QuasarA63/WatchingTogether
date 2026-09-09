from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    """
    Категория контента (фильмы, сериалы, музыка и т.д.).
    """
    name = models.CharField(
        max_length=100,
        verbose_name=_('Название')
    )
    slug = models.SlugField(
        unique=True,
        verbose_name=_('Slug')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Описание')
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Иконка'),
        help_text=_('CSS класс иконки (например, bi-film)')
    )
    sort = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Порядок сортировки'),
        help_text=_('Чем меньше число, тем выше категория в списках')
    )

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')
        ordering = ['sort', 'name']

    def __str__(self):
        return self.name


class Genre(TimeStampedModel):
    """
    Жанр контента (для фильмов и сериалов) или стиль (для музыки).
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Название')
    )
    slug = models.SlugField(
        unique=True,
        verbose_name=_('Slug')
    )

    class Meta:
        verbose_name = _('Жанр')
        verbose_name_plural = _('Жанры')
        ordering = ['name']

    def __str__(self):
        return self.name


class ContentItem(TimeStampedModel):
    """
    Элемент контента (фильм, сериал, альбом, сезон и т.д.).

    Поддерживает вложенность через self-FK parent:
    например, сезон сериала ссылается на родительский сериал.
    """
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Родительский объект'),
        help_text=_('Например, сериал для сезона')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Категория')
    )
    genres = models.ManyToManyField(
        Genre,
        blank=True,
        related_name='items',
        verbose_name=_('Жанры')
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_('Название')
    )
    original_title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Оригинальное название')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Описание')
    )
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Год выпуска')
    )
    poster = models.ImageField(
        upload_to='posters/',
        blank=True,
        verbose_name=_('Постер')
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Внешний ID'),
        help_text=_('ID из внешних API (Kinopoisk, TMDB и т.д.)')
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Метаданные'),
        help_text=_('Дополнительные данные в формате JSON')
    )
    external_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        verbose_name=_('Внешний рейтинг'),
        help_text=_('Рейтинг из внешних источников (Кинопоиск, TMDB)')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Активен'),
        help_text=_('Неактивные объекты скрыты из каталога (мягкое удаление)')
    )

    class Meta:
        verbose_name = _('Элемент контента')
        verbose_name_plural = _('Элементы контента')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'title']),
            models.Index(fields=['external_id']),
        ]

    def __str__(self):
        return f'{self.title} ({self.year})' if self.year else self.title

    @property
    def average_rating(self):
        """Средняя оценка по отзывам пользователей (целое, 1-10)."""
        reviews = self.reviews.all()
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews))

    @property
    def is_season(self):
        """Является ли объект сезоном (дочерним объектом сериала)."""
        return self.parent_id is not None

    @property
    def is_ended(self):
        """
        Завершён ли сериал (не ожидаются новые сезоны).

        Возвращает True/False по данным Кинопоиска или None,
        если признак ещё не был получен.
        """
        if 'ended' not in self.metadata:
            return None
        return bool(self.metadata.get('ended'))

    @property
    def season_number(self):
        """Номер сезона из метаданных (если это сезон)."""
        if self.is_season:
            return self.metadata.get('season_number')
        return None


class Person(TimeStampedModel):
    """
    Персона: режиссёр, актёр, исполнитель, участник группы и т.д.
    """
    name = models.CharField(
        max_length=255,
        verbose_name=_('Имя')
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Внешний ID'),
        help_text=_('ID из внешних API (Kinopoisk и т.д.)')
    )
    photo = models.URLField(
        blank=True,
        verbose_name=_('Фото'),
        help_text=_('URL фотографии персоны')
    )

    class Meta:
        verbose_name = _('Персона')
        verbose_name_plural = _('Персоны')
        ordering = ['name']

    def __str__(self):
        return self.name


class ContentItemPerson(TimeStampedModel):
    """
    Связь персоны с элементом контента с указанием роли.
    """

    class Role(models.TextChoices):
        DIRECTOR = 'director', _('Режиссёр')
        ACTOR = 'actor', _('Актёр')
        ARTIST = 'artist', _('Исполнитель')
        BAND_MEMBER = 'band_member', _('Участник группы')
        COMPOSER = 'composer', _('Композитор')
        PRODUCER = 'producer', _('Продюсер')
        WRITER = 'writer', _('Сценарист')

    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='persons',
        verbose_name=_('Элемент контента')
    )
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='content_items',
        verbose_name=_('Персона')
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        verbose_name=_('Роль')
    )

    class Meta:
        verbose_name = _('Персона контента')
        verbose_name_plural = _('Персоны контента')
        ordering = ['role', 'person__name']
        constraints = [
            models.UniqueConstraint(
                fields=['content_item', 'person', 'role'],
                name='unique_content_item_person_role'
            )
        ]

    def __str__(self):
        return f'{self.person.name} — {self.get_role_display()} ({self.content_item.title})'


class UserContentItem(TimeStampedModel):
    """
    Личный объект пользователя: привязка элемента контента
    к пользователю с личным комментарием и статусом просмотра.
    """

    class Status(models.TextChoices):
        PLANNED = 'planned', _('В планах')
        WATCHING = 'watching', _('Смотрю')
        ON_HOLD = 'on_hold', _('Отложил')
        COMPLETED = 'completed', _('Посмотрел')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_items',
        verbose_name=_('Пользователь')
    )
    content_item = models.ForeignKey(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='user_entries',
        verbose_name=_('Элемент контента')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name=_('Статус просмотра')
    )
    personal_rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(i, i) for i in range(1, 11)],
        verbose_name=_('Личная оценка'),
        help_text=_('Оценка от 1 до 10')
    )
    comment = models.TextField(
        blank=True,
        verbose_name=_('Комментарий')
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name=_('Публичный'),
        help_text=_('Публичные комментарии видны всем на главной странице')
    )

    class Meta:
        verbose_name = _('Объект пользователя')
        verbose_name_plural = _('Объекты пользователей')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'content_item'],
                name='unique_user_content_item'
            )
        ]

    def __str__(self):
        return f'{self.user} — {self.content_item}'
