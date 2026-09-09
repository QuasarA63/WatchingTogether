from datetime import date, datetime, timezone

from django.core.management.base import BaseCommand
from django.urls import reverse

from apps.content import services
from apps.content.models import ContentItem, UserContentItem
from apps.content.web_views import (
    _import_seasons,
    _parse_air_date,
    released_episode_keys,
    season_numbers,
)
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = 'Проверить новые серии и сезоны сериалов и разослать уведомления'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что будет сделано, без записи в БД',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if not services.is_configured():
            self.stderr.write(self.style.ERROR(
                'Кинопоиск API не настроен: задайте KINOPOISK_API_KEY.'
            ))
            return

        series_qs = ContentItem.objects.filter(
            category__slug='series',
            parent__isnull=True,
            is_active=True,
        ).exclude(external_id='')

        today = date.today()
        baseline_count = 0
        updated_series = 0
        new_episode_total = 0
        new_season_total = 0
        notified_users = 0
        errors = 0

        for item in series_qs:
            try:
                seasons = services.get_seasons(item.external_id)
            except services.KinopoiskError as exc:
                self.stderr.write(self.style.ERROR(f'{item.title}: {exc}'))
                errors += 1
                continue

            current_episodes = released_episode_keys(seasons, today)
            current_seasons = season_numbers(seasons)

            meta = item.metadata or {}
            notified_before = set(map(tuple, meta.get('notified_episodes') or []))
            notified_seasons_before = set(meta.get('notified_seasons') or [])

            is_baseline = (
                'notified_episodes' not in meta
                and 'notified_seasons' not in meta
            )

            new_episode_keys = current_episodes - notified_before
            new_season_nums = current_seasons - notified_seasons_before

            new_episodes = []
            for season in seasons:
                season_num = season.get('number')
                for ep in season.get('episodes', []) or []:
                    air_date = _parse_air_date(ep.get('air_date'))
                    if not air_date or air_date > today:
                        continue
                    if (season_num, ep.get('number')) in new_episode_keys:
                        new_episodes.append({
                            'season': season_num,
                            'episode': ep.get('number'),
                            'name': ep.get('name') or '',
                            'air_date': air_date.isoformat(),
                        })

            if is_baseline:
                if dry_run:
                    self.stdout.write(f'{item.title}: базовая линия (dry-run)')
                else:
                    _import_seasons(item, item.external_id, seasons_data=seasons)
                    item.metadata['notified_episodes'] = sorted(
                        [list(k) for k in current_episodes]
                    )
                    item.metadata['notified_seasons'] = sorted(current_seasons)
                    item.save(update_fields=['metadata', 'updated_at'])
                    baseline_count += 1
                    self.stdout.write(f'{item.title}: базовая линия зафиксирована')
                continue

            if not new_episodes and not new_season_nums:
                self.stdout.write(f'{item.title}: без изменений')
                continue

            if dry_run:
                self.stdout.write(
                    f'{item.title}: {len(new_episodes)} новых серий, '
                    f'{len(new_season_nums)} новых сезонов (dry-run)'
                )
                new_episode_total += len(new_episodes)
                new_season_total += len(new_season_nums)
                continue

            # Обновляем сезоны/даты в БД (в т.ч. создаём новые сезоны)
            _import_seasons(item, item.external_id, seasons_data=seasons)

            # Сохраняем сведения о новинках в сам объект
            item.metadata['new_episodes'] = new_episodes
            item.metadata['new_seasons'] = sorted(new_season_nums)
            item.metadata['new_updates_at'] = datetime.now(timezone.utc).isoformat()
            item.metadata['notified_episodes'] = sorted(
                [list(k) for k in current_episodes]
            )
            item.metadata['notified_seasons'] = sorted(current_seasons)
            item.save(update_fields=['metadata', 'updated_at'])

            # Рассылка уведомлений заинтересованным пользователям
            link = reverse('content_detail', args=[item.pk])
            recipient_statuses = [
                UserContentItem.Status.WATCHING,
                UserContentItem.Status.ON_HOLD,
                UserContentItem.Status.COMPLETED,
            ]
            user_ids = item.user_entries.filter(
                status__in=recipient_statuses
            ).values_list('user_id', flat=True).distinct()

            notifications = []
            for uid in user_ids:
                if new_episodes:
                    lines = []
                    for ep in new_episodes:
                        name = f' «{ep["name"]}»' if ep['name'] else ''
                        when = date.fromisoformat(ep['air_date']).strftime('%d.%m.%Y')
                        lines.append(
                            f'С{ep["season"]}E{ep["episode"]}{name} — {when}'
                        )
                    notifications.append(Notification(
                        user_id=uid,
                        notification_type='new_episode',
                        title=f'Новая серия: {item.title}',
                        message='Вышла новая серия:\n' + '\n'.join(lines),
                        link=link,
                    ))
                if new_season_nums:
                    nums = ', '.join(str(n) for n in sorted(new_season_nums))
                    notifications.append(Notification(
                        user_id=uid,
                        notification_type='new_season',
                        title=f'Новый сезон: {item.title}',
                        message=f'Вышел новый сезон {nums} сериала «{item.title}».',
                        link=link,
                    ))

            Notification.objects.bulk_create(notifications)
            notified_users += len(user_ids)
            updated_series += 1
            new_episode_total += len(new_episodes)
            new_season_total += len(new_season_nums)

            self.stdout.write(self.style.SUCCESS(
                f'{item.title}: {len(new_episodes)} новых серий, '
                f'{len(new_season_nums)} новых сезонов, '
                f'уведомлено пользователей: {len(user_ids)}'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nГотово: базовых линий {baseline_count}, обновлено сериалов '
            f'{updated_series}, новых серий {new_episode_total}, новых сезонов '
            f'{new_season_total}, уведомлено пользователей {notified_users}, '
            f'ошибок {errors}.'
        ))
