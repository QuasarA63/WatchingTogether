# Архитектура web-приложения "Смотрим вместе" ("Watching Together")

## Обзор

Приложение для обмена мнениями в группах о просмотренных фильмах, сериалах, музыке и другом контенте. Архитектура позволяет легко добавлять новые категории контента.

## Технологический стек

### Backend
- **Framework:** Django 6.0 / Django REST Framework 3.15+
- **Database:** SQLite (dev) / MySQL 8.0+ (production)
- **Authentication:** JWT (djangorestframework-simplejwt)
- **API Documentation:** drf-spectacular (Swagger/OpenAPI)
- **Templates:** Django Templates (MVP), позже SPA
- **Package Manager:** Poetry

### Frontend (MVP)
- Django Templates + Bootstrap 5
- HTMX для динамических интерфейсов (опционально)

### Хостинг
- **Платформа:** beget.ru (виртуальный хостинг)
- **Домен:** wt.larimaritgroup.ru (поддомен)
- **WSGI:** Passenger (стандарт для beget)

## Структура проекта

```
watching_together/
├── config/                 # Настройки проекта
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py        # Базовые настройки
│   │   ├── development.py # Настройки разработки
│   │   └── production.py  # Настройки продакшена
│   ├── urls.py
│   └── wsgi.py
├── apps/                   # Приложения Django
│   ├── __init__.py
│   ├── core/              # Базовые модели и утилиты
│   │   ├── __init__.py
│   │   ├── models.py      # Abstract базовые модели
│   │   ├── mixins.py
│   │   └── utils.py
│   ├── users/             # Пользователи и профили
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── groups/            # Группы пользователей
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── content/           # Контент (фильмы, сериалы, музыка)
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── reviews/           # Отзывы и оценки
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── notifications/     # Уведомления (колокольчик в navbar)
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── web_views.py
│   │   ├── context_processors.py
│   │   ├── urls.py
│   │   └── admin.py
│   └── api/               # API v1 (агрегация)
│       ├── __init__.py
│       ├── urls.py
│       └── views.py
├── templates/             # Django Templates
│   ├── base.html
│   ├── includes/
│   └── pages/
├── static/                # Статические файлы
│   ├── css/
│   ├── js/
│   └── images/
├── media/                 # Загружаемые файлы
├── pyproject.toml         # Зависимости Poetry
├── .env.example           # Пример переменных окружения
├── .gitignore
├── manage.py
└── README.md
```

## Модели данных

### Core (apps/core/models.py)

```python
class TimeStampedModel(models.Model):
    """Абстрактная модель с временными метками"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
```

### Users (apps/users/models.py)

```python
class User(AbstractUser, TimeStampedModel):
    """Расширенная модель пользователя"""
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    bio = models.TextField(blank=True)
    
class Profile(TimeStampedModel):
    """Профиль пользователя"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Дополнительные поля профиля
```

### Groups (apps/groups/models.py)

```python
class Group(TimeStampedModel):
    """Группа для обсуждения контента"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='group_avatars/', blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_groups')
    members = models.ManyToManyField(User, through='GroupMembership', related_name='member_groups')
    is_private = models.BooleanField(default=False)
    
class GroupMembership(TimeStampedModel):
    """Членство в группе"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=[
        ('owner', 'Владелец'),
        ('admin', 'Администратор'),
        ('member', 'Участник'),
    ], default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

class GroupInvitation(TimeStampedModel):
    """Приглашение пользователя в группу"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='invitations')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_group_invitations')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_group_invitations')
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Ожидает ответа'),
        ('accepted', 'Принято'),
        ('declined', 'Отклонено'),
    ], default='pending')
    message = models.TextField(blank=True)

    class Meta:
        constraints = [
            # Одно активное приглашение на пару (группа, пользователь)
            models.UniqueConstraint(fields=['group', 'to_user'],
                                    condition=models.Q(status='pending'),
                                    name='unique_pending_group_invitation')
        ]

class GroupMessage(TimeStampedModel):
    """Сообщение в групповом чате (AJAX polling, без WebSocket)"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_messages')
    text = models.TextField(max_length=2000)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['group', 'id'])]

class GroupContentComment(TimeStampedModel):
    """Комментарий к обсуждению объекта в группе (форумная вложенность)"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='content_comments')
    content_item = models.ForeignKey(ContentItem, on_delete=models.CASCADE, related_name='group_comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_content_comments')
    text = models.TextField(max_length=2000)
    parent = models.ForeignKey('self', on_delete=models.CASCADE,
                               null=True, blank=True, related_name='replies')

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['group', 'content_item'])]
```

### Notifications (apps/notifications/models.py)

```python
class Notification(TimeStampedModel):
    """Уведомление пользователя (приглашения в группы и др.)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=[
        ('group_invite', 'Приглашение в группу'),
        ('group_invite_accepted', 'Приглашение принято'),
        ('group_invite_declined', 'Приглашение отклонено'),
        ('group_new_message', 'Новое сообщение в группе'),
    ])
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)  # URL перехода по клику
    is_read = models.BooleanField(default=False)
    invitation = models.ForeignKey('groups.GroupInvitation', on_delete=models.CASCADE,
                                   null=True, blank=True, related_name='notifications')

    class Meta:
        indexes = [models.Index(fields=['user', 'is_read'])]
```

### Content (apps/content/models.py)

```python
class Category(TimeStampedModel):
    """Категория контента (фильмы, сериалы, музыка и т.д.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # CSS класс иконки

class Genre(TimeStampedModel):
    """Жанр контента (для фильмов/сериалов) или стиль (для музыки)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

class ContentItem(TimeStampedModel):
    """Элемент контента"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    genres = models.ManyToManyField(Genre, blank=True, related_name='items')
    title = models.CharField(max_length=255)
    original_title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    poster = models.ImageField(upload_to='posters/', blank=True)
    external_id = models.CharField(max_length=100, blank=True)  # ID из внешних API (Kinopoisk, TMDB)
    external_rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)  # Рейтинг Кинопоиска
    metadata = models.JSONField(default=dict, blank=True)  # Дополнительные данные
    is_active = models.BooleanField(default=True)  # Мягкое удаление

    @property
    def average_rating(self):
        """Средняя оценка по отзывам пользователей"""
        ...

    class Meta:
        indexes = [
            models.Index(fields=['category', 'title']),
            models.Index(fields=['external_id']),
        ]

class Person(TimeStampedModel):
    """Персона: режиссёр, актёр, исполнитель, участник группы и т.д."""
    name = models.CharField(max_length=255)
    external_id = models.CharField(max_length=100, blank=True)  # ID из внешних API
    photo = models.URLField(blank=True)  # URL фотографии

class ContentItemPerson(TimeStampedModel):
    """Связь персоны с элементом контента с указанием роли"""

    class Role(models.TextChoices):
        DIRECTOR = 'director', 'Режиссёр'
        ACTOR = 'actor', 'Актёр'
        ARTIST = 'artist', 'Исполнитель'
        BAND_MEMBER = 'band_member', 'Участник группы'
        COMPOSER = 'composer', 'Композитор'
        PRODUCER = 'producer', 'Продюсер'
        WRITER = 'writer', 'Сценарист'

    content_item = models.ForeignKey(ContentItem, on_delete=models.CASCADE, related_name='persons')
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='content_items')
    role = models.CharField(max_length=20, choices=Role.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['content_item', 'person', 'role'], name='unique_content_item_person_role')
        ]

class UserContentItem(TimeStampedModel):
    """Личный объект пользователя с комментарием и статусом просмотра"""

    class Status(models.TextChoices):
        PLANNED = 'planned', 'В планах'
        WATCHING = 'watching', 'Смотрю'
        ON_HOLD = 'on_hold', 'Отложил'
        COMPLETED = 'completed', 'Посмотрел'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_items')
    content_item = models.ForeignKey(ContentItem, on_delete=models.CASCADE, related_name='user_entries')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PLANNED)
    personal_rating = models.PositiveSmallIntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])  # 1-5 звёзд
    comment = models.TextField(blank=True)  # Комментарий
    is_public = models.BooleanField(default=False)  # Публичный комментарий (виден на главной)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'content_item'], name='unique_user_content_item')
        ]
```

### Reviews (apps/reviews/models.py)

```python
class Review(TimeStampedModel):
    """Отзыв на контент"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    content_item = models.ForeignKey(ContentItem, on_delete=models.CASCADE, related_name='reviews')
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 11)])  # 1-10
    title = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    is_spoiler = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'content_item', 'group']
        indexes = [
            models.Index(fields=['content_item', 'group']),
            models.Index(fields=['user', 'created_at']),
        ]

class Comment(TimeStampedModel):
    """Комментарий к отзыву"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
```

## API Endpoints (DRF)

### Аутентификация
```
POST   /api/v1/auth/register/          # Регистрация
POST   /api/v1/auth/login/             # Вход (JWT)
POST   /api/v1/auth/refresh/           # Обновление токена
POST   /api/v1/auth/logout/            # Выход
GET    /api/v1/auth/me/                # Текущий пользователь
```

### Пользователи
```
GET    /api/v1/users/                  # Список пользователей
GET    /api/v1/users/{id}/             # Профиль пользователя
PATCH  /api/v1/users/{id}/             # Обновление профиля
GET    /api/v1/users/{id}/reviews/     # Отзывы пользователя
```

### Группы
```
GET    /api/v1/groups/                 # Список групп
POST   /api/v1/groups/                 # Создание группы
GET    /api/v1/groups/{id}/            # Детали группы
PATCH  /api/v1/groups/{id}/            # Обновление группы
DELETE /api/v1/groups/{id}/            # Удаление группы
POST   /api/v1/groups/{id}/join/       # Вступить в группу (приватная — только по приглашению)
POST   /api/v1/groups/{id}/leave/      # Покинуть группу
GET    /api/v1/groups/{id}/members/    # Участники группы
GET    /api/v1/groups/{id}/reviews/    # Отзывы группы
POST   /api/v1/groups/{id}/invite/     # Пригласить пользователя (owner/admin)
GET    /api/v1/groups/{id}/invitations/  # Приглашения группы (owner/admin, фильтр ?status=)
GET    /api/v1/groups/{id}/messages/   # Сообщения чата (участники, ?after_id= для polling)
POST   /api/v1/groups/{id}/messages/   # Отправить сообщение в чат (участники)
GET    /api/v1/groups/{id}/content/{content_id}/comments/   # Дерево комментариев обсуждения (участники)
POST   /api/v1/groups/{id}/content/{content_id}/comments/   # Комментарий в обсуждение (text, parent опционально)
```

### Приглашения в группы
```
GET    /api/v1/group-invitations/      # Входящие и исходящие приглашения (фильтр ?status=)
GET    /api/v1/group-invitations/{id}/ # Детали приглашения
POST   /api/v1/group-invitations/{id}/accept/   # Принять (только получатель)
POST   /api/v1/group-invitations/{id}/decline/  # Отклонить (только получатель)
```

### Уведомления
```
GET    /api/v1/notifications/          # Уведомления текущего пользователя
GET    /api/v1/notifications/{id}/     # Детали уведомления
POST   /api/v1/notifications/{id}/mark_read/   # Пометить прочитанным
POST   /api/v1/notifications/mark_all_read/    # Пометить все прочитанными
GET    /api/v1/notifications/unread_count/     # Счётчик непрочитанных
```

### Контент
```
GET    /api/v1/categories/             # Список категорий
GET    /api/v1/genres/                 # Список жанров/стилей
GET    /api/v1/content/                # Список контента (фильтры: ?category=slug, ?genre=slug, поиск ?search=)
POST   /api/v1/content/                # Добавление контента
GET    /api/v1/content/{id}/           # Детали контента (включая genres)
PATCH  /api/v1/content/{id}/           # Обновление контента
GET    /api/v1/content/{id}/reviews/   # Отзывы на контент
```

### Личные объекты пользователя
```
GET    /api/v1/my-content/             # Мои объекты (фильтры: ?category=slug, ?genre=slug, ?status=planned|watching|on_hold|completed)
POST   /api/v1/my-content/             # Добавить объект к себе (content_item_id, status, comment)
GET    /api/v1/my-content/{id}/        # Детали личного объекта
PATCH  /api/v1/my-content/{id}/        # Обновить статус/комментарий
DELETE /api/v1/my-content/{id}/        # Удалить из моих (мягкое удаление ContentItem)
```

### Отзывы
```
GET    /api/v1/reviews/                # Список отзывов (фильтры)
POST   /api/v1/reviews/                # Создание отзыва
GET    /api/v1/reviews/{id}/           # Детали отзыва
PATCH  /api/v1/reviews/{id}/           # Обновление отзыва
DELETE /api/v1/reviews/{id}/           # Удаление отзыва
POST   /api/v1/reviews/{id}/comments/  # Добавить комментарий
GET    /api/v1/reviews/{id}/comments/  # Комментарии к отзыву
```

## Django Templates (MVP)

### Основные страницы
- `/` — Главная (последние отзывы, популярный контент)
- `/login/` — Вход
- `/register/` — Регистрация
- `/profile/` — Профиль пользователя
- `/groups/` — Список групп
- `/groups/{id}/` — Страница группы (вкладки: Отзывы / Обсуждения / Участники)
- `/groups/{id}/invite/` — Приглашение пользователя в группу (owner/admin)
- `/groups/{id}/chat/` — Групповой чат (AJAX polling каждые 3 сек, только участники; справа список участников)
- `/groups/{id}/content/{content_id}/` — Обсуждение объекта в группе (сводка по участникам, форумные вложенные комментарии, «Взять себе»)
- `/notifications/` — Уведомления (колокольчик в navbar со счётчиком непрочитанных)
- `/content/` — Каталог контента (фильтры по категории и жанру, рейтинги)
- `/content/{id}/` — Страница контента с отзывами (жанры, рейтинги Кинопоиска и пользователей)
- `/content/my/` — Мои объекты (фильтры по категории, жанру, статусу; карточки с постером слева)
- `/content/my/search/` — Поиск и добавление объектов из Кинопоиска
- `/reviews/{id}/` — Детальный отзыв с комментариями

## Развертывание на beget.ru

### Требования
- Python 3.10+
- MySQL 8.0+
- Passenger WSGI

### Настройка
1. Создать поддомен `wt.larimaritgroup.ru` в панели beget
2. Создать базу данных MySQL
3. Настроить `passenger_wsgi.py`
4. Настроить `.htaccess` для статики
5. Установить зависимости через SSH или панель

### Переменные окружения (.env)
```
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=mysql://user:password@localhost/dbname
ALLOWED_HOSTS=wt.larimaritgroup.ru
```

## Расширяемость

### Добавление новой категории контента
1. Добавить запись в `Category` через админку
2. Настроить иконку и описание
3. Готово — категория доступна в API и интерфейсе

### Интеграция внешних API
- **Кинопоиск API** — основной провайдер для фильмов и сериалов (реализовано в `apps/content/services.py`)
  - Поиск: `services.search(query, category_slug)` — фильмы и сериалы с русскими названиями и описаниями
  - Детали: `services.get_details(external_id, media_type)` — жанры, страны, постер, рейтинг
  - Токен задаётся в `.env` как `KINOPOISK_API_KEY` (получить: @kinopoiskdev_bot в Telegram)
  - Примечание: TMDB не используется — домен themoviedb.org заблокирован на уровне DNS (в т.ч. на beget.ru)
- **Spotify API** — для музыки
- **Google Books API** — для книг

### Будущие возможности
- Уведомления по email и push (внутренние уведомления реализованы)
- Рекомендательная система
- Импорт оценок из других сервисов
- Мобильное приложение (React Native / Flutter)
- SPA frontend (React / Vue)

## Безопасность

- JWT токены с коротким временем жизни
- CORS настройки для API
- Rate limiting для API endpoints
- Валидация всех входных данных
- Защита от XSS в шаблонах
- HTTPS обязательно

## Производительность

- Индексы на часто запрашиваемые поля
- Пагинация для всех списков
- Кэширование (Redis при необходимости)
- Оптимизация запросов (select_related, prefetch_related)
- CDN для статики (опционально)
