# Смотрим вместе (Watching Together)

Web-приложение для обмена мнениями в группах о просмотренных фильмах, сериалах, музыке и другом контенте.

## Технологии

- **Backend:** Django 4.2+ / Django REST Framework
- **Database:** MySQL 8.0+
- **Authentication:** JWT (djangorestframework-simplejwt)
- **API Documentation:** drf-spectacular (Swagger)
- **Frontend:** Django Templates + Bootstrap 5 (MVP)

## Установка и запуск

### Требования

- Python 3.10+
- MySQL 8.0+
- Virtual environment

### Установка

1. Клонировать репозиторий:
```bash
git clone <repository-url>
cd WatchingTogether
```

2. Создать виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установить зависимости:
```bash
pip install -r requirements/development.txt
```

4. Создать файл `.env` на основе `.env.example`:
```bash
cp .env.example .env
```

5. Настроить базу данных в `.env`:

**Для локальной разработки (SQLite, по умолчанию):**
```
DB_ENGINE=sqlite
```
База данных создастся автоматически в файле `db.sqlite3`.

**Для MySQL (production):**
```
DB_ENGINE=mysql
DB_NAME=watching_together
DB_USER=your_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306
```

6. Применить миграции:
```bash
python manage.py migrate
```

7. Создать суперпользователя:
```bash
python manage.py createsuperuser
```

8. Запустить сервер разработки:
```bash
python manage.py runserver
```

Приложение будет доступно по адресу: http://127.0.0.1:8000/

## Структура проекта

```
watching_together/
├── config/              # Настройки проекта
├── apps/                # Приложения Django
│   ├── core/           # Базовые модели и утилиты
│   ├── users/          # Пользователи
│   ├── groups/         # Группы
│   ├── content/        # Контент (фильмы, сериалы, музыка)
│   ├── reviews/        # Отзывы и комментарии
│   └── api/            # REST API
├── templates/          # Django Templates
├── static/             # Статические файлы
├── media/              # Загружаемые файлы
└── requirements/       # Зависимости
```

## API Documentation

После запуска сервера документация API доступна по адресам:

- Swagger UI: http://127.0.0.1:8000/api/docs/
- OpenAPI Schema: http://127.0.0.1:8000/api/schema/

## Разработка

### Создание миграций

```bash
python manage.py makemigrations
python manage.py migrate
```

### Запуск тестов

```bash
pytest
```

### Форматирование кода

```bash
black .
isort .
flake8
```

## Развертывание на beget.ru

См. документацию в `docs/ARCHITECTURE.md`

## Лицензия

Проприетарная
