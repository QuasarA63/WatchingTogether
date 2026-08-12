"""
Management-команда для догрузки персон к существующим объектам контента.

Загружает персон (режиссёров, актёров и т.д.) из Кинопоиск API
для объектов, у которых они ещё не загружены.
"""

from django.core.management.base import BaseCommand
from apps.content.models import ContentItem, Person, ContentItemPerson
from apps.content import services


class Command(BaseCommand):
    help = 'Догрузка персон из Кинопоиск API для существующих объектов контента'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перезагрузить персоны даже для объектов, у которых они уже есть',
        )

    def handle(self, *args, **options):
        force = options['force']

        # Проверяем, настроен ли API-ключ
        if not services.is_configured():
            self.stderr.write(self.style.ERROR(
                'Кинопоиск API не настроен: задайте KINOPOISK_API_KEY в .env'
            ))
            return

        # Выбираем объекты без персон (или все, если --force)
        items = ContentItem.objects.filter(is_active=True, external_id__gt='')
        if not force:
            items = items.exclude(persons__isnull=False).distinct()

        total = items.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Нет объектов для обработки.'))
            return

        self.stdout.write(f'Найдено объектов для обработки: {total}')

        updated = 0
        errors = 0

        for item in items:
            try:
                self.stdout.write(f'  Загрузка: {item.title} (external_id={item.external_id})... ', ending='')

                details = services.get_details(item.external_id)
                persons_data = details.get('persons', [])

                if not persons_data:
                    self.stdout.write(self.style.WARNING('нет персон'))
                    continue

                # Удаляем старые связи, если force
                if force:
                    item.persons.all().delete()

                # Создаём персоны и связи
                created_count = 0
                for p_data in persons_data:
                    name = p_data.get('name', '').strip()
                    if not name:
                        continue

                    # Ищем или создаём персону
                    person = None
                    ext_id = p_data.get('external_id', '')
                    if ext_id:
                        person = Person.objects.filter(external_id=ext_id).first()
                    if person is None:
                        person = Person.objects.filter(name=name).first()
                    if person is None:
                        person = Person.objects.create(
                            name=name,
                            external_id=ext_id,
                            photo=p_data.get('photo', ''),
                        )

                    role = p_data.get('role', '')
                    if role:
                        _, created = ContentItemPerson.objects.get_or_create(
                            content_item=item,
                            person=person,
                            role=role,
                        )
                        if created:
                            created_count += 1

                self.stdout.write(self.style.SUCCESS(f'OK (+{created_count} персон)'))
                updated += 1

            except services.KinopoiskError as exc:
                self.stdout.write(self.style.ERROR(f'ошибка API: {exc}'))
                errors += 1
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'ошибка: {exc}'))
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово: обновлено {updated} объектов, ошибок {errors}'
        ))
