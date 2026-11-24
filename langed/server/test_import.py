"""
Тесты команды import_bundle и миграции незаполненного состава игр
"""
import io
import json
import os
import tempfile
from datetime import date, datetime, time, timedelta
from unittest import mock

import pytz
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase, override_settings

from .management.commands.import_bundle import PosterError, download_poster, normalize_name
from .models import (
    City, CommonEvent, Convention, ConventionEvent, ConventionLink, Game, Room, Run, Venue,
)

User = get_user_model()


def png_bytes(image_format='PNG'):
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'white').save(buffer, image_format)
    return buffer.getvalue()


def bundle():
    """Набор: всё новое, связи по key"""
    start = date.today() + timedelta(days=30)
    return {
        'cities': [{'key': 'spb', 'name': 'Санкт-Петербург', 'timezone': 'Europe/Moscow'}],
        'venues': [{'key': 'loft', 'name': 'Лофт «Дом»', 'city': 'spb', 'address': 'Невский, 1',
                    'rooms': ['Зал 1', {'name': 'Чёрный зал', 'blackbox': True}]}],
        'games': [{
            'key': 'g1', 'name': '«Сто лет одиночества»', 'announcement': 'Анонс',
            'authors_text': 'Анна Смирнова (https://vk.com/anna)', 'source_url': 'https://vk.com/wall-1_1',
            'players_min': 4, 'players_max': 6, 'female_roles_min': None, 'technicians': 1,
        }],
        'conventions': [{'key': 'c1', 'name': 'Белые ночи', 'description': 'Конвент',
                         'source_url': 'https://vk.com/wall-1_2',
                         'links': [{'type': 'vk', 'url': 'https://vk.com/nights', 'title': 'Группа'}]}],
        'events': [{'key': 'e1', 'convention': 'c1', 'city': 'spb', 'venue': 'loft',
                    'date_start': start.isoformat(), 'date_end': (start + timedelta(days=1)).isoformat(),
                    'source_url': 'https://vk.com/wall-1_3'}],
        'runs': [{'event': 'e1', 'game': 'g1', 'date_local': f'{start.isoformat()}T12:00', 'duration': 240,
                  'rooms': ['Зал 1']}],
        'common_events': [{'event': 'e1', 'name': 'Ужин', 'date_local': f'{start.isoformat()}T19:00',
                           'duration': 60, 'description': 'В кафе'}],
    }


class ImportBundleTestCase(TestCase):

    def run_import(self, data, *args):
        """Запустить команду; вернуть JSON-сводку и человекочитаемый вывод"""
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False)
        self.addCleanup(os.unlink, file.name)
        out, err = io.StringIO(), io.StringIO()
        call_command('import_bundle', file.name, *args, stdout=out, stderr=err)
        return json.loads(out.getvalue()), err.getvalue()

    @staticmethod
    def item(result, section, key):
        return next(item for item in result['items'] if item['section'] == section and item['key'] == key)


class NormalizeNameTests(TestCase):

    def test_normalize(self):
        self.assertEqual(normalize_name('  «Ёлка»,  и — ПАЛКА! '), normalize_name('"елка" и палка'))
        self.assertEqual(normalize_name('Сто-лет'), normalize_name('сто лет'))
        self.assertNotEqual(normalize_name('Сто лет'), normalize_name('Сто лет 2'))


class ImportBundleTests(ImportBundleTestCase):

    def test_creates_everything_with_relations(self):
        result, human = self.run_import(bundle())
        self.assertEqual(result['errors'], 0, result)
        game = Game.objects.get(name='«Сто лет одиночества»')
        self.assertEqual(game.authors_text, 'Анна Смирнова (https://vk.com/anna)')
        self.assertEqual(game.source_url, 'https://vk.com/wall-1_1')
        self.assertEqual((game.players_min, game.players_max, game.female_roles_min), (4, 6, None))
        self.assertEqual(game.technicians, 1)
        self.assertFalse(game.creators.exists())
        venue = Venue.objects.get(name='Лофт «Дом»')
        self.assertEqual(sorted(venue.rooms.values_list('name', 'blackbox')), [('Зал 1', False), ('Чёрный зал', True)])
        event = ConventionEvent.objects.get(convention__name='Белые ночи')
        self.assertEqual((event.venue, event.source_url), (venue, 'https://vk.com/wall-1_3'))
        self.assertEqual(event.convention.source_url, 'https://vk.com/wall-1_2')
        self.assertEqual(ConventionLink.objects.get(convention=event.convention).link_type, 'vk')
        run = Run.objects.get(game=game)
        self.assertEqual(run.convention_event, event)
        self.assertEqual(run.city, event.city)
        self.assertEqual(run.duration, 240)
        self.assertEqual(list(run.rooms.values_list('name', flat=True)), ['Зал 1'])
        # Местное время города → UTC
        self.assertEqual(run.date.astimezone(pytz.timezone('Europe/Moscow')).hour, 12)
        self.assertFalse(run.masters.exists())
        self.assertEqual(CommonEvent.objects.get(convention_event=event).description, 'В кафе')
        self.assertEqual(result['summary']['games'], {'created': 1})
        self.assertIn('Игры:', human)

    def test_second_run_creates_nothing(self):
        self.run_import(bundle())
        counts = [model.objects.count() for model in (City, Venue, Room, Game, Convention, ConventionLink,
                                                       ConventionEvent, Run, CommonEvent)]
        result, _ = self.run_import(bundle())
        self.assertEqual(counts, [model.objects.count() for model in (City, Venue, Room, Game, Convention,
                                                                       ConventionLink, ConventionEvent, Run,
                                                                       CommonEvent)])
        self.assertEqual({item['action'] for item in result['items']}, {'unchanged'})
        self.assertEqual(result['errors'], 0)

    def test_dry_run_rolls_back(self):
        result, human = self.run_import(bundle(), '--dry-run')
        self.assertTrue(result['dry_run'])
        self.assertEqual(result['summary']['runs'], {'created': 1})
        self.assertFalse(Game.objects.filter(name='«Сто лет одиночества»').exists())
        self.assertFalse(City.objects.filter(name='Санкт-Петербург').exists())
        self.assertFalse(Run.objects.exists())
        self.assertIn('--dry-run', human)

    def test_matches_existing_records(self):
        city = City.objects.create(name='САНКТ-ПЕТЕРБУРГ')
        game = Game.objects.create(name='Сто лет одиночества.', announcement='Своё', players_min=3)
        convention = Convention.objects.create(name='белые  ночи')
        data = bundle()
        result, _ = self.run_import(data)
        self.assertEqual(result['errors'], 0, result)
        self.assertEqual(City.objects.count(), 1)
        self.assertEqual(Game.objects.count(), 1)
        self.assertEqual(Convention.objects.count(), 1)
        self.assertEqual(self.item(result, 'cities', 'spb')['action'], 'unchanged')
        self.assertEqual(Venue.objects.get().city, city)

        game.refresh_from_db()
        # Заполнены только пустые поля, остальное — конфликты без перезаписи
        self.assertEqual(game.announcement, 'Своё')
        self.assertEqual(game.players_min, 3)
        self.assertEqual(game.players_max, 6)
        self.assertEqual(game.source_url, 'https://vk.com/wall-1_1')
        self.assertEqual(game.technicians, 1)
        game_item = self.item(result, 'games', 'g1')
        self.assertEqual(game_item['action'], 'filled')
        self.assertEqual(set(game_item['filled']),
                         {'authors_text', 'source_url', 'players_max', 'technicians'})
        self.assertEqual(game_item['conflicts']['announcement'], {'db': 'Своё', 'bundle': 'Анонс'})
        self.assertEqual(game_item['conflicts']['players_min'], {'db': 3, 'bundle': 4})

        convention.refresh_from_db()
        self.assertEqual(convention.description, 'Конвент')
        self.assertEqual(Run.objects.get().game, game)

    def test_references_by_name_and_id_in_db(self):
        city = City.objects.create(name='Казань', timezone='Europe/Moscow')
        venue = Venue.objects.create(name='Площадка', city=city)
        Room.objects.create(venue=venue, name='Зал А')
        game = Game.objects.create(name='Старая игра')
        convention = Convention.objects.create(name='Старый конвент')
        start = date.today() + timedelta(days=5)
        event = ConventionEvent.objects.create(convention=convention, city=city, date_start=start, date_end=start)
        data = {
            'events': [{'key': 'e', 'convention': 'старый конвент', 'city': 'казань', 'venue': 'площадка',
                        'date_start': start.isoformat()}],
            'runs': [
                {'event': 'e', 'game': 'СТАРАЯ ИГРА', 'date_local': f'{start.isoformat()}T10:00', 'rooms': ['зал а']},
                {'event': event.pk, 'game': game.pk, 'date_local': f'{start.isoformat()}T15:00'},
                {'event': None, 'game': 'Старая игра', 'city': 'Казань', 'venue': 'Площадка',
                 'date_local': f'{start.isoformat()}T20:00'},
            ],
        }
        result, _ = self.run_import(data)
        self.assertEqual(result['errors'], 0, result)
        self.assertEqual(ConventionEvent.objects.count(), 1)
        event.refresh_from_db()
        self.assertEqual(event.venue, venue)  # пустая площадка заполнена
        self.assertEqual(self.item(result, 'events', 'e')['filled'], ['venue'])
        self.assertEqual(Run.objects.filter(convention_event=event).count(), 2)
        self.assertEqual(Run.objects.filter(convention_event=None).count(), 1)
        morning = pytz.timezone('Europe/Moscow').localize(datetime.combine(start, time(10, 0)))
        self.assertEqual(list(Run.objects.get(date=morning).rooms.values_list('name', flat=True)), ['Зал А'])

    def test_errors_do_not_stop_import(self):
        data = bundle()
        data['games'].append({'key': 'bad', 'name': 'Плохая', 'players_min': 5, 'players_max': 2})
        data['runs'].append({'event': 'e1', 'game': 'bad', 'date_local': '2000-01-01T10:00'})
        data['runs'].append({'event': 'e1', 'game': 'g1', 'date_local': '2000-01-01T10:00'})
        data['runs'].append({'event': 'e1', 'game': 'нет такой', 'date_local': '2000-01-01T10:00'})
        result, human = self.run_import(data)
        self.assertEqual(result['errors'], 4)
        self.assertFalse(Game.objects.filter(name='Плохая').exists())
        self.assertTrue(Game.objects.filter(name='«Сто лет одиночества»').exists())
        self.assertEqual(Run.objects.count(), 1)
        errors = [item['errors'][0] for item in result['items'] if item['action'] == 'error']
        self.assertTrue(any('не загружена' in message for message in errors), errors)
        self.assertTrue(any('в пределах дат' in message for message in errors), errors)
        self.assertTrue(any('нет ни в наборе, ни в БД' in message for message in errors), errors)
        self.assertIn('ошибка:', human)

    def test_duplicate_keys_and_invalid_values(self):
        data = {'games': [
            {'key': 'x', 'name': 'Игра 1', 'source_url': 'javascript:alert(1)'},
            {'key': 'x', 'name': 'Игра 2'},
            {'name': 'Игра 3', 'players_min': -1},
        ]}
        result, _ = self.run_import(data)
        self.assertEqual(Game.objects.get().name, 'Игра 1')
        self.assertEqual(Game.objects.get().source_url, '')
        self.assertTrue(self.item(result, 'games', 'x')['warnings'])
        self.assertEqual(result['errors'], 2)

    def test_users_are_not_touched(self):
        users = User.objects.count()
        self.run_import(bundle())
        self.assertEqual(User.objects.count(), users)

    def test_source_tag_marks_audit_log(self):
        from auditlog.models import LogEntry
        result, _ = self.run_import({'games': [{'name': 'С меткой'}]}, '--source-tag', 'vk-test')
        self.assertEqual(result['source_tag'], 'vk-test')
        game = Game.objects.get(name='С меткой')
        entry = LogEntry.objects.get_for_object(game).get()
        self.assertEqual(entry.additional_data, {'import_bundle': 'vk-test'})

    def test_bad_file(self):
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as file:
            file.write('[1, 2]')
        self.addCleanup(os.unlink, file.name)
        with self.assertRaises(CommandError):
            call_command('import_bundle', file.name, stdout=io.StringIO(), stderr=io.StringIO())
        with self.assertRaises(CommandError):
            call_command('import_bundle', '/nonexistent.json', stdout=io.StringIO(), stderr=io.StringIO())


class ImportAgeRatingTests(ImportBundleTestCase):

    def test_new_game_gets_age_rating(self):
        result, _ = self.run_import({'games': [{'name': 'Взрослая', 'age_rating': '18+'},
                                               {'name': 'Без рейтинга', 'age_rating': ''}]})
        self.assertEqual(result['errors'], 0, result)
        self.assertEqual(Game.objects.get(name='Взрослая').age_rating, '18+')
        self.assertEqual(Game.objects.get(name='Без рейтинга').age_rating, '')

    def test_invalid_age_rating_is_item_error(self):
        result, _ = self.run_import({'games': [{'name': 'Неверная', 'age_rating': '17+'},
                                               {'name': 'Без плюса', 'age_rating': '16'}]})
        self.assertEqual(result['errors'], 2)
        self.assertFalse(Game.objects.exists())
        self.assertIn('age_rating', self.item(result, 'games', 'Неверная')['errors'][0])

    def test_existing_game_filled_only_when_empty(self):
        empty = Game.objects.create(name='Пустая')
        rated = Game.objects.create(name='С рейтингом', age_rating='12+')
        result, _ = self.run_import({'games': [{'name': 'Пустая', 'age_rating': '6+'},
                                               {'name': 'С рейтингом', 'age_rating': '16+'}]})
        self.assertEqual(result['errors'], 0, result)
        empty.refresh_from_db()
        rated.refresh_from_db()
        self.assertEqual(empty.age_rating, '6+')
        self.assertEqual(self.item(result, 'games', 'Пустая')['filled'], ['age_rating'])
        self.assertEqual(rated.age_rating, '12+')
        item = self.item(result, 'games', 'С рейтингом')
        self.assertEqual(item['action'], 'unchanged')
        self.assertEqual(item['conflicts']['age_rating'], {'db': '12+', 'bundle': '16+'})


class ImportGameKindTests(ImportBundleTestCase):

    def test_new_game_gets_kind(self):
        result, _ = self.run_import({'games': [
            {'name': 'Без типа'},
            {'name': 'Настольная ролевая', 'kind': 'ttrpg'},
            {'name': 'Спектакль', 'kind': 'Другое'},
            {'name': 'Кабинетная', 'kind': 'кри'},
            {'name': 'Ещё НРИ', 'kind': 'НРИ'},
        ]})
        self.assertEqual(result['errors'], 0, result)
        kinds = dict(Game.objects.values_list('name', 'kind'))
        self.assertEqual(kinds, {
            'Без типа': 'larp', 'Настольная ролевая': 'ttrpg', 'Спектакль': 'other',
            'Кабинетная': 'larp', 'Ещё НРИ': 'ttrpg',
        })

    def test_invalid_kind_is_item_error(self):
        result, _ = self.run_import({'games': [{'name': 'Неверная', 'kind': 'board'},
                                               {'name': 'Список', 'kind': ['larp']}]})
        self.assertEqual(result['errors'], 2)
        self.assertFalse(Game.objects.exists())
        self.assertIn('kind', self.item(result, 'games', 'Неверная')['errors'][0])
        self.assertIn('kind', self.item(result, 'games', 'Список')['errors'][0])

    def test_existing_default_kind_is_filled(self):
        game = Game.objects.create(name='Была КРИ')
        result, _ = self.run_import({'games': [{'name': 'Была КРИ', 'kind': 'НРИ'}]})
        self.assertEqual(result['errors'], 0, result)
        game.refresh_from_db()
        self.assertEqual(game.kind, 'ttrpg')
        item = self.item(result, 'games', 'Была КРИ')
        self.assertEqual(item['filled'], ['kind'])
        self.assertFalse(item.get('conflicts'))

    def test_same_or_missing_kind_is_unchanged(self):
        Game.objects.create(name='КРИ')
        Game.objects.create(name='НРИ', kind='ttrpg')
        result, _ = self.run_import({'games': [{'name': 'КРИ', 'kind': 'larp'},
                                               {'name': 'НРИ', 'kind': 'ttrpg'},
                                               {'key': 'nri-again', 'name': 'НРИ'}]})
        self.assertEqual(result['errors'], 0, result)
        self.assertEqual({item['action'] for item in result['items']}, {'unchanged'})
        self.assertFalse(any(item.get('conflicts') for item in result['items']), result)

    def test_other_kind_is_conflict(self):
        game = Game.objects.create(name='Настолка', kind='other')
        result, _ = self.run_import({'games': [{'name': 'Настолка', 'kind': 'ttrpg'},
                                               {'key': 'as-larp', 'name': 'Настолка', 'kind': 'larp'}]})
        self.assertEqual(result['errors'], 0, result)
        game.refresh_from_db()
        self.assertEqual(game.kind, 'other')
        item = self.item(result, 'games', 'Настолка')
        self.assertEqual(item['action'], 'unchanged')
        self.assertEqual(item['conflicts']['kind'], {'db': 'other', 'bundle': 'ttrpg'})
        self.assertEqual(self.item(result, 'games', 'as-larp')['conflicts']['kind'], {'db': 'other', 'bundle': 'larp'})


class ImportSameNameGamesTests(ImportBundleTestCase):

    def setUp(self):
        self.city = City.objects.create(name='Казань', timezone='Europe/Moscow')
        self.start = date.today() + timedelta(days=10)

    def run_entry(self, game_ref, hour=12):
        return {'game': game_ref, 'city': 'Казань', 'date_local': f'{self.start.isoformat()}T{hour}:00'}

    def test_not_ids_creates_second_game_and_rerun_is_idempotent(self):
        old = Game.objects.create(name='Сто лет одиночества', announcement='Старая')
        data = {
            'games': [{'key': 'new', 'name': '«Сто лет одиночества»', 'announcement': 'Новая',
                       'not_ids': [old.pk]}],
            'runs': [self.run_entry('new')],
        }
        result, _ = self.run_import(data)
        self.assertEqual(result['errors'], 0, result)
        self.assertEqual(Game.objects.count(), 2)
        new = Game.objects.exclude(pk=old.pk).get()
        self.assertEqual(new.announcement, 'Новая')
        self.assertEqual(self.item(result, 'games', 'new')['action'], 'created')
        self.assertEqual(self.item(result, 'games', 'new')['id'], new.pk)
        old.refresh_from_db()
        self.assertEqual(old.announcement, 'Старая')
        self.assertEqual(Run.objects.get().game, new)

        # Повторный прогон находит созданную игру и ничего не создаёт
        result, _ = self.run_import(data)
        self.assertEqual(result['errors'], 0, result)
        self.assertEqual(Game.objects.count(), 2)
        self.assertEqual(Run.objects.count(), 1)
        self.assertEqual(self.item(result, 'games', 'new')['id'], new.pk)
        self.assertEqual({item['action'] for item in result['items']}, {'unchanged'})
        self.assertFalse(self.item(result, 'games', 'new').get('warnings'))

    def test_two_same_name_games_in_one_bundle(self):
        old = Game.objects.create(name='Игра')
        data = {
            'games': [{'key': 'a', 'name': 'Игра', 'not_ids': [old.pk]},
                      {'key': 'b', 'name': 'игра', 'not_ids': [old.pk]}],
        }
        result, _ = self.run_import(data)
        # Вторая запись без исключения созданной первой сопоставляется с ней же
        self.assertEqual(result['errors'], 0, result)
        self.assertEqual(Game.objects.count(), 2)
        self.assertEqual(self.item(result, 'games', 'a')['id'], self.item(result, 'games', 'b')['id'])

    def test_several_candidates_take_smallest_id_with_warning(self):
        first = Game.objects.create(name='Игра')
        Game.objects.create(name='ИГРА')
        result, _ = self.run_import({'games': [{'name': 'игра', 'red_flags': 'Флаги'}]})
        self.assertEqual(result['errors'], 0, result)
        self.assertEqual(Game.objects.count(), 2)
        item = self.item(result, 'games', 'игра')
        self.assertEqual(item['id'], first.pk)
        self.assertTrue(any('not_ids' in warning for warning in item['warnings']), item)
        first.refresh_from_db()
        self.assertEqual(first.red_flags, 'Флаги')

    def test_run_by_ambiguous_name_is_error(self):
        first = Game.objects.create(name='Игра')
        second = Game.objects.create(name='Игра')
        result, _ = self.run_import({'runs': [self.run_entry('Игра', 10), self.run_entry(second.pk, 14)]})
        self.assertEqual(result['errors'], 1)
        error = next(item for item in result['items'] if item['action'] == 'error')['errors'][0]
        self.assertIn('несколько игр', error)
        self.assertIn('key', error)
        self.assertIn(str(first.pk), error)
        self.assertEqual(Run.objects.get().game, second)

    def test_invalid_not_ids(self):
        result, _ = self.run_import({'games': [{'name': 'Игра', 'not_ids': ['1']},
                                               {'key': 'two', 'name': 'Игра 2', 'not_ids': 5}]})
        self.assertEqual(result['errors'], 2)
        self.assertFalse(Game.objects.exists())
        self.assertIn('not_ids', self.item(result, 'games', 'Игра')['errors'][0])


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class ImportPosterTests(ImportBundleTestCase):

    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)

    def test_poster_saved_only_when_missing(self):
        data = {'games': [{'name': 'С постером', 'poster_url': 'https://example.com/p.png'}]}
        with mock.patch('server.management.commands.import_bundle.download_poster',
                        return_value=('png', png_bytes())) as download:
            result, _ = self.run_import(data)
            self.assertEqual(self.item(result, 'games', 'С постером')['poster'], 'saved')
            game = Game.objects.get()
            self.assertTrue(game.poster.name.startswith('games/posters/import-'))
            # Постер уже есть — повторно не скачиваем
            result, _ = self.run_import(data)
            self.assertEqual(download.call_count, 1)
            self.assertEqual(self.item(result, 'games', 'С постером')['action'], 'unchanged')

    def test_dry_run_does_not_download(self):
        data = {'games': [{'name': 'С постером', 'poster_url': 'https://example.com/p.png'}]}
        with mock.patch('server.management.commands.import_bundle.download_poster') as download:
            result, _ = self.run_import(data, '--dry-run')
        download.assert_not_called()
        self.assertEqual(self.item(result, 'games', 'С постером')['poster'], 'planned')

    def test_download_error_is_warning(self):
        data = {'games': [{'name': 'Без постера', 'poster_url': 'https://example.com/p.png'}]}
        with mock.patch('server.management.commands.import_bundle.download_poster',
                        side_effect=PosterError('файл больше 5 МБ')):
            result, _ = self.run_import(data)
        item = self.item(result, 'games', 'Без постера')
        self.assertEqual(item['action'], 'created')
        self.assertIn('постер: файл больше 5 МБ', item['warnings'])
        self.assertFalse(Game.objects.get().poster)


class DownloadPosterTests(TestCase):

    def response(self, body, headers=None):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.headers = headers or {}
        response.iter_content.return_value = [body[i:i + 1024] for i in range(0, len(body), 1024)]
        return response

    def test_scheme(self):
        with self.assertRaises(PosterError):
            download_poster('file:///etc/passwd')
        with self.assertRaises(PosterError):
            download_poster('ftp://example.com/p.png')

    def test_format_and_size(self):
        target = 'server.management.commands.import_bundle.requests.get'
        with mock.patch(target, return_value=self.response(png_bytes('WEBP'))) as get:
            self.assertEqual(download_poster('https://example.com/p')[0], 'webp')
        self.assertIn('timeout', get.call_args.kwargs)
        with mock.patch(target, return_value=self.response(png_bytes('GIF'))):
            with self.assertRaises(PosterError):
                download_poster('https://example.com/p.gif')
        with mock.patch(target, return_value=self.response(b'not an image')):
            with self.assertRaises(PosterError):
                download_poster('https://example.com/p.png')
        with mock.patch(target, return_value=self.response(b'', {'Content-Length': str(6 * 1024 * 1024)})):
            with self.assertRaises(PosterError):
                download_poster('https://example.com/big.png')
        with mock.patch('server.management.commands.import_bundle.POSTER_MAX_SIZE', 10), \
                mock.patch(target, return_value=self.response(png_bytes())):
            with self.assertRaises(PosterError):
                download_poster('https://example.com/p.png')


class DefaultCountsMigrationTests(TransactionTestCase):
    """Миграция 0026: значения по умолчанию прежнего импорта → null"""

    before = [('server', '0025_registration_rejected_status')]
    after = [('server', '0026_game_authors_text_source_url_nullable_counts')]

    def tearDown(self):
        # Вернуть схему тестовой БД к последним миграциям
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_defaults_become_null(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        old_apps = executor.loader.project_state(self.before).apps
        OldGame = old_apps.get_model('server', 'Game')
        imported = OldGame.objects.create(name='Импорт')  # 1–10, роли 0–0, игротехников нет
        with_technicians = OldGame.objects.create(name='С игротехником', technicians=1)
        real = OldGame.objects.create(name='Настоящая', players_min=1, players_max=10,
                                      female_roles_min=0, female_roles_max=3)
        filled = OldGame.objects.create(name='Заполненная', players_min=2, players_max=5)

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.after)
        new_apps = executor.loader.project_state(self.after).apps
        NewGame = new_apps.get_model('server', 'Game')

        def counts(game):
            game = NewGame.objects.get(pk=game.pk)
            return (game.players_min, game.players_max, game.female_roles_min, game.female_roles_max,
                    game.male_roles_min, game.male_roles_max)

        self.assertEqual(counts(imported), (None, None, None, None, None, None))
        self.assertEqual(counts(with_technicians), (1, 10, None, None, None, None))
        self.assertEqual(counts(real), (1, 10, 0, 3, None, None))
        self.assertEqual(counts(filled), (2, 5, None, None, None, None))
