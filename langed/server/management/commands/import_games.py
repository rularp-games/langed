"""
Management command для импорта игр из CSV файла.

Использование:
    python manage.py import_games path/to/games.csv
    python manage.py import_games path/to/games.csv --update  # обновлять существующие
"""
import csv
from django.core.management.base import BaseCommand, CommandError
from server.models import Game


class Command(BaseCommand):
    help = 'Импортирует игры из CSV файла'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Путь к CSV файлу')
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновлять существующие игры (по умолчанию пропускаются)'
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        update_existing = options['update']

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                created_count = 0
                updated_count = 0
                skipped_count = 0
                
                for row in reader:
                    name = row.get('название', '').strip()
                    if not name:
                        self.stdout.write(
                            self.style.WARNING(f'Пропущена строка без названия')
                        )
                        continue
                    
                    announcement = row.get('анонс', '').strip()
                    red_flags = row.get('красные флаги', '').strip()
                    
                    game, created = Game.objects.get_or_create(
                        name=name,
                        defaults={
                            'announcement': announcement,
                            'red_flags': red_flags,
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Создана игра: {name}')
                        )
                    elif update_existing:
                        game.announcement = announcement
                        game.red_flags = red_flags
                        game.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'Обновлена игра: {name}')
                        )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            f'Пропущена существующая игра: {name}'
                        )
                
                self.stdout.write(self.style.SUCCESS(
                    f'\nИтого: создано {created_count}, '
                    f'обновлено {updated_count}, пропущено {skipped_count}'
                ))
                
        except FileNotFoundError:
            raise CommandError(f'Файл не найден: {csv_file}')
        except Exception as e:
            raise CommandError(f'Ошибка при импорте: {e}')

