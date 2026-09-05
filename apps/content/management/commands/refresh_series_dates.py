from django.core.management.base import BaseCommand
from apps.content.models import ContentItem
from apps.content.web_views import _import_seasons


class Command(BaseCommand):
    help = 'Обновить даты выхода серий и сезонов сериалов с Кинопоиска'

    def add_arguments(self, parser):
        parser.add_argument(
            '--external-id',
            dest='external_id',
            default='',
            help='Обновить только конкретный сериал по внешнему ID Кинопоиска',
        )

    def handle(self, *args, **options):
        series = ContentItem.objects.filter(
            category__slug='series',
            parent__isnull=True,
            is_active=True,
        ).exclude(external_id='')

        if options['external_id']:
            series = series.filter(external_id=options['external_id'])

        total = series.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('Нет сериалов для обновления дат.'))
            return

        self.stdout.write(f'Найдено сериалов: {total}')

        updated = 0
        errors = 0
        for item in series:
            self.stdout.write(f'  {item.title} (ID: {item.external_id})...', ending=' ')
            try:
                before = {s.id: s.metadata.get('episodes') for s in item.children.all()}
                _import_seasons(item, item.external_id)
                after = {s.id: s.metadata.get('episodes') for s in item.children.all()}
                if before != after:
                    self.stdout.write(self.style.SUCCESS('даты обновлены'))
                    updated += 1
                else:
                    self.stdout.write('без изменений')
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'ошибка: {exc}'))
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово: {updated} сериалов обновлено, {errors} ошибок.'
        ))
