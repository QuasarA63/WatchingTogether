# Data-миграция: перенос жанров из ContentItem.metadata['genres'] в M2M-связь.

from django.db import migrations
from django.utils.text import slugify


def migrate_genres_from_metadata(apps, schema_editor):
    """Перенести жанры из JSON-метаданных в связь M2M с моделью Genre."""
    ContentItem = apps.get_model('content', 'ContentItem')
    Genre = apps.get_model('content', 'Genre')

    for item in ContentItem.objects.all():
        genre_names = (item.metadata or {}).get('genres') or []
        for name in genre_names:
            name = name.strip()
            if not name:
                continue
            # Сначала ищем по имени (уникальное поле)
            genre = Genre.objects.filter(name=name).first()
            if genre is None:
                slug = slugify(name)
                if not slug:
                    # Для названий без латиницы/кириллицы slugify может дать пустую строку
                    slug = f'genre-{Genre.objects.count() + 1}'
                # Проверяем уникальность slug
                base_slug = slug
                counter = 1
                while Genre.objects.filter(slug=slug).exists():
                    slug = f'{base_slug}-{counter}'
                    counter += 1
                genre = Genre.objects.create(name=name, slug=slug)
            item.genres.add(genre)


def reverse_migration(apps, schema_editor):
    """Откат: очистить M2M-связи (метаданные не трогаем)."""
    ContentItem = apps.get_model('content', 'ContentItem')
    for item in ContentItem.objects.all():
        item.genres.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0003_genre_contentitem_genres"),
    ]

    operations = [
        migrations.RunPython(migrate_genres_from_metadata, reverse_migration),
    ]
