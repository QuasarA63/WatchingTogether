# Архитектура web-приложения "Смотрим вместе" ("Watching Together")

## Обзор

Приложение для обмена мнениями в группах о просмотренных фильмах, сериалах, музыке и другом контенте. Архитектура позволяет легко добавлять новые категории контента.

## Технологический стек

### Backend
- **Framework:** Django 4.2+ / Django REST Framework 3.14+
- **Database:** MySQL 8.0+
- **Authentication:** JWT (djangorestframework-simplejwt)
- **API Documentation:** drf-spectacular (Swagger/OpenAPI)
- **Templates:** Django Templates (MVP), позже SPA

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
├── requirements/          # Зависимости
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
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
```

### Content (apps/content/models.py)

```python
class Category(TimeStampedModel):
    """Категория контента (фильмы, сериалы, музыка и т.д.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)  # CSS класс иконки
    
class ContentItem(TimeStampedModel):
    """Элемент контента"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=255)
    original_title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    poster = models.ImageField(upload_to='posters/', blank=True)
    external_id = models.CharField(max_length=100, blank=True)  # ID из внешних API (Kinopoisk, TMDB)
    metadata = models.JSONField(default=dict, blank=True)  # Дополнительные данные
    
    class Meta:
        indexes = [
            models.Index(fields=['category', 'title']),
            models.Index(fields=['external_id']),
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
POST   /api/v1/groups/{id}/join/       # Вступить в группу
POST   /api/v1/groups/{id}/leave/      # Покинуть группу
GET    /api/v1/groups/{id}/members/    # Участники группы
GET    /api/v1/groups/{id}/reviews/    # Отзывы группы
```

### Контент
```
GET    /api/v1/categories/             # Список категорий
GET    /api/v1/content/                # Список контента (фильтры по категории, поиск)
POST   /api/v1/content/                # Добавление контента
GET    /api/v1/content/{id}/           # Детали контента
PATCH  /api/v1/content/{id}/           # Обновление контента
GET    /api/v1/content/{id}/reviews/   # Отзывы на контент
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
- `/groups/{id}/` — Страница группы
- `/content/` — Каталог контента
- `/content/{id}/` — Страница контента с отзывами
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
- **Kinopoisk API** — для фильмов и сериалов
- **TMDB API** — альтернатива для фильмов
- **Spotify API** — для музыки
- **Google Books API** — для книг

### Будущие возможности
- Уведомления (email, push)
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
