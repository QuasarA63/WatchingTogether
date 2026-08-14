from django.core.management.base import BaseCommand
from apps.content.models import ContentItem
from apps.content.web_views import _import_seasons


class Command(BaseCommand):
    help = 'Импортировать сезоны для существующих сериалов, у которых их ещё нет'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Переимпортировать сезоны даже для сериалов, у которых они уже есть',
        )

    def handle(self, *args, **options):
        # Находим все сериалы (категория series, есть external_id, верхний уровень)
        series = ContentItem.objects.filter(
            category__slug='series',
            parent__isnull=True,
            is_active=True,
        ).exclude(external_id='')

        if not options['all']:
            # Только те, у которых ещё нет дочерних объектов
            series = series.filter(children__isnull=True).distinct()

        total = series.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('Нет сериалов для импорта сезонов.'))
            return

        self.stdout.write(f'Найдено сериалов: {total}')

        imported = 0
        errors = 0
        for item in series:
            self.stdout.write(f'  {item.title} (ID: {item.external_id})...', ending=' ')
            try:
                before = item.children.count()
                _import_seasons(item, item.external_id)
                after = item.children.count()
                new_count = after - before
                if new_count > 0:
                    self.stdout.write(self.style.SUCCESS(f'+{new_count} сезонов'))
                    imported += 1
                else:
                    self.stdout.write(self.style.WARNING('нет новых сезонов'))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'ошибка: {exc}'))
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово: {imported} сериалов обновлено, {errors} ошибок.'
        ))
