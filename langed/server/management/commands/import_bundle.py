"""
Загрузка подготовленного JSON-набора (города, площадки, игры, конвенты, проведения,
прогоны, общие события) в БД. Повторный запуск того же набора ничего не создаёт.

Использование:
    python manage.py import_bundle bundle.json
    python manage.py import_bundle bundle.json --dry-run          # всё в транзакции с откатом
    python manage.py import_bundle bundle.json --source-tag vk-2026-11

Вывод: человекочитаемый журнал — в stderr, JSON-сводка — в stdout.

Формат набора (все разделы и все поля, кроме отмеченных, необязательны):

    {
      "cities": [{"key", "name"*, "timezone"}],
      "venues": [{"key", "name"*, "city"*, "address", "rooms": ["Зал 1", {"name", "blackbox"}]}],
      "games": [{"key", "name"*, "not_ids", "announcement", "red_flags", "authors_text",
                 "source_url", "age_rating", "players_min", "players_max", "female_roles_min",
                 "female_roles_max", "male_roles_min", "male_roles_max", "technicians",
                 "poster_url"}],
      "conventions": [{"key", "name"*, "description", "source_url",
                       "links": [{"type", "url"*, "title"}]}],
      "events": [{"key", "convention"*, "city"*, "venue", "date_start"*, "date_end", "source_url"}],
      "runs": [{"event", "game"*, "city", "venue", "date_local"*, "duration", "rooms": ["Зал 1"]}],
      "common_events": [{"event"*, "name"*, "date_local"*, "duration", "description"}]
    }

    key — идентификатор записи внутри набора (по умолчанию — name). Ссылки (city, venue,
    convention, event, game) — key записи этого набора, иначе название существующей записи
    в БД (для event — только key) или её числовой id.
    timezone — из pytz (по умолчанию Europe/Moscow). date_start/date_end — YYYY-MM-DD
    (date_end по умолчанию = date_start). date_local — YYYY-MM-DDTHH:MM, местное время города
    (прогон: city, иначе город проведения; общее событие — город проведения).
    duration — минуты (прогон по умолчанию 180, общее событие — 60).
    Числа состава — целые ≥ 0 или null (не указано). links.type — vk, telegram, website,
    discord, youtube, other. rooms прогона — названия помещений площадки venue прогона,
    иначе площадки проведения. poster_url — http(s)-адрес постера. age_rating — 0+, 6+, 12+,
    16+, 18+ или пусто (не указан); другое значение — ошибка записи.
    not_ids игры — список id игр в БД, с которыми запись сопоставлять нельзя: так загружается
    другая игра с тем же названием, что и существующая. key такой записи лучше задать явно
    и ссылаться из runs.game по нему.

Сопоставление с существующими записями:
    город — название без учёта регистра; площадка — город + нормализованное название;
    игра, конвент — нормализованное название (регистр, ё/е, кавычки, пунктуация, пробелы);
    у игры — среди одноимённых, кроме not_ids; подходящей нет — создаётся новая, несколько —
    берётся с наименьшим id (с предупреждением). Ссылка runs.game на название существующей
    игры, когда одноимённых в БД несколько, неоднозначна — ошибка записи (укажите key или id);
    проведение — конвент + date_start; прогон — игра + время + проведение;
    общее событие — проведение + нормализованное название + время;
    ссылка конвента — URL; помещение — название в площадке.

Существующие записи не перезаписываются: заполняются только пустые поля, расхождения
попадают в отчёт как конфликты. Пользователи (авторы, мастера, организаторы) не создаются
и не меняются. Постер скачивается (http/https, таймаут, не больше 5 МБ, JPEG/PNG/WebP)
только если у игры постера нет; ошибка скачивания — предупреждение, импорт продолжается.
В --dry-run постеры не скачиваются. --source-tag (по умолчанию — имя файла) попадает
в отчёт и в additional_data записей журнала изменений (auditlog), созданных импортом.
"""
import datetime
import io
import json
import os
import re
import unicodedata
from collections import defaultdict

import pytz
import requests
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from django.db import DatabaseError, transaction

from server.models import (
    City, CommonEvent, Convention, ConventionEvent, ConventionLink, Game, Room, Run, Venue,
    date_outside_event_error,
)
from server.serializers import POSTER_CONTENT_TYPES, POSTER_MAX_SIZE

SECTIONS = ('cities', 'venues', 'games', 'conventions', 'events', 'runs', 'common_events')
SECTION_TITLES = {
    'cities': 'Города', 'venues': 'Площадки', 'games': 'Игры', 'conventions': 'Конвенты',
    'events': 'Проведения', 'runs': 'Прогоны', 'common_events': 'Общие события',
}
GAME_TEXT_FIELDS = ('announcement', 'red_flags', 'authors_text')
GAME_COUNT_FIELDS = (
    'players_min', 'players_max', 'female_roles_min', 'female_roles_max',
    'male_roles_min', 'male_roles_max',
)
GAME_RANGES = ('players', 'female_roles', 'male_roles')
GAME_AGE_RATINGS = tuple(choice for choice, _ in Game._meta.get_field('age_rating').choices)
LINK_TYPES = {choice for choice, _ in ConventionLink.LINK_TYPE_CHOICES}
DEFAULT_TIMEZONE = 'Europe/Moscow'
POSTER_TIMEOUT = 20
POSTER_EXTENSIONS = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp'}


class ItemError(Exception):
    """Запись набора не может быть загружена"""


class PosterError(Exception):
    """Постер не удалось скачать или он не подходит"""


def normalize_name(value):
    """Название для сопоставления: регистр, ё/е, кавычки, пунктуация и пробелы не важны"""
    text = unicodedata.normalize('NFKC', str(value or '')).casefold().replace('ё', 'е')
    text = re.sub(r'[\W_]+', ' ', text)
    return ' '.join(text.split())


def fold_city(value):
    """Название города для сравнения без учёта регистра (в Python: SQLite не умеет кириллицу)"""
    return ' '.join(str(value or '').split()).casefold()


def normalize_url(value):
    return str(value or '').strip().rstrip('/')


def download_poster(url):
    """
    Скачать постер: только http/https, таймаут, не больше POSTER_MAX_SIZE, формат —
    JPEG/PNG/WebP по содержимому (Pillow), как у валидатора постера.
    Возвращает (расширение, байты).
    """
    from PIL import Image

    if not re.match(r'^https?://', str(url or ''), re.IGNORECASE):
        raise PosterError('адрес постера должен начинаться с http:// или https://')
    try:
        with requests.get(url, stream=True, timeout=POSTER_TIMEOUT) as response:
            response.raise_for_status()
            declared = response.headers.get('Content-Length')
            if declared and declared.isdigit() and int(declared) > POSTER_MAX_SIZE:
                raise PosterError('файл больше 5 МБ')
            chunks, size = [], 0
            for chunk in response.iter_content(64 * 1024):
                size += len(chunk)
                if size > POSTER_MAX_SIZE:
                    raise PosterError('файл больше 5 МБ')
                chunks.append(chunk)
    except requests.RequestException as error:
        raise PosterError(f'не удалось скачать: {error}')
    data = b''.join(chunks)
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
            content_type = Image.MIME.get(image.format)
    except Exception:
        raise PosterError('файл не является изображением')
    if content_type not in POSTER_CONTENT_TYPES:
        raise PosterError('постер должен быть в формате JPEG, PNG или WebP')
    return POSTER_EXTENSIONS[content_type], data


class Report:
    """Результаты импорта: по записи на каждый элемент набора"""

    def __init__(self):
        self.items = []
        self.warnings = []

    def add(self, section, key, action, obj=None, label='', **extra):
        item = {'section': section, 'key': key, 'action': action,
                'id': getattr(obj, 'pk', None), 'label': label}
        item.update({name: value for name, value in extra.items() if value})
        self.items.append(item)
        return item

    def summary(self):
        counts = {section: defaultdict(int) for section in SECTIONS}
        for item in self.items:
            counts[item['section']][item['action']] += 1
        return {section: dict(values) for section, values in counts.items() if values}


class Importer:
    """Загрузка набора в текущей транзакции"""

    def __init__(self, bundle, *, dry_run=False):
        self.bundle = bundle
        self.dry_run = dry_run
        self.report = Report()
        # key набора → объект БД (None — запись не загрузилась)
        self.keys = {section: {} for section in SECTIONS}
        self.saved_files = []
        self.url_validator = URLValidator(schemes=['http', 'https'])
        self._load_indexes()

    # --- Индексы существующих записей ---

    def _load_indexes(self):
        self.city_index = {}
        for city in City.objects.order_by('pk'):
            self.city_index.setdefault(fold_city(city.name), city)
        self.venue_index = {}
        for venue in Venue.objects.order_by('pk'):
            self.venue_index.setdefault((venue.city_id, normalize_name(venue.name)), venue)
        # Нормализованное название → одноимённые игры по возрастанию id
        self.game_index = defaultdict(list)
        for game in Game.objects.order_by('pk'):
            self.game_index[normalize_name(game.name)].append(game)
        self.convention_index = {}
        for convention in Convention.objects.order_by('pk'):
            self.convention_index.setdefault(normalize_name(convention.name), convention)

    # --- Разбор значений ---

    @staticmethod
    def text(entry, field):
        value = entry.get(field)
        if value is None:
            return ''
        if not isinstance(value, (str, int, float)):
            raise ItemError(f'{field}: ожидается строка')
        return str(value).strip()

    def url(self, entry, field, warnings):
        value = self.text(entry, field)
        if not value:
            return ''
        try:
            self.url_validator(value)
        except ValidationError:
            warnings.append(f'{field}: некорректный адрес «{value}» — пропущен')
            return ''
        if len(value) > 500:
            warnings.append(f'{field}: адрес длиннее 500 символов — пропущен')
            return ''
        return value

    @staticmethod
    def count(entry, field, *, minimum=0):
        value = entry.get(field)
        if value is None or value == '':
            return None
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ItemError(f'{field}: ожидается целое число')
        try:
            number = int(value)
        except ValueError:
            raise ItemError(f'{field}: ожидается целое число')
        if number < minimum:
            raise ItemError(f'{field}: число должно быть не меньше {minimum}')
        return number

    @staticmethod
    def date(entry, field, *, required=True):
        value = entry.get(field)
        if not value:
            if required:
                raise ItemError(f'{field}: дата обязательна')
            return None
        try:
            return datetime.date.fromisoformat(str(value))
        except ValueError:
            raise ItemError(f'{field}: ожидается дата YYYY-MM-DD')

    @staticmethod
    def local_datetime(entry, field, timezone_name):
        value = entry.get(field)
        if not value:
            raise ItemError(f'{field}: время обязательно')
        try:
            naive = datetime.datetime.fromisoformat(str(value))
        except ValueError:
            raise ItemError(f'{field}: ожидается YYYY-MM-DDTHH:MM')
        if naive.tzinfo is not None:
            raise ItemError(f'{field}: время указывается местное, без часового пояса')
        return pytz.timezone(timezone_name).localize(naive).astimezone(pytz.UTC)

    @staticmethod
    def required(entry, field):
        value = Importer.text(entry, field)
        if not value:
            raise ItemError(f'{field}: обязательное поле')
        return value

    # --- Ссылки ---

    def resolve(self, section, ref, *, city=None, required=False, field=None):
        """Объект по key набора, id или названию существующей записи"""
        field = field or section
        if ref is None or ref == '':
            if required:
                raise ItemError(f'{field}: обязательная ссылка')
            return None
        if isinstance(ref, str) and ref in self.keys[section]:
            obj = self.keys[section][ref]
            if obj is None:
                raise ItemError(f'{field}: запись «{ref}» набора не загружена')
            return obj
        model = {
            'cities': City, 'venues': Venue, 'games': Game, 'conventions': Convention,
            'events': ConventionEvent,
        }[section]
        if isinstance(ref, int) and not isinstance(ref, bool):
            obj = model.objects.filter(pk=ref).first()
            if obj is None:
                raise ItemError(f'{field}: запись с id {ref} не найдена')
            return obj
        if not isinstance(ref, str):
            raise ItemError(f'{field}: ожидается key, название или id')
        obj = None
        if section == 'cities':
            obj = self.city_index.get(fold_city(ref))
        elif section == 'venues':
            if city is not None:
                obj = self.venue_index.get((city.pk, normalize_name(ref)))
        elif section == 'games':
            games = self.game_index.get(normalize_name(ref)) or []
            if len(games) > 1:
                ids = ', '.join(str(game.pk) for game in games)
                raise ItemError(
                    f'{field}: в БД несколько игр «{ref}» (id {ids}) — '
                    'укажите key записи набора или id игры'
                )
            obj = games[0] if games else None
        elif section == 'conventions':
            obj = self.convention_index.get(normalize_name(ref))
        if obj is None:
            raise ItemError(f'{field}: «{ref}» нет ни в наборе, ни в БД')
        return obj

    # --- Заполнение пустых полей ---

    @staticmethod
    def fill(obj, values, filled, conflicts, *, empty=(None, '')):
        """Заполнить пустые поля; расхождения с непустыми — в conflicts"""
        for field, value in values.items():
            if value in (None, ''):
                continue
            current = getattr(obj, field)
            if current in empty:
                setattr(obj, field, value)
                filled.append(field)
            elif current != value:
                conflicts[field] = {'db': _plain(current), 'bundle': _plain(value)}

    # --- Разделы ---

    def run(self):
        unknown = sorted(set(self.bundle) - set(SECTIONS))
        if unknown:
            self.report.warnings.append(f'Неизвестные разделы пропущены: {", ".join(unknown)}')
        for section in SECTIONS:
            entries = self.bundle.get(section) or []
            if not isinstance(entries, list):
                raise CommandError(f'Раздел {section} должен быть списком')
            handler = getattr(self, f'import_{section}')
            for index, entry in enumerate(entries):
                self._import_entry(section, index, entry, handler)
        return self.report

    def _import_entry(self, section, index, entry, handler):
        if not isinstance(entry, dict):
            self.report.add(section, f'#{index}', 'error', errors=['запись должна быть объектом'])
            return
        key = entry.get('key') or entry.get('name') or f'#{index}'
        if not isinstance(key, str):
            key = str(key)
        if key in self.keys[section]:
            self.report.add(section, key, 'error', errors=[f'повторяющийся key «{key}»'])
            return
        self.keys[section][key] = None
        warnings = []
        try:
            with transaction.atomic():
                obj, action, label, details = handler(entry, warnings)
        except (ItemError, ValidationError, DatabaseError) as error:
            message = '; '.join(error.messages) if isinstance(error, ValidationError) else str(error)
            self.report.add(section, key, 'error', errors=[message], warnings=warnings)
            return
        self.keys[section][key] = obj
        self.report.add(section, key, action, obj, label, warnings=warnings, **details)

    @staticmethod
    def _action(created, filled):
        if created:
            return 'created'
        return 'filled' if filled else 'unchanged'

    def import_cities(self, entry, warnings):
        name = self.required(entry, 'name')
        timezone_name = self.text(entry, 'timezone')
        if timezone_name and timezone_name not in pytz.all_timezones_set:
            raise ItemError(f'timezone: неизвестный часовой пояс «{timezone_name}»')
        city = self.city_index.get(fold_city(name))
        conflicts = {}
        if city is None:
            city = City.objects.create(name=' '.join(name.split()), timezone=timezone_name or DEFAULT_TIMEZONE)
            self.city_index[fold_city(name)] = city
            created = True
        else:
            created = False
            if timezone_name and timezone_name != city.timezone:
                conflicts['timezone'] = {'db': city.timezone, 'bundle': timezone_name}
        if timezone_name and timezone_name not in dict(City.TIMEZONE_CHOICES):
            warnings.append(f'timezone «{timezone_name}» нет в списке часовых поясов портала')
        return city, self._action(created, []), city.name, {'conflicts': conflicts}

    def import_venues(self, entry, warnings):
        name = self.required(entry, 'name')
        city = self.resolve('cities', entry.get('city'), required=True, field='city')
        address = self.text(entry, 'address')
        rooms = self._room_specs(entry.get('rooms'))
        venue = self.venue_index.get((city.pk, normalize_name(name)))
        filled, conflicts = [], {}
        if venue is None:
            venue = Venue.objects.create(name=name, city=city, address=address)
            self.venue_index[(city.pk, normalize_name(name))] = venue
            created = True
        else:
            created = False
            self.fill(venue, {'address': address}, filled, conflicts)
            if filled:
                venue.save()
        existing = {fold_city(room.name): room for room in venue.rooms.all()}
        rooms_added = []
        for room_name, blackbox in rooms:
            room = existing.get(fold_city(room_name))
            if room is None:
                room = Room.objects.create(venue=venue, name=room_name, blackbox=blackbox)
                existing[fold_city(room_name)] = room
                rooms_added.append(room_name)
            elif blackbox and not room.blackbox:
                conflicts[f'rooms.{room_name}.blackbox'] = {'db': False, 'bundle': True}
        if rooms_added and not created:
            filled.append('rooms')
        return venue, self._action(created, filled), f'{venue.name} ({city.name})', {
            'filled': filled, 'conflicts': conflicts, 'rooms_added': rooms_added,
        }

    def _room_specs(self, rooms):
        if rooms is None:
            return []
        if not isinstance(rooms, list):
            raise ItemError('rooms: ожидается список')
        specs = []
        for room in rooms:
            if isinstance(room, str) and room.strip():
                specs.append((room.strip(), False))
            elif isinstance(room, dict) and str(room.get('name') or '').strip():
                specs.append((str(room['name']).strip(), bool(room.get('blackbox'))))
            else:
                raise ItemError('rooms: помещение — строка или объект с name')
        return specs

    def import_games(self, entry, warnings):
        name = self.required(entry, 'name')
        if len(name) > 255:
            raise ItemError('name: длиннее 255 символов')
        values = {field: self.text(entry, field) for field in GAME_TEXT_FIELDS}
        values['source_url'] = self.url(entry, 'source_url', warnings)
        for field in GAME_COUNT_FIELDS:
            values[field] = self.count(entry, field)
        technicians = self.count(entry, 'technicians')
        for prefix in GAME_RANGES:
            low, high = values[f'{prefix}_min'], values[f'{prefix}_max']
            if low is not None and high is not None and low > high:
                raise ItemError(f'{prefix}_min больше {prefix}_max')
        values['age_rating'] = self.text(entry, 'age_rating')
        if values['age_rating'] and values['age_rating'] not in GAME_AGE_RATINGS:
            raise ItemError(
                f'age_rating: «{values["age_rating"]}» — допустимы {", ".join(GAME_AGE_RATINGS)} или пусто'
            )
        not_ids = self._ids(entry, 'not_ids')
        poster_url = self.text(entry, 'poster_url')

        candidates = [
            game for game in self.game_index.get(normalize_name(name), []) if game.pk not in not_ids
        ]
        if len(candidates) > 1:
            ids = ', '.join(str(game.pk) for game in candidates)
            warnings.append(
                f'одноимённых игр в БД несколько (id {ids}) — сопоставлено с id {candidates[0].pk}; '
                'остальные исключите через not_ids'
            )
        game = candidates[0] if candidates else None
        filled, conflicts = [], {}
        if game is None:
            game = Game.objects.create(name=name, technicians=technicians or 0, **values)
            self.game_index[normalize_name(name)].append(game)
            created = True
        else:
            created = False
            before = {field: getattr(game, field) for field in GAME_COUNT_FIELDS}
            self.fill(game, values, filled, conflicts)
            # Заполненная граница не должна противоречить сохранённой
            for prefix in GAME_RANGES:
                low_field, high_field = f'{prefix}_min', f'{prefix}_max'
                low, high = getattr(game, low_field), getattr(game, high_field)
                if low is not None and high is not None and low > high:
                    reverted = [field for field in (low_field, high_field) if field in filled]
                    for field in reverted:
                        setattr(game, field, before[field])
                        filled.remove(field)
                    if reverted:
                        warnings.append(f'{", ".join(reverted)}: противоречит значению в БД — не заполнено')
            self.fill(game, {'technicians': technicians}, filled, conflicts, empty=(0,))
            if filled:
                game.save()

        poster = self._poster(game, poster_url, warnings)
        if poster and not created:
            filled.append('poster')
        return game, self._action(created, filled), game.name, {
            'filled': filled, 'conflicts': conflicts, 'poster': poster,
        }

    @staticmethod
    def _ids(entry, field):
        """Список id записей БД (целые числа)"""
        value = entry.get(field)
        if value is None:
            return set()
        if not isinstance(value, list) or any(
            isinstance(item, bool) or not isinstance(item, int) for item in value
        ):
            raise ItemError(f'{field}: ожидается список целых id')
        return set(value)

    def _poster(self, game, poster_url, warnings):
        """Скачать постер, если его нет. Возвращает 'saved', 'planned' или ''"""
        if not poster_url or game.poster:
            return ''
        if self.dry_run:
            return 'planned'
        try:
            extension, data = download_poster(poster_url)
        except PosterError as error:
            warnings.append(f'постер: {error}')
            return ''
        game.poster.save(f'import-{game.pk}.{extension}', ContentFile(data), save=True)
        self.saved_files.append(game.poster.name)
        return 'saved'

    def import_conventions(self, entry, warnings):
        name = self.required(entry, 'name')
        if len(name) > 255:
            raise ItemError('name: длиннее 255 символов')
        values = {
            'description': self.text(entry, 'description'),
            'source_url': self.url(entry, 'source_url', warnings),
        }
        links = self._link_specs(entry.get('links'), warnings)
        convention = self.convention_index.get(normalize_name(name))
        filled, conflicts = [], {}
        if convention is None:
            convention = Convention.objects.create(name=name, **values)
            self.convention_index[normalize_name(name)] = convention
            created = True
        else:
            created = False
            self.fill(convention, values, filled, conflicts)
            if filled:
                convention.save()
        existing = {normalize_url(link.url) for link in convention.links.all()}
        links_added = []
        for link in links:
            if normalize_url(link['url']) in existing:
                continue
            ConventionLink.objects.create(convention=convention, **link)
            existing.add(normalize_url(link['url']))
            links_added.append(link['url'])
        if links_added and not created:
            filled.append('links')
        return convention, self._action(created, filled), convention.name, {
            'filled': filled, 'conflicts': conflicts, 'links_added': links_added,
        }

    def _link_specs(self, links, warnings):
        if links is None:
            return []
        if not isinstance(links, list):
            raise ItemError('links: ожидается список')
        specs = []
        for link in links:
            if not isinstance(link, dict):
                raise ItemError('links: ссылка — объект {type, url, title}')
            url = self.url(link, 'url', warnings)
            if not url:
                continue
            link_type = self.text(link, 'type') or 'other'
            if link_type not in LINK_TYPES:
                warnings.append(f'links: тип «{link_type}» неизвестен — записан как other')
                link_type = 'other'
            specs.append({'url': url, 'link_type': link_type, 'title': self.text(link, 'title')[:100]})
        return specs

    def import_events(self, entry, warnings):
        convention = self.resolve('conventions', entry.get('convention'), required=True, field='convention')
        city = self.resolve('cities', entry.get('city'), required=True, field='city')
        venue = self.resolve('venues', entry.get('venue'), city=city, field='venue')
        if venue is not None and venue.city_id != city.pk:
            raise ItemError('venue: площадка в другом городе')
        date_start = self.date(entry, 'date_start')
        date_end = self.date(entry, 'date_end', required=False) or date_start
        if date_end < date_start:
            raise ItemError('date_end раньше date_start')
        source_url = self.url(entry, 'source_url', warnings)

        event = ConventionEvent.objects.filter(
            convention=convention, date_start=date_start,
        ).order_by('pk').first()
        filled, conflicts = [], {}
        if event is None:
            event = ConventionEvent.objects.create(
                convention=convention, city=city, venue=venue,
                date_start=date_start, date_end=date_end, source_url=source_url,
            )
            created = True
        else:
            created = False
            self.fill(event, {'venue': venue, 'source_url': source_url}, filled, conflicts)
            if event.city_id != city.pk:
                conflicts['city'] = {'db': event.city.name, 'bundle': city.name}
            if event.date_end != date_end:
                conflicts['date_end'] = {'db': _plain(event.date_end), 'bundle': _plain(date_end)}
            if filled:
                event.save()
        label = f'{convention.name} — {event.city.name}, {event.date_start.isoformat()}'
        return event, self._action(created, filled), label, {'filled': filled, 'conflicts': conflicts}

    def import_runs(self, entry, warnings):
        game = self.resolve('games', entry.get('game'), required=True, field='game')
        event = self.resolve('events', entry.get('event'), field='event')
        city = self.resolve('cities', entry.get('city'), field='city')
        if city is None:
            if event is None:
                raise ItemError('city: обязателен для прогона вне проведения')
            city = event.city
        venue = self.resolve('venues', entry.get('venue'), city=city, field='venue')
        if venue is None and event is not None:
            venue = event.venue
        date = self.local_datetime(entry, 'date_local', city.timezone)
        if event is not None:
            error = date_outside_event_error(date, event, 'прогона')
            if error:
                raise ItemError(error)
        duration = self.count(entry, 'duration', minimum=1)
        rooms = self._rooms(venue, entry.get('rooms'))

        run = Run.objects.filter(game=game, date=date, convention_event=event).order_by('pk').first()
        filled, conflicts = [], {}
        if run is None:
            run = Run.objects.create(
                game=game, date=date, city=city, convention_event=event,
                **({'duration': duration} if duration else {}),
            )
            if rooms:
                run.rooms.set(rooms)
            created = True
        else:
            created = False
            if duration and run.duration != duration:
                conflicts['duration'] = {'db': run.duration, 'bundle': duration}
            if run.city_id != city.pk:
                conflicts['city'] = {'db': run.city.name, 'bundle': city.name}
            current_rooms = list(run.rooms.all())
            if rooms and not current_rooms:
                run.rooms.set(rooms)
                filled.append('rooms')
            elif rooms and {room.pk for room in rooms} != {room.pk for room in current_rooms}:
                conflicts['rooms'] = {
                    'db': sorted(room.name for room in current_rooms),
                    'bundle': sorted(room.name for room in rooms),
                }
        local = date.astimezone(pytz.timezone(city.timezone)).strftime('%Y-%m-%d %H:%M')
        return run, self._action(created, filled), f'{game.name} — {city.name}, {local}', {
            'filled': filled, 'conflicts': conflicts,
        }

    def _rooms(self, venue, rooms):
        names = [name for name, _ in self._room_specs(rooms)]
        if not names:
            return []
        if venue is None:
            raise ItemError('rooms: не определена площадка (укажите venue или площадку проведения)')
        existing = {fold_city(room.name): room for room in venue.rooms.all()}
        missing = [name for name in names if fold_city(name) not in existing]
        if missing:
            raise ItemError(f'rooms: на площадке «{venue.name}» нет помещений: {", ".join(missing)}')
        return [existing[fold_city(name)] for name in names]

    def import_common_events(self, entry, warnings):
        event = self.resolve('events', entry.get('event'), required=True, field='event')
        name = self.required(entry, 'name')
        if len(name) > 255:
            raise ItemError('name: длиннее 255 символов')
        date = self.local_datetime(entry, 'date_local', event.city.timezone)
        error = date_outside_event_error(date, event, 'события')
        if error:
            raise ItemError(error)
        duration = self.count(entry, 'duration', minimum=1)
        description = self.text(entry, 'description')

        normalized = normalize_name(name)
        common = next(
            (item for item in event.common_events.filter(date=date).order_by('pk')
             if normalize_name(item.name) == normalized),
            None,
        )
        filled, conflicts = [], {}
        if common is None:
            common = CommonEvent.objects.create(
                convention_event=event, name=name, date=date, description=description,
                **({'duration': duration} if duration else {}),
            )
            created = True
        else:
            created = False
            self.fill(common, {'description': description}, filled, conflicts)
            if duration and common.duration != duration:
                conflicts['duration'] = {'db': common.duration, 'bundle': duration}
            if filled:
                common.save()
        return common, self._action(created, filled), f'{common.name} — {event}', {
            'filled': filled, 'conflicts': conflicts,
        }


def _plain(value):
    """Значение поля для JSON-отчёта"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value)


ACTION_MARKS = {'created': '+', 'filled': '~', 'unchanged': '=', 'error': '!'}
ACTION_TITLES = {'created': 'создано', 'filled': 'дополнено', 'unchanged': 'без изменений', 'error': 'ошибки'}


class Command(BaseCommand):
    help = 'Загружает JSON-набор (города, площадки, игры, конвенты, проведения, прогоны) идемпотентно'

    def add_arguments(self, parser):
        parser.add_argument('file', help='Путь к JSON-набору')
        parser.add_argument('--dry-run', action='store_true', help='Выполнить в транзакции и откатить')
        parser.add_argument('--source-tag', default='', help='Метка источника для отчёта и журнала изменений')

    def handle(self, *args, **options):
        path = options['file']
        try:
            with open(path, encoding='utf-8') as file:
                bundle = json.load(file)
        except FileNotFoundError:
            raise CommandError(f'Файл не найден: {path}')
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CommandError(f'Не удалось прочитать JSON: {error}')
        if not isinstance(bundle, dict):
            raise CommandError('Набор должен быть JSON-объектом с разделами')

        dry_run = options['dry_run']
        source_tag = options['source_tag'] or os.path.basename(path)
        importer = None
        try:
            with transaction.atomic():
                log_start = _last_log_entry_id()
                importer = Importer(bundle, dry_run=dry_run)
                report = importer.run()
                _tag_log_entries(log_start, source_tag)
                if dry_run:
                    transaction.set_rollback(True)
        except Exception:
            # Транзакция откатилась — сохранённые постеры больше ни к чему не привязаны
            if importer is not None:
                for name in importer.saved_files:
                    Game._meta.get_field('poster').storage.delete(name)
            raise

        result = {
            'dry_run': dry_run,
            'source_tag': source_tag,
            'summary': report.summary(),
            'errors': sum(1 for item in report.items if item['action'] == 'error'),
            'warnings': report.warnings,
            'items': report.items,
        }
        self._print_human(result)
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))

    def _print_human(self, result):
        """Журнал для человека — в stderr, чтобы stdout оставался валидным JSON"""
        write = lambda text='': self.stderr.write(text, style_func=lambda line: line)  # noqa: E731
        write('Пробный запуск (--dry-run): изменения откачены.' if result['dry_run'] else 'Импорт выполнен.')
        write(f'Источник: {result["source_tag"]}')
        for warning in result['warnings']:
            write(f'! {warning}')
        for section in SECTIONS:
            items = [item for item in result['items'] if item['section'] == section]
            if not items:
                continue
            write()
            write(f'{SECTION_TITLES[section]}:')
            for item in items:
                title = item.get('label') or item['key']
                suffix = f' (id {item["id"]})' if item.get('id') else ''
                write(f'  {ACTION_MARKS[item["action"]]} {title}{suffix}')
                if item.get('filled'):
                    write(f'      заполнено: {", ".join(item["filled"])}')
                for name in item.get('rooms_added', []):
                    write(f'      помещение: {name}')
                for url in item.get('links_added', []):
                    write(f'      ссылка: {url}')
                if item.get('poster') == 'planned':
                    write('      постер: будет скачан')
                elif item.get('poster') == 'saved':
                    write('      постер: сохранён')
                for field, values in item.get('conflicts', {}).items():
                    write(f'      не изменено {field}: в БД {values["db"]!r}, в наборе {values["bundle"]!r}')
                for message in item.get('errors', []):
                    write(f'      ошибка: {message}')
                for message in item.get('warnings', []):
                    write(f'      предупреждение: {message}')
        write()
        write('Итого:')
        for section, counts in result['summary'].items():
            parts = ', '.join(f'{ACTION_TITLES[action]} {count}' for action, count in counts.items())
            write(f'  {SECTION_TITLES[section]}: {parts}')
        if result['errors']:
            write(f'Записей с ошибками: {result["errors"]}')


def _last_log_entry_id():
    from auditlog.models import LogEntry
    return LogEntry.objects.order_by('-pk').values_list('pk', flat=True).first() or 0


def _tag_log_entries(after_id, source_tag):
    """Пометить записи журнала изменений, созданные импортом"""
    from auditlog.models import LogEntry
    LogEntry.objects.filter(pk__gt=after_id).update(additional_data={'import_bundle': source_tag})
