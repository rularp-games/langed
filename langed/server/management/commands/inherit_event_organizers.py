"""
Команда для наследования организаторов проведений от организаторов конвентов.
Заполняет организаторов для проведений, у которых они не заданы.
"""

from django.core.management.base import BaseCommand
from server.models import ConventionEvent


class Command(BaseCommand):
    help = 'Наследует организаторов проведений от организаторов конвентов для существующих записей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Перезаписать организаторов даже если они уже заданы',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет сделано, не внося изменений',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)
        
        events = ConventionEvent.objects.select_related('convention').prefetch_related(
            'organizers', 'convention__organizers'
        ).all()
        
        updated_count = 0
        skipped_count = 0
        
        for event in events:
            current_organizers = event.organizers.count()
            convention_organizers = event.convention.organizers.all()
            
            if current_organizers == 0 or force:
                if convention_organizers.exists():
                    if dry_run:
                        self.stdout.write(
                            f'  [DRY RUN] {event.convention.name} ({event.date_start}): '
                            f'унаследует {convention_organizers.count()} организатор(ов)'
                        )
                    else:
                        event.organizers.set(convention_organizers)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  ✓ {event.convention.name} ({event.date_start}): '
                                f'унаследовано {convention_organizers.count()} организатор(ов)'
                            )
                        )
                    updated_count += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  ⚠ {event.convention.name} ({event.date_start}): '
                            f'у конвента нет организаторов'
                        )
                    )
                    skipped_count += 1
            else:
                self.stdout.write(
                    f'  - {event.convention.name} ({event.date_start}): '
                    f'уже есть {current_organizers} организатор(ов), пропущено'
                )
                skipped_count += 1
        
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(f'DRY RUN: Будет обновлено {updated_count} проведений'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Обновлено: {updated_count} проведений'))
        self.stdout.write(f'Пропущено: {skipped_count} проведений')
