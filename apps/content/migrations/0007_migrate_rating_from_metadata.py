# Data-миграция: перенос рейтинга из ContentItem.metadata['rating'] в external_rating.

from django.db import migrations


def migrate_rating_from_metadata(apps, schema_editor):
    """Перенести рейтинг из JSON-метаданных в поле external_rating."""
    ContentItem = apps.get_model('content', 'ContentItem')

    for item in ContentItem.objects.all():
        rating = (item.metadata or {}).get('rating')
        if rating is not None:
            try:
                item.external_rating = float(rating)
                item.save(update_fields=['external_rating'])
            except (ValueError, TypeError):
                pass


def reverse_migration(apps, schema_editor):
    """Откат: очистить external_rating (метаданные не трогаем)."""
    ContentItem = apps.get_model('content', 'ContentItem')
    ContentItem.objects.update(external_rating=None)


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0006_contentitem_external_rating"),
    ]

    operations = [
        migrations.RunPython(migrate_rating_from_metadata, reverse_migration),
    ]
