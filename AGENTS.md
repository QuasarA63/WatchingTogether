Это репозиторий web-приложения "Смотрим вместе" ("Watching Together").

Задачи по разработке ставятся через систему 1YES!.

#### О проекте

**"Смотрим вместе" ("Watching Together")** — web-приложение для обмена мнениями в группах о просмотренных фильмах, сериалах, музыке и другом контенте.

**Основные возможности:**
- Создание групп пользователей для совместного обсуждения контента
- Отзывы и оценки (1-10) на фильмы, сериалы, музыку и другие категории
- Комментарии к отзывам
- Гибкая система категорий контента (легко добавлять новые типы)
- REST API для интеграции с мобильными приложениями и SPA

**Технологический стек:**
- Backend: Django 5.2 + Django REST Framework
- Database: SQLite (dev) / MySQL 8.0+ (production)
- Authentication: JWT (djangorestframework-simplejwt)
- API Documentation: drf-spectacular (Swagger)
- Frontend: Django Templates + Bootstrap 5 (MVP), позже SPA
- Package Manager: Poetry

**Хостинг:** beget.ru (виртуальный хостинг), поддомен wt.larimaritgroup.ru

Подробная архитектура описана в `docs/ARCHITECTURE.md`.

#### Деплой на продакшен (beget.ru)

**Требования:**
- SSH доступ к beget.ru (хранится в `.env.production`, не коммитится)
- Python 3.10+ на сервере
- База данных MySQL (опционально, можно SQLite)

**Процедура деплоя:**

1. **Подготовка локального окружения:**
   ```bash
   poetry install
   poetry run python manage.py migrate
   poetry run python manage.py check
   ```

2. **Автоматический деплой через скрипт:**
   ```bash
   python deploy.py
   ```
   Скript создаёт tar.gz архив проекта, загружает на сервер через SSH/SFTP и распаковывает в `~/wt.larimaritgroup.ru/public_html/`.

3. **Настройка сервера (первый раз):**
   ```bash
   python setup_server.py
   ```
   Скрипт выполняет:
   - Создание виртуального окружения `venv`
   - Установку зависимостей (Django, DRF, JWT, и т.д.)
   - Создание `.env` с production настройками
   - Применение миграций
   - Создание суперпользователя (admin/admin123)
   - Создание базовых категорий (Movies, Series, Music)
   - Сбор статики (`collectstatic`)
   - Настройку Passenger (создание `tmp/restart.txt`)

4. **Перезапуск приложения:**
   ```bash
   ssh larimagu@lancelot.beget.com
   cd ~/wt.larimaritgroup.ru/public_html/
   touch tmp/restart.txt
   ```

**Структура на сервере:**
```
~/wt.larimaritgroup.ru/public_html/
├── .env                    # Production настройки (DEBUG=False, SQLite/MySQL)
├── .htaccess              # Конфигурация Passenger
├── passenger_wsgi.py      # WSGI entry point
├── venv/                  # Виртуальное окружение
├── apps/                  # Django приложения
├── config/                # Настройки Django
├── staticfiles/           # Собранная статика
├── tmp/restart.txt        # Файл для перезапуска Passenger
└── manage.py
```

**Проверка работоспособности:**
- API: http://wt.larimaritgroup.ru/api/v1/categories/
- Админка: http://wt.larimaritgroup.ru/admin/ (admin/admin123)
- Swagger: http://wt.larimaritgroup.ru/api/docs/

**Особенности beget.ru:**
- Используется Passenger WSGI для запуска Django
- Защита от ботов: нужна cookie `beget=begetok` для доступа к сайту
- MySQL доступен только с `localhost` (не из Docker контейнера)
- SQLite используется как fallback, если MySQL недоступен

**Обновление кода:**
1. Закоммитить изменения локально
2. Запустить `python deploy.py`
3. Перезапустить Passenger: `touch tmp/restart.txt` на сервере

**Логи:**
- Passenger логи: панель beget.ru
- Django логи: `~/wt.larimaritgroup.ru/public_html/tmp/` (если настроено)



По запросу "1YES! Задача #<номер_задачи>" агент может взаимодействовать с системой задач 1YES! через REST API.

*   Все эндпоинты доступны по адресу: `https://larimaritgroup.ru/api/`
*   ВАЖНО: Используй ТОЛЬКО официально описанные эндпоинты. Не пытайся угадывать URL, использовать `.json`, вставлять логин/пароль в URL. Применяй стандартную схему Token-аутентификации.

#### Аутентификация (1YES!)

1.  Получить токен:
    *   `POST /api-token-auth/`
    *   `Content-Type: application/json`
    *   `{"username": "agent-kilo", "password": "agent-kilo_000"}`
    *   Ответ: `{"token": "abc123..."}` (токен действителен до сброса)
2.  Добавляй заголовок ко всем последующим запросам:
    *   `Authorization: Token <полученный_токен>`

#### Основные Эндпоинты (1YES!)

Базовый путь: `/projects/api/v1/`

##### Проекты

| Метод | URL                             | Описание                      |
| :---- | :------------------------------ | :---------------------------- |
| `GET` | `/projects/api/v1/project/`     | Список активных проектов      |
| `GET` | `/projects/api/v1/project/{id}/`| Проект по ID                  |
| `POST`| `/projects/api/v1/project/`     | Создать проект                |
| `PATCH`| `/projects/api/v1/project/{id}/`| Изменить проект (частично)    |
| `DELETE`| `/projects/api/v1/project/{id}/`| Деактивировать проект         |

##### Задачи

| Метод | URL                         | Описание                    |
| :---- | :-------------------------- | :-------------------------- |
| `GET` | `/projects/api/v1/task/`    | Список активных задач       |
| `GET` | `/projects/api/v1/task/{id}/`| Задача по ID                |
| `POST`| `/projects/api/v1/task/`    | Создать задачу              |
| `PATCH`| `/projects/api/v1/task/{id}/`| Изменить задачу (частично)  |
| `DELETE`| `/projects/api/v1/task/{id}/`| Деактивировать задачу       |

##### Комментарии к задачам

| Метод | URL                               | Описание                     |
| :---- | :-------------------------------- | :--------------------------- |
| `GET` | `/projects/api/v1/taskcomment/`   | Список комментариев          |
| `POST`| `/projects/api/v1/taskcomment/`   | Добавить комментарий         |
| `PATCH`| `/projects/api/v1/taskcomment/{id}/`| Изменить комментарий         |

##### Файлы

| Метод | URL                     | Описание                 |
| :---- | :---------------------- | :----------------------- |
| `GET` | `/projects/api/v1/file/`| Список файлов            |
| `POST`| `/projects/api/v1/file/`| Загрузить файл           |

##### Справочники

| URL                                      | Описание                    |
| :--------------------------------------- | :-------------------------- |
| `/projects/api/v1/project-status/`       | Статусы проектов            |
| `/projects/api/v1/project-type/`         | Типы проектов               |
| `/projects/api/v1/project-structure-type/`| Типы в иерархии проектов    |
| `/projects/api/v1/task-status/`          | Статусы задач               |
| `/projects/api/v1/task-type/`            | Типы задач                  |
| `/projects/api/v1/task-structure-type/`  | Типы в иерархии задач       |
| `/projects/api/v1/currency/`             | Валюты                      |

**Соглашение по полям (1YES!):**

*   При **чтении (GET)**: поля внешних ключей (FK) отображают человекочитаемое имя (`"status": "В работе"`).
*   При **записи (POST/PATCH)**: используй поля с суффиксом `_id` (`"status_id": 3`).

#### Типовые сценарии (1YES!)

1.  **Агент читает свою задачу:**
    `GET /projects/api/v1/task/<id>/`
    `Authorization: Token <токен>`

2.  **Агент меняет процент выполнения:**
    `PATCH /projects/api/v1/task/<id>/`
    `Authorization: Token <токен>`
    `Content-Type: application/json`
    `{"percentage": "75.00"}`

3.  **Агент добавляет комментарий к задаче:**
    `POST /projects/api/v1/taskcomment/`
    `Authorization: Token <токен>`
    `Content-Type: application/json`
    `{"name": "Краткое описание", "description": "Подробности", "time": "0.5", "task_id": <id>}`
    (Поле `author_id` определяется автоматически по токену, если не указано.)

4.  **Агент читает комментарии к задаче:**
    `GET /projects/api/v1/taskcomment/?task_id=<id>`
    `Authorization: Token <токен>`

5.  **Агент отвечает на комментарий (постановку задачи):**
    *   Прочитай комментарии к задаче (`GET .../taskcomment/?task_id=<id>`).
    *   Найди последний комментарий от постановщика (не от агента) — это постановка задачи.
    *   Выполни поставленную задачу.
    *   После завершения добавь комментарий: `POST /projects/api/v1/taskcomment/` с `task_id`, `name="Готово"`, `description=<краткий отчёт>`, `time=<затраченные часы>`.

6.  **Агент узнаёт ID статусов:**
    `GET /projects/api/v1/task-status/`
    `Authorization: Token <токен>`

#### Работа с Задачей из системы 1YES!

*   При начале работы над задачей, установи ей статус "В работе".
*   Прочитай комментарии к задаче, найди последнюю постановку и выполни её.
*   По окончании работы:
    *   Пометь задачу как решённую (установи соответствующий статус и дату закрытия).
    *   Укажи затраченное время и примерную стоимость.
    *   Добавь комментарий с кратким отчётом о проделанной работе.