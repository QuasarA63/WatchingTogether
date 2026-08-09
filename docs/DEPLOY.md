# Инструкция по развертыванию на beget.ru

## Подготовка

1. Создать поддомен `wt.larimaritgroup.ru` в панели beget
2. Включить SSH доступ
3. Создать базу данных MySQL в панели beget

## Установка на сервере

```bash
# Подключиться по SSH
ssh username@wt.larimaritgroup.ru

# Клонировать репозиторий (или загрузить файлы)
cd ~
git clone <repository-url> wt.larimaritgroup.ru
cd wt.larimaritgroup.ru

# Создать виртуальное окружение
python3.10 -m venv venv
source venv/bin/activate

# Установить зависимости
pip install poetry
poetry install --only main,prod

# Создать .env файл
cp .env.example .env
nano .env  # Отредактировать настройки
```

## Настройка .env для production

```env
DEBUG=False
SECRET_KEY=<сгенерировать-сложный-ключ>
ALLOWED_HOSTS=wt.larimaritgroup.ru

DB_ENGINE=mysql
DB_NAME=<имя-базы-данных>
DB_USER=<пользователь-бд>
DB_PASSWORD=<пароль-бд>
DB_HOST=localhost
DB_PORT=3306

JWT_ACCESS_TOKEN_LIFETIME=3600
JWT_REFRESH_TOKEN_LIFETIME=86400
```

## Инициализация базы данных

```bash
# Применить миграции
python manage.py migrate

# Создать суперпользователя
python manage.py createsuperuser

# Собрать статику
python manage.py collectstatic --noinput
```

## Настройка Passenger

1. Отредактировать `.htaccess`:
   - Заменить `username` на реальное имя пользователя
   - Проверить путь к Python в venv

2. Создать файл `tmp/restart.txt` для перезапуска Passenger:
```bash
mkdir -p tmp
touch tmp/restart.txt
```

## Проверка

- Открыть https://wt.larimaritgroup.ru/admin/ — должна открыться админка
- Открыть https://wt.larimaritgroup.ru/api/docs/ — должна открыться Swagger документация
- Проверить API: https://wt.larimaritgroup.ru/api/v1/categories/

## Перезапуск приложения

После изменений в коде:
```bash
touch tmp/restart.txt
```

## Логи

Логи Passenger находятся в панели beget или в `~/logs/`
