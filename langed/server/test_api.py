"""
Тесты API: пагинация, фильтры, приватность регистраций, число SQL-запросов на списки
"""
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    City, CommonEvent, Convention, ConventionEvent, ConventionEventRegistration,
    ConventionLink, Game, Region, Registration, Room, Run, Venue,
)
from .serializers import make_excerpt

User = get_user_model()

# Верхняя граница числа SQL-запросов на любой список (включая сессию и пользователя)
MAX_LIST_QUERIES = 8


def ids(response):
    """Идентификаторы объектов страницы списка в порядке выдачи"""
    return [item['id'] for item in response.data['results']]


class ApiTestCase(TestCase):
    """Общий набор данных для тестов API"""

    @classmethod
    def setUpTestData(cls):
        now = timezone.now()
        today = timezone.localdate()

        cls.master = User.objects.create(username='master', first_name='Мария', last_name='Мастер')
        cls.player = User.objects.create(username='player', first_name='Пётр', last_name='Игрок')
        cls.organizer = User.objects.create(username='organizer', email='org@example.com')
        cls.conv_organizer = User.objects.create(username='conv_organizer')
        cls.staff = User.objects.create(username='staff', is_staff=True)
        cls.stranger = User.objects.create(username='stranger')

        region = Region.objects.create(name='Регион')
        cls.moscow = City.objects.create(name='Москва', region=region)
        cls.kazan = City.objects.create(name='Казань')

        cls.venue = Venue.objects.create(name='Loft Alpha', address='ул. Ленина, 1', city=cls.moscow)
        cls.venue_kazan = Venue.objects.create(name='Beta Hall', address='Kremlin street', city=cls.kazan)
        cls.room = Room.objects.create(venue=cls.venue, name='Зал 1')
        cls.room_blackbox = Room.objects.create(venue=cls.venue, name='Зал 2', blackbox=True)

        cls.game = Game.objects.create(
            name='Alpha Station',
            announcement='слово ' * 100,
            red_flags='Красные флаги',
            players_max=4,
        )
        cls.game.creators.add(cls.master)
        cls.game_other = Game.objects.create(name='Beta Colony', announcement='Короткий анонс')
        cls.game_other.creators.add(cls.stranger)

        cls.convention = Convention.objects.create(name='Alpha Con', description='Описание')
        cls.convention.organizers.add(cls.conv_organizer)
        ConventionLink.objects.create(convention=cls.convention, url='https://example.com', link_type='website')
        cls.convention_other = Convention.objects.create(name='Beta Fest')

        cls.event = ConventionEvent.objects.create(
            convention=cls.convention, city=cls.moscow, venue=cls.venue,
            date_start=today + timedelta(days=10), date_end=today + timedelta(days=12),
            capacity=3, registration_open=True,
        )
        cls.event.organizers.add(cls.organizer)
        cls.event_past = ConventionEvent.objects.create(
            convention=cls.convention_other, city=cls.kazan,
            date_start=today - timedelta(days=30), date_end=today - timedelta(days=28),
        )
        cls.event_registration = ConventionEventRegistration.objects.create(
            convention_event=cls.event, user=cls.player, status='confirmed', comment='Буду'
        )
        ConventionEventRegistration.objects.create(
            convention_event=cls.event, user=cls.stranger, status='pending'
        )
        CommonEvent.objects.create(
            convention_event=cls.event, name='Ужин', date=now + timedelta(days=10, hours=5)
        )

        # Предстоящий прогон вне конвента
        cls.run_soon = Run.objects.create(game=cls.game, date=now + timedelta(days=2), city=cls.moscow)
        cls.run_soon.masters.add(cls.master)
        cls.run_soon.rooms.add(cls.room)
        # Предстоящий прогон на конвенте
        cls.run_convention = Run.objects.create(
            game=cls.game_other, date=now + timedelta(days=10), city=cls.moscow,
            convention_event=cls.event,
        )
        cls.run_convention.masters.add(cls.stranger)
        cls.run_convention.rooms.add(cls.room, cls.room_blackbox)
        # Прошедшие прогоны
        cls.run_past = Run.objects.create(game=cls.game, date=now - timedelta(days=5), city=cls.kazan)
        cls.run_past.masters.add(cls.master)
        cls.run_past_old = Run.objects.create(game=cls.game_other, date=now - timedelta(days=50), city=cls.kazan)
        cls.run_past_old.masters.add(cls.stranger)

        cls.registration = Registration.objects.create(
            run=cls.run_soon, user=cls.player, status='confirmed', comment='Хочу роль капитана'
        )
        Registration.objects.create(run=cls.run_soon, user=cls.stranger, status='pending')
        Registration.objects.create(run=cls.run_soon, user=cls.organizer, status='waitlist')
        Registration.objects.create(run=cls.run_soon, user=cls.conv_organizer, status='confirmed', is_technician=True)
        Registration.objects.create(run=cls.run_convention, user=cls.player, status='pending')

    def setUp(self):
        self.client = APIClient()

    def login(self, user):
        self.client.force_login(user)


class ExcerptTests(TestCase):
    """Выдержка из анонса"""

    def test_short_text_is_unchanged(self):
        self.assertEqual(make_excerpt('Короткий  анонс\nв две строки'), 'Короткий анонс в две строки')

    def test_long_text_is_cut_at_word_boundary(self):
        excerpt = make_excerpt('слово ' * 100)
        self.assertLessEqual(len(excerpt), 201)
        self.assertTrue(excerpt.endswith('слово…'))

    def test_word_is_not_broken(self):
        text = 'а' * 150 + ' ' + 'б' * 100
        self.assertEqual(make_excerpt(text), 'а' * 150 + '…')

    def test_empty_text(self):
        self.assertEqual(make_excerpt(''), '')
        self.assertEqual(make_excerpt(None), '')


class PaginationTests(ApiTestCase):
    """Постраничная выдача списков"""

    PAGINATED = ['/api/games/', '/api/runs/', '/api/conventions/', '/api/convention-events/', '/api/venues/']

    def test_paginated_lists_have_envelope(self):
        for url in self.PAGINATED:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(set(response.data), {'count', 'next', 'previous', 'results'})

    def test_unpaginated_lists(self):
        for url in ['/api/cities/', '/api/rooms/', '/api/convention-links/']:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertIsInstance(response.data, list)

    def test_default_page_size_and_pages(self):
        Game.objects.bulk_create([Game(name=f'Bulk {i:03d}') for i in range(30)])
        response = self.client.get('/api/games/')
        self.assertEqual(response.data['count'], 32)
        self.assertEqual(len(response.data['results']), 24)
        self.assertIn('page=2', response.data['next'])
        self.assertIsNone(response.data['previous'])

        second = self.client.get('/api/games/?page=2')
        self.assertEqual(len(second.data['results']), 8)
        self.assertIsNone(second.data['next'])
        self.assertFalse(set(ids(response)) & set(ids(second)))

    def test_page_size_param_and_limit(self):
        Game.objects.bulk_create([Game(name=f'Bulk {i:03d}') for i in range(120)])
        response = self.client.get('/api/games/?page_size=5')
        self.assertEqual(len(response.data['results']), 5)
        response = self.client.get('/api/games/?page_size=1000')
        self.assertEqual(len(response.data['results']), 100)

    def test_page_out_of_range(self):
        response = self.client.get('/api/games/?page=99')
        self.assertEqual(response.status_code, 404)


class GameApiTests(ApiTestCase):
    """Список и карточка игры"""

    def test_list_item_is_light(self):
        response = self.client.get('/api/games/')
        item = next(g for g in response.data['results'] if g['id'] == self.game.id)
        self.assertEqual(set(item), {
            'id', 'name', 'creators', 'poster', 'announcement_excerpt',
            'players_min', 'players_max', 'female_roles_min', 'female_roles_max',
            'male_roles_min', 'male_roles_max', 'technicians', 'can_edit',
        })
        self.assertLessEqual(len(item['announcement_excerpt']), 201)
        self.assertTrue(item['announcement_excerpt'].endswith('слово…'))
        self.assertEqual(item['creators'], [{'id': self.master.id, 'display_name': 'Мария Мастер'}])
        self.assertFalse(item['can_edit'])

    def test_short_announcement_excerpt_is_full(self):
        response = self.client.get('/api/games/')
        item = next(g for g in response.data['results'] if g['id'] == self.game_other.id)
        self.assertEqual(item['announcement_excerpt'], 'Короткий анонс')

    def test_detail_has_full_texts(self):
        response = self.client.get(f'/api/games/{self.game.id}/')
        self.assertEqual(response.data['announcement'], self.game.announcement)
        self.assertEqual(response.data['red_flags'], 'Красные флаги')
        self.assertNotIn('username', response.data['creators'][0])

    def test_can_edit(self):
        self.login(self.master)
        response = self.client.get('/api/games/')
        flags = {g['id']: g['can_edit'] for g in response.data['results']}
        self.assertEqual(flags, {self.game.id: True, self.game_other.id: False})
        self.login(self.staff)
        response = self.client.get('/api/games/')
        self.assertTrue(all(g['can_edit'] for g in response.data['results']))

    def test_poster_url_is_built_from_request(self):
        game = Game.objects.create(name='With poster', poster='games/posters/p.png')
        response = self.client.get('/api/games/?search=With poster')
        self.assertEqual(response.data['results'][0]['poster'], 'http://testserver/media/games/posters/p.png')
        response = self.client.get(f'/api/games/{game.id}/', secure=True)
        self.assertEqual(response.data['poster'], 'https://testserver/media/games/posters/p.png')
        self.assertEqual(response.data['poster_url'], 'https://testserver/media/games/posters/p.png')

    def test_search(self):
        response = self.client.get('/api/games/?search=alpha')
        self.assertEqual(ids(response), [self.game.id])
        response = self.client.get('/api/games/?search=nothing')
        self.assertEqual(response.data['count'], 0)

    def test_ordering(self):
        response = self.client.get('/api/games/?ordering=name')
        self.assertEqual(ids(response), [self.game.id, self.game_other.id])
        response = self.client.get('/api/games/?ordering=-name')
        self.assertEqual(ids(response), [self.game_other.id, self.game.id])
        Game.objects.filter(pk=self.game.pk).update(created_at=timezone.now() + timedelta(hours=1))
        response = self.client.get('/api/games/?ordering=-created_at')
        self.assertEqual(ids(response), [self.game.id, self.game_other.id])
        self.assertEqual(ids(self.client.get('/api/games/')), [self.game.id, self.game_other.id])
        response = self.client.get('/api/games/?ordering=created_at')
        self.assertEqual(ids(response), [self.game_other.id, self.game.id])

    def test_invalid_ordering(self):
        response = self.client.get('/api/games/?ordering=announcement')
        self.assertEqual(response.status_code, 400)

    def test_creator_filter(self):
        response = self.client.get(f'/api/games/?creator={self.stranger.id}')
        self.assertEqual(ids(response), [self.game_other.id])
        response = self.client.get('/api/games/?creator=abc')
        self.assertEqual(response.status_code, 400)

    def test_mine(self):
        response = self.client.get('/api/games/?mine=1')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['results'], [])
        self.login(self.master)
        response = self.client.get('/api/games/?mine=1')
        self.assertEqual(ids(response), [self.game.id])

    def test_filters_do_not_affect_detail(self):
        response = self.client.get(f'/api/games/{self.game.id}/?search=nothing&mine=1')
        self.assertEqual(response.status_code, 200)

    def test_only_creator_manages_creators(self):
        url = f'/api/games/{self.game.id}/add_creator/'
        self.assertEqual(self.client.post(url, {'username': 'stranger'}).status_code, 403)
        self.login(self.stranger)
        self.assertEqual(self.client.post(url, {'username': 'stranger'}).status_code, 403)
        self.login(self.master)
        response = self.client.post(url, {'username': 'stranger'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['creators']), 2)
        response = self.client.post(
            f'/api/games/{self.game.id}/remove_creator/', {'user_id': self.stranger.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['creators']), 1)


class RunListTests(ApiTestCase):
    """Фильтры и состав списка прогонов"""

    def test_default_is_upcoming_ascending(self):
        response = self.client.get('/api/runs/')
        self.assertEqual(ids(response), [self.run_soon.id, self.run_convention.id])
        self.assertEqual(ids(self.client.get('/api/runs/?time=upcoming')), ids(response))

    def test_past_is_descending(self):
        response = self.client.get('/api/runs/?time=past')
        self.assertEqual(ids(response), [self.run_past.id, self.run_past_old.id])

    def test_all(self):
        response = self.client.get('/api/runs/?time=all')
        self.assertEqual(ids(response), [
            self.run_convention.id, self.run_soon.id, self.run_past.id, self.run_past_old.id
        ])

    def test_invalid_params(self):
        self.assertEqual(self.client.get('/api/runs/?time=tomorrow').status_code, 400)
        self.assertEqual(self.client.get('/api/runs/?city=Москва').status_code, 400)

    def test_city_filter(self):
        response = self.client.get(f'/api/runs/?time=all&city={self.kazan.id}')
        self.assertEqual(ids(response), [self.run_past.id, self.run_past_old.id])
        response = self.client.get(f'/api/runs/?city={self.kazan.id}')
        self.assertEqual(ids(response), [])

    def test_game_filter(self):
        response = self.client.get(f'/api/runs/?time=all&game={self.game.id}')
        self.assertEqual(ids(response), [self.run_soon.id, self.run_past.id])

    def test_convention_event_filter(self):
        response = self.client.get(f'/api/runs/?convention_event={self.event.id}')
        self.assertEqual(ids(response), [self.run_convention.id])

    def test_standalone_filter(self):
        response = self.client.get('/api/runs/?standalone=1')
        self.assertEqual(ids(response), [self.run_soon.id])

    def test_master_filter(self):
        response = self.client.get(f'/api/runs/?time=all&master={self.master.id}')
        self.assertEqual(ids(response), [self.run_soon.id, self.run_past.id])

    def test_mine(self):
        response = self.client.get('/api/runs/?time=all&mine=1')
        self.assertEqual(response.data['count'], 0)
        # Мастер
        self.login(self.master)
        response = self.client.get('/api/runs/?time=all&mine=1')
        self.assertEqual(ids(response), [self.run_soon.id, self.run_past.id])
        # Игрок с регистрациями
        self.login(self.player)
        response = self.client.get('/api/runs/?time=all&mine=1')
        self.assertEqual(ids(response), [self.run_convention.id, self.run_soon.id])
        # Пользователь без прогонов и регистраций
        self.login(self.staff)
        response = self.client.get('/api/runs/?time=all&mine=1')
        self.assertEqual(ids(response), [])

    def test_filters_do_not_affect_detail(self):
        response = self.client.get(f'/api/runs/{self.run_past.id}/')
        self.assertEqual(response.status_code, 200)

    def test_list_item_shape(self):
        response = self.client.get('/api/runs/')
        item = response.data['results'][0]
        self.assertEqual(set(item), {
            'id', 'game', 'masters', 'date', 'date_local', 'duration',
            'city', 'city_id', 'city_timezone', 'rooms', 'venue_name',
            'convention_event', 'convention_name', 'max_players', 'registration_open',
            'registered_count', 'available_slots', 'is_full',
            'current_user_registration', 'effective_max_players',
            'can_edit', 'can_manage_registrations',
        })
        self.assertEqual(item['game'], {'id': self.game.id, 'name': 'Alpha Station', 'poster': None})
        self.assertEqual(item['masters'], [{'id': self.master.id, 'display_name': 'Мария Мастер'}])
        self.assertEqual(item['city'], 'Москва')
        self.assertEqual(item['city_id'], self.moscow.id)
        self.assertEqual(item['rooms'], [
            {'id': self.room.id, 'name': 'Зал 1', 'blackbox': False, 'venue_id': self.venue.id,
             'venue_name': 'Loft Alpha'}
        ])
        self.assertEqual(item['venue_name'], 'Loft Alpha')
        self.assertIsNone(item['convention_event'])
        self.assertIsNone(item['convention_name'])
        # confirmed + pending без игротехников и листа ожидания
        self.assertEqual(item['registered_count'], 2)
        self.assertEqual(item['effective_max_players'], 4)
        self.assertEqual(item['available_slots'], 2)
        self.assertFalse(item['is_full'])
        self.assertIsNone(item['current_user_registration'])
        self.assertFalse(item['can_edit'])
        self.assertFalse(item['can_manage_registrations'])

        convention_item = response.data['results'][1]
        self.assertEqual(convention_item['convention_event'], self.event.id)
        self.assertEqual(convention_item['convention_name'], 'Alpha Con')
        self.assertEqual(convention_item['registered_count'], 1)

    def test_is_full(self):
        Run.objects.filter(pk=self.run_soon.pk).update(max_players=2)
        item = self.client.get('/api/runs/').data['results'][0]
        self.assertEqual(item['available_slots'], 0)
        self.assertTrue(item['is_full'])

    def test_list_flags_for_users(self):
        def flags(user):
            self.login(user)
            return {
                item['id']: (item['can_edit'], item['can_manage_registrations'])
                for item in self.client.get('/api/runs/').data['results']
            }

        self.assertEqual(flags(self.master), {
            self.run_soon.id: (True, True), self.run_convention.id: (False, False)
        })
        self.assertEqual(flags(self.organizer), {
            self.run_soon.id: (False, False), self.run_convention.id: (True, True)
        })
        self.assertEqual(flags(self.conv_organizer), {
            self.run_soon.id: (False, False), self.run_convention.id: (True, True)
        })
        self.assertEqual(flags(self.staff), {
            self.run_soon.id: (True, True), self.run_convention.id: (True, True)
        })

    def test_cities_action(self):
        response = self.client.get('/api/runs/cities/')
        self.assertEqual(response.data, [
            {'id': self.kazan.id, 'name': 'Казань'}, {'id': self.moscow.id, 'name': 'Москва'}
        ])


class RunRegistrationPrivacyTests(ApiTestCase):
    """Данные о регистрациях видит только тот, кто ими управляет"""

    def assert_no_user_data(self, response):
        content = response.content.decode()
        self.assertNotIn('"username"', content)
        self.assertNotIn('"player"', content)
        self.assertNotIn('Пётр Игрок', content)
        self.assertNotIn('Хочу роль капитана', content)

    def test_anonymous_list_has_no_registrations(self):
        response = self.client.get('/api/runs/?time=all')
        for item in response.data['results']:
            self.assertNotIn('registrations', item)
            self.assertIsNone(item['current_user_registration'])
        self.assert_no_user_data(response)

    def test_master_list_has_no_registrations(self):
        self.login(self.master)
        response = self.client.get('/api/runs/?time=all')
        for item in response.data['results']:
            self.assertNotIn('registrations', item)

    def test_anonymous_detail_hides_registrations(self):
        response = self.client.get(f'/api/runs/{self.run_soon.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['registrations'])
        self.assertIsNone(response.data['current_user_registration'])
        self.assertEqual(response.data['registered_count'], 2)
        self.assertEqual(response.data['available_slots'], 2)
        self.assertFalse(response.data['can_manage_registrations'])
        self.assert_no_user_data(response)

    def test_player_sees_only_own_registration(self):
        self.login(self.player)
        response = self.client.get(f'/api/runs/{self.run_soon.id}/')
        self.assertIsNone(response.data['registrations'])
        own = response.data['current_user_registration']
        self.assertEqual(own['id'], self.registration.id)
        self.assertEqual(own['status'], 'confirmed')
        self.assertEqual(own['user']['id'], self.player.id)
        self.assertNotIn('"stranger"', response.content.decode())

        item = self.client.get('/api/runs/').data['results'][0]
        self.assertEqual(item['current_user_registration']['id'], self.registration.id)

    def test_master_sees_registrations(self):
        self.login(self.master)
        response = self.client.get(f'/api/runs/{self.run_soon.id}/')
        registrations = response.data['registrations']
        self.assertEqual(len(registrations), 4)
        first = registrations[0]
        self.assertEqual(first['user'], {
            'id': self.player.id, 'username': 'player', 'display_name': 'Пётр Игрок'
        })
        self.assertEqual(first['comment'], 'Хочу роль капитана')
        self.assertTrue(response.data['can_manage_registrations'])

    def test_master_of_other_run_does_not_see_registrations(self):
        self.login(self.master)
        response = self.client.get(f'/api/runs/{self.run_convention.id}/')
        self.assertIsNone(response.data['registrations'])

    def test_organizers_and_staff_see_convention_run_registrations(self):
        for user in (self.organizer, self.conv_organizer, self.staff, self.stranger):
            with self.subTest(user=user.username):
                self.login(user)
                response = self.client.get(f'/api/runs/{self.run_convention.id}/')
                self.assertEqual(len(response.data['registrations']), 1)

    def test_organizer_does_not_see_standalone_run_registrations(self):
        self.login(self.organizer)
        response = self.client.get(f'/api/runs/{self.run_soon.id}/')
        self.assertIsNone(response.data['registrations'])

    def test_registrations_action(self):
        url = f'/api/runs/{self.run_soon.id}/registrations/'
        self.assertEqual(self.client.get(url).status_code, 403)
        self.login(self.player)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.login(self.master)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 4)

    def test_register_response_hides_other_registrations(self):
        run = Run.objects.create(game=self.game, date=timezone.now() + timedelta(days=3), city=self.kazan)
        run.masters.add(self.master)
        self.login(self.staff)
        response = self.client.post(f'/api/runs/{run.id}/register/', {'comment': 'Иду'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['run']['registered_count'], 1)
        self.assertEqual(response.data['run']['current_user_registration']['status'], 'pending')

        self.login(self.player)
        response = self.client.post(f'/api/runs/{run.id}/register/', {})
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data['run']['registrations'])
        self.assertEqual(response.data['run']['registered_count'], 2)
        response = self.client.post(f'/api/runs/{run.id}/unregister/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['run']['registered_count'], 1)
        self.assertIsNone(response.data['run']['current_user_registration'])

    def test_update_registration(self):
        url = f'/api/runs/{self.run_soon.id}/update_registration/'
        data = {'registration_id': self.registration.id, 'status': 'cancelled'}
        self.login(self.player)
        self.assertEqual(self.client.post(url, data).status_code, 403)
        self.login(self.master)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['registration']['status'], 'cancelled')
        self.assertEqual(response.data['run']['registered_count'], 1)

    def test_only_master_manages_masters(self):
        url = f'/api/runs/{self.run_soon.id}/add_master/'
        self.assertEqual(self.client.post(url, {'username': 'player'}).status_code, 403)
        self.login(self.player)
        self.assertEqual(self.client.post(url, {'username': 'player'}).status_code, 403)
        self.assertIsNone(self.client.get(f'/api/runs/{self.run_soon.id}/').data['registrations'])
        self.login(self.master)
        response = self.client.post(url, {'username': 'stranger'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['masters']), 2)
        response = self.client.post(
            f'/api/runs/{self.run_soon.id}/remove_master/', {'user_id': self.stranger.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['masters']), 1)

    def test_schedule_has_no_user_data(self):
        response = self.client.get(f'/api/convention-events/{self.event.id}/schedule/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('registrations', response.data['runs'][0])
        self.assert_no_user_data(response)


class ConventionEventApiTests(ApiTestCase):
    """Список, карточка и расписание проведения конвента"""

    def test_default_is_all_descending(self):
        response = self.client.get('/api/convention-events/')
        self.assertEqual(ids(response), [self.event.id, self.event_past.id])
        self.assertEqual(ids(self.client.get('/api/convention-events/?time=all')), ids(response))

    def test_time_filter(self):
        response = self.client.get('/api/convention-events/?time=upcoming')
        self.assertEqual(ids(response), [self.event.id])
        response = self.client.get('/api/convention-events/?time=past')
        self.assertEqual(ids(response), [self.event_past.id])
        self.assertEqual(self.client.get('/api/convention-events/?time=x').status_code, 400)

    def test_event_ending_today_is_upcoming(self):
        today = timezone.localdate()
        ConventionEvent.objects.filter(pk=self.event_past.pk).update(
            date_start=today - timedelta(days=1), date_end=today
        )
        response = self.client.get('/api/convention-events/?time=upcoming')
        self.assertEqual(ids(response), [self.event_past.id, self.event.id])

    def test_city_filter(self):
        response = self.client.get(f'/api/convention-events/?city={self.kazan.id}')
        self.assertEqual(ids(response), [self.event_past.id])

    def test_convention_filter(self):
        response = self.client.get(f'/api/convention-events/?convention={self.convention.id}')
        self.assertEqual(ids(response), [self.event.id])

    def test_mine(self):
        self.assertEqual(self.client.get('/api/convention-events/?mine=1').data['count'], 0)
        for user in (self.organizer, self.conv_organizer, self.player):
            with self.subTest(user=user.username):
                self.login(user)
                response = self.client.get('/api/convention-events/?mine=1')
                self.assertEqual(ids(response), [self.event.id])
        self.login(self.master)
        self.assertEqual(ids(self.client.get('/api/convention-events/?mine=1')), [])

    def test_list_item_shape(self):
        response = self.client.get('/api/convention-events/')
        item = response.data['results'][0]
        self.assertEqual(set(item), {
            'id', 'convention', 'convention_name', 'city', 'city_name',
            'venue', 'venue_name', 'date_start', 'date_end',
            'capacity', 'registration_open', 'runs_count',
            'registrations_count', 'pending_registrations_count',
            'available_slots', 'is_full', 'current_user_registration', 'can_edit',
        })
        self.assertEqual(item['convention'], self.convention.id)
        self.assertEqual(item['convention_name'], 'Alpha Con')
        self.assertEqual(item['city']['id'], self.moscow.id)
        self.assertEqual(item['city']['region'], {'id': self.moscow.region_id, 'name': 'Регион'})
        self.assertEqual(item['venue'], {'id': self.venue.id, 'name': 'Loft Alpha', 'address': 'ул. Ленина, 1'})
        self.assertEqual(item['runs_count'], 1)
        self.assertEqual(item['registrations_count'], 1)
        self.assertEqual(item['pending_registrations_count'], 1)
        self.assertEqual(item['available_slots'], 2)
        self.assertFalse(item['is_full'])
        self.assertIsNone(item['current_user_registration'])
        self.assertFalse(item['can_edit'])

        past = response.data['results'][1]
        self.assertIsNone(past['venue'])
        self.assertIsNone(past['venue_name'])
        self.assertIsNone(past['capacity'])
        self.assertIsNone(past['available_slots'])
        self.assertEqual(past['runs_count'], 0)

    def test_list_flags_for_users(self):
        def flags(user):
            self.login(user)
            return {
                item['id']: item['can_edit']
                for item in self.client.get('/api/convention-events/').data['results']
            }

        self.assertEqual(flags(self.organizer), {self.event.id: True, self.event_past.id: False})
        self.assertEqual(flags(self.conv_organizer), {self.event.id: True, self.event_past.id: False})
        self.assertEqual(flags(self.player), {self.event.id: False, self.event_past.id: False})
        self.assertEqual(flags(self.staff), {self.event.id: True, self.event_past.id: True})

    def test_current_user_registration(self):
        self.login(self.player)
        item = self.client.get('/api/convention-events/').data['results'][0]
        own = item['current_user_registration']
        self.assertEqual(own['id'], self.event_registration.id)
        self.assertEqual(own['status'], 'confirmed')
        detail = self.client.get(f'/api/convention-events/{self.event.id}/')
        self.assertEqual(detail.data['current_user_registration']['id'], self.event_registration.id)

    def test_detail(self):
        response = self.client.get(f'/api/convention-events/{self.event.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['runs'][0]['id'], self.run_convention.id)
        self.assertEqual(response.data['games'][0]['id'], self.game_other.id)
        self.assertEqual(response.data['runs_count'], 1)
        self.assertEqual(response.data['registrations_count'], 1)
        self.assertEqual(response.data['organizers'], [{'id': self.organizer.id, 'display_name': 'organizer'}])
        self.assertNotIn('"username"', response.content.decode())
        self.assertNotIn('org@example.com', response.content.decode())

    def test_registrations_action_is_for_organizers(self):
        url = f'/api/convention-events/{self.event.id}/registrations/'
        self.assertEqual(self.client.get(url).status_code, 403)
        self.login(self.player)
        self.assertEqual(self.client.get(url).status_code, 403)
        for user in (self.organizer, self.conv_organizer, self.staff):
            with self.subTest(user=user.username):
                self.login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.data), 2)
                self.assertEqual(response.data[0]['user']['username'], 'player')
                self.assertEqual(response.data[0]['comment'], 'Буду')

    def test_schedule_is_single_request(self):
        response = self.client.get(f'/api/convention-events/{self.event.id}/schedule/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['convention_name'], 'Alpha Con')
        self.assertEqual(len(response.data['common_events']), 1)
        self.assertEqual(len(response.data['venue_rooms']), 2)
        self.assertEqual(response.data['venues'], [
            {'id': self.venue.id, 'name': 'Loft Alpha', 'address': 'ул. Ленина, 1'}
        ])
        self.assertEqual(response.data['games'][0]['id'], self.game_other.id)
        run = response.data['runs'][0]
        self.assertEqual(run['id'], self.run_convention.id)
        self.assertEqual(run['registered_count'], 1)
        self.assertEqual(len(run['rooms']), 2)
        self.assertEqual(run['masters'], [{'id': self.stranger.id, 'display_name': 'stranger'}])
        self.assertFalse(run['can_edit'])

        self.login(self.organizer)
        response = self.client.get(f'/api/convention-events/{self.event.id}/schedule/')
        self.assertTrue(response.data['can_edit'])
        self.assertTrue(response.data['runs'][0]['can_edit'])
        self.assertTrue(response.data['runs'][0]['can_manage_registrations'])
        self.assertTrue(response.data['common_events'][0]['can_edit'])

    def test_cities_action(self):
        response = self.client.get('/api/convention-events/cities/')
        self.assertEqual(response.data, [
            {'id': self.kazan.id, 'name': 'Казань'}, {'id': self.moscow.id, 'name': 'Москва'}
        ])


class ConventionAndVenueApiTests(ApiTestCase):
    """Конвенты и площадки"""

    def test_convention_search(self):
        response = self.client.get('/api/conventions/?search=alpha')
        self.assertEqual(ids(response), [self.convention.id])

    def test_convention_item(self):
        response = self.client.get('/api/conventions/')
        self.assertEqual(ids(response), [self.convention.id, self.convention_other.id])
        item = response.data['results'][0]
        self.assertEqual(item['events_count'], 1)
        self.assertEqual(len(item['links']), 1)
        self.assertEqual(item['organizers'], [{'id': self.conv_organizer.id, 'display_name': 'conv_organizer'}])
        detail = self.client.get(f'/api/conventions/{self.convention.id}/')
        self.assertEqual(detail.data['events_count'], 1)

    def test_only_organizer_manages_organizers(self):
        url = f'/api/conventions/{self.convention.id}/add_organizer/'
        self.assertEqual(self.client.post(url, {'username': 'player'}).status_code, 403)
        self.login(self.player)
        self.assertEqual(self.client.post(url, {'username': 'player'}).status_code, 403)
        self.login(self.conv_organizer)
        self.assertEqual(self.client.post(url, {'username': 'player'}).status_code, 200)

    def test_venue_search(self):
        self.assertEqual(ids(self.client.get('/api/venues/?search=loft')), [self.venue.id])
        self.assertEqual(ids(self.client.get('/api/venues/?search=kremlin')), [self.venue_kazan.id])

    def test_venue_city_filter(self):
        response = self.client.get(f'/api/venues/?city={self.kazan.id}')
        self.assertEqual(ids(response), [self.venue_kazan.id])
        self.assertEqual(self.client.get('/api/venues/?city=x').status_code, 400)

    def test_venue_item(self):
        response = self.client.get('/api/venues/')
        self.assertEqual(ids(response), [self.venue_kazan.id, self.venue.id])
        item = response.data['results'][1]
        self.assertEqual(item['city']['name'], 'Москва')
        self.assertEqual(item['rooms'], [
            {'id': self.room.id, 'name': 'Зал 1', 'blackbox': False, 'venue_id': self.venue.id,
             'venue_name': 'Loft Alpha'},
            {'id': self.room_blackbox.id, 'name': 'Зал 2', 'blackbox': True, 'venue_id': self.venue.id,
             'venue_name': 'Loft Alpha'},
        ])


class QueryCountTests(ApiTestCase):
    """Число SQL-запросов на список не зависит от числа объектов"""

    LIST_URLS = [
        '/api/games/?page_size=100',
        '/api/runs/?time=all&page_size=100',
        '/api/runs/?time=all&mine=1&page_size=100',
        '/api/conventions/?page_size=100',
        '/api/convention-events/?page_size=100',
        '/api/convention-events/?mine=1&page_size=100',
        '/api/venues/?page_size=100',
    ]

    def add_objects(self, count, prefix):
        """Добавляет count объектов каждого вида со всеми связями"""
        now = timezone.now()
        today = timezone.localdate()
        users = [User.objects.create(username=f'{prefix}_user_{i}') for i in range(4)]
        for i in range(count):
            venue = Venue.objects.create(name=f'{prefix} venue {i}', city=self.moscow)
            rooms = [Room.objects.create(venue=venue, name=f'Комната {k}') for k in range(2)]
            convention = Convention.objects.create(name=f'{prefix} convention {i}')
            convention.organizers.add(users[0], self.conv_organizer)
            ConventionLink.objects.create(convention=convention, url='https://example.com')
            event = ConventionEvent.objects.create(
                convention=convention, city=self.moscow, venue=venue,
                date_start=today + timedelta(days=3), date_end=today + timedelta(days=4), capacity=10,
            )
            event.organizers.add(users[1], self.organizer)
            game = Game.objects.create(name=f'{prefix} game {i}', announcement='слово ' * 300)
            game.creators.add(users[0], users[1])
            for user in users[2:] + [self.player]:
                ConventionEventRegistration.objects.create(convention_event=event, user=user, status='confirmed')
            for k in range(2):
                run = Run.objects.create(
                    game=game, date=now + timedelta(days=3, hours=k), city=self.moscow,
                    convention_event=event if k else None,
                )
                run.masters.add(users[k], self.master)
                run.rooms.add(*rooms)
                for user in users[2:] + [self.player]:
                    Registration.objects.create(run=run, user=user, status='confirmed')

    def count_queries(self, url):
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return len(context), response

    def test_list_queries_do_not_grow(self):
        clients = [None, self.player, self.master, self.organizer, self.conv_organizer, self.staff]
        self.add_objects(3, 'first')
        before = {}
        for user in clients:
            self.client = APIClient()
            if user:
                self.login(user)
            for url in self.LIST_URLS:
                before[(user, url)] = self.count_queries(url)[0]

        self.add_objects(20, 'second')
        for user in clients:
            self.client = APIClient()
            if user:
                self.login(user)
            for url in self.LIST_URLS:
                with self.subTest(user=getattr(user, 'username', 'anonymous'), url=url):
                    queries, response = self.count_queries(url)
                    self.assertEqual(queries, before[(user, url)])
                    self.assertLessEqual(queries, MAX_LIST_QUERIES)
                    if 'mine' not in url:
                        self.assertGreater(len(response.data['results']), 20)

    def test_anonymous_list_query_counts(self):
        self.add_objects(5, 'bulk')
        expected = {
            '/api/games/': 3,              # count, игры, авторы
            '/api/runs/?time=all': 4,      # count, прогоны, мастера, помещения
            '/api/conventions/': 4,        # count, конвенты, организаторы, ссылки
            '/api/convention-events/': 2,  # count, проведения
            '/api/venues/': 3,             # count, площадки, помещения
        }
        for url, queries in expected.items():
            with self.subTest(url=url):
                with self.assertNumQueries(queries):
                    self.client.get(url)

    def test_schedule_queries_do_not_grow(self):
        url = f'/api/convention-events/{self.event.id}/schedule/'
        for user in (None, self.organizer, self.player):
            with self.subTest(user=getattr(user, 'username', 'anonymous')):
                self.client = APIClient()
                if user:
                    self.login(user)
                before, _ = self.count_queries(url)
                now = timezone.now()
                for i in range(15):
                    run = Run.objects.create(
                        game=self.game, date=now + timedelta(days=11, hours=i), city=self.moscow,
                        convention_event=self.event,
                    )
                    run.masters.add(self.master, self.stranger)
                    run.rooms.add(self.room, self.room_blackbox)
                    Registration.objects.create(run=run, user=self.player, status='confirmed')
                    CommonEvent.objects.create(
                        convention_event=self.event, name=f'Событие {i}', date=now + timedelta(days=11)
                    )
                after, response = self.count_queries(url)
                self.assertEqual(after, before)
                self.assertGreater(len(response.data['runs']), 15)


class DateFormatTests(ApiTestCase):
    """date отдаётся в UTC с суффиксом Z, date_local — локальное время города без таймзоны"""

    def assert_utc(self, value, expected):
        self.assertTrue(value.endswith('Z'), value)
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        self.assertEqual(parsed, expected.astimezone(dt_timezone.utc))

    def test_run_dates(self):
        item = self.client.get('/api/runs/').data['results'][0]
        self.assert_utc(item['date'], self.run_soon.date)
        self.assertNotIn('Z', item['date_local'])
        self.assertNotIn('+', item['date_local'])
        detail = self.client.get(f'/api/runs/{self.run_soon.id}/').data
        self.assertEqual(detail['date'], item['date'])
        self.assertEqual(detail['date_local'], item['date_local'])

    def test_schedule_and_event_dates(self):
        schedule = self.client.get(f'/api/convention-events/{self.event.id}/schedule/').data
        self.assert_utc(schedule['runs'][0]['date'], self.run_convention.date)
        self.assertTrue(schedule['common_events'][0]['date'].endswith('Z'))
        detail = self.client.get(f'/api/convention-events/{self.event.id}/').data
        self.assert_utc(detail['runs'][0]['date'], self.run_convention.date)

    def test_naive_input_is_city_local_time(self):
        self.login(self.master)
        response = self.client.post('/api/runs/', {
            'game_id': self.game.id, 'city_id': self.moscow.id, 'date': '2027-01-15T19:00:00',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['date'], '2027-01-15T16:00:00Z')
        self.assertEqual(response.data['date_local'], '2027-01-15T19:00:00')
        # Значение из ответа можно отправить обратно без изменения момента времени
        response = self.client.patch(
            f"/api/runs/{response.data['id']}/", {'date': response.data['date']}, format='json'
        )
        self.assertEqual(response.data['date'], '2027-01-15T16:00:00Z')


class WritePermissionTests(ApiTestCase):
    """Права на запись и обязательные поля"""

    def event_payload(self, **extra):
        payload = {
            'convention_id': self.convention.id, 'city_id': self.kazan.id,
            'date_start': '2027-02-01', 'date_end': '2027-02-02',
        }
        payload.update(extra)
        return payload

    def test_event_requires_convention_and_city(self):
        self.login(self.staff)
        response = self.client.post(
            '/api/convention-events/', {'date_start': '2027-02-01', 'date_end': '2027-02-02'}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('convention_id', response.data)
        self.assertIn('city_id', response.data)
        # Частичное обновление по-прежнему не требует этих полей
        response = self.client.patch(f'/api/convention-events/{self.event.id}/', {'capacity': 5}, format='json')
        self.assertEqual(response.status_code, 200)

    def test_event_create_is_for_convention_organizers(self):
        url = '/api/convention-events/'
        self.assertEqual(self.client.post(url, self.event_payload(), format='json').status_code, 403)
        for user in (self.player, self.organizer):
            self.login(user)
            self.assertEqual(self.client.post(url, self.event_payload(), format='json').status_code, 403)
        self.login(self.conv_organizer)
        response = self.client.post(url, self.event_payload(), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['organizers'][0]['id'], self.conv_organizer.id)
        self.login(self.staff)
        self.assertEqual(self.client.post(url, self.event_payload(), format='json').status_code, 201)

    def test_event_cannot_be_moved_to_foreign_convention(self):
        self.login(self.organizer)
        response = self.client.patch(
            f'/api/convention-events/{self.event.id}/', {'convention_id': self.convention_other.id}, format='json'
        )
        self.assertEqual(response.status_code, 403)

    def run_payload(self, **extra):
        local = datetime.combine(self.event.date_start, datetime.min.time()).replace(hour=15)
        payload = {'game_id': self.game.id, 'city_id': self.moscow.id, 'date': local.isoformat()}
        payload.update(extra)
        return payload

    def test_run_in_convention_is_for_organizers(self):
        payload = self.run_payload(convention_event_id=self.event.id)
        self.login(self.master)
        self.assertEqual(self.client.post('/api/runs/', payload, format='json').status_code, 403)
        # Вне конвента прогон может создать любой авторизованный
        response = self.client.post('/api/runs/', self.run_payload(), format='json')
        self.assertEqual(response.status_code, 201)
        run_id = response.data['id']
        # Перенести свой прогон в чужое расписание нельзя
        response = self.client.patch(
            f'/api/runs/{run_id}/', {'convention_event_id': self.event.id}, format='json'
        )
        self.assertEqual(response.status_code, 403)
        for user in (self.organizer, self.conv_organizer, self.staff):
            with self.subTest(user=user.username):
                self.login(user)
                response = self.client.post('/api/runs/', payload, format='json')
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.data['convention_event'], self.event.id)
        response = self.client.patch(
            f'/api/runs/{run_id}/', {'convention_event_id': self.event.id}, format='json'
        )
        self.assertEqual(response.status_code, 200)

    def test_run_edit_is_for_masters_and_organizers(self):
        url = f'/api/runs/{self.run_convention.id}/'
        self.login(self.player)
        self.assertEqual(self.client.patch(url, {'duration': 100}, format='json').status_code, 403)
        self.login(self.master)
        self.assertEqual(self.client.patch(url, {'duration': 100}, format='json').status_code, 403)
        for user in (self.stranger, self.organizer, self.conv_organizer, self.staff):
            with self.subTest(user=user.username):
                self.login(user)
                self.assertTrue(self.client.get(url).data['can_edit'])
                response = self.client.patch(url, {'duration': 100}, format='json')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['duration'], 100)
        # Организатор конвента не управляет прогонами вне своего конвента
        self.login(self.organizer)
        standalone = f'/api/runs/{self.run_soon.id}/'
        self.assertFalse(self.client.get(standalone).data['can_edit'])
        self.assertEqual(self.client.patch(standalone, {'duration': 100}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(standalone).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_dictionaries_delete_is_for_staff(self):
        self.login(self.player)
        city = self.client.post('/api/cities/', {'name': 'Тверь'}, format='json')
        self.assertEqual(city.status_code, 201)
        venue = self.client.post('/api/venues/', {'name': 'Клуб', 'city_id': city.data['id']}, format='json')
        self.assertEqual(venue.status_code, 201)
        room = self.client.post('/api/rooms/', {'name': 'Зал', 'venue_id': venue.data['id']}, format='json')
        self.assertEqual(room.status_code, 201)
        response = self.client.patch(f"/api/venues/{venue.data['id']}/", {'address': 'Адрес'}, format='json')
        self.assertEqual(response.status_code, 200)
        urls = [
            f"/api/rooms/{room.data['id']}/", f"/api/venues/{venue.data['id']}/", f"/api/cities/{city.data['id']}/",
        ]
        for url in urls:
            self.assertEqual(self.client.delete(url).status_code, 403)
        self.login(self.staff)
        for url in urls:
            self.assertEqual(self.client.delete(url).status_code, 204)

    def test_import_csv_is_for_staff(self):
        def games_file():
            return SimpleUploadedFile('games.csv', 'Название,Анонс,Красные флаги\nИмпорт,Текст,\n'.encode())

        def conventions_file():
            return SimpleUploadedFile(
                'c.csv', 'Название мероприятия,Город,Дата начала,Дата конца\nКон,Москва,01.02.2027,02.02.2027\n'.encode()
            )

        self.login(self.master)
        response = self.client.post('/api/games/import_csv/', {'file': games_file()}, format='multipart')
        self.assertEqual(response.status_code, 403)
        response = self.client.post('/api/conventions/import_csv/', {'file': conventions_file()}, format='multipart')
        self.assertEqual(response.status_code, 403)
        self.login(self.staff)
        response = self.client.post('/api/games/import_csv/', {'file': games_file()}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 1)
        response = self.client.post('/api/conventions/import_csv/', {'file': conventions_file()}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['events_created'], 1)

    def test_parent_ids_are_readable(self):
        room = next(r for r in self.client.get('/api/rooms/').data if r['id'] == self.room.id)
        self.assertEqual(room['venue_id'], self.venue.id)
        link = self.client.get('/api/convention-links/').data[0]
        self.assertEqual(link['convention_id'], self.convention.id)


class UserSearchTests(ApiTestCase):
    """Поиск пользователей не раскрывает email"""

    def test_email_is_for_staff_only(self):
        self.login(self.player)
        response = self.client.get('/api/users/search/?q=organ')
        self.assertEqual(
            sorted(u['username'] for u in response.data), ['conv_organizer', 'organizer']
        )
        for user in response.data:
            self.assertEqual(set(user), {'id', 'username', 'display_name'})
        self.login(self.staff)
        response = self.client.get('/api/users/search/?q=organizer')
        emails = {u['username']: u['email'] for u in response.data}
        self.assertEqual(emails['organizer'], 'org@example.com')

    def test_email_search_is_exact_only(self):
        self.login(self.player)
        self.assertEqual(self.client.get('/api/users/search/?q=example.com').data, [])
        self.assertEqual(self.client.get('/api/users/search/?q=org@').data, [])
        response = self.client.get('/api/users/search/?q=ORG@example.com')
        self.assertEqual([u['username'] for u in response.data], ['organizer'])


class EventDateRangeTests(ApiTestCase):
    """Дата прогона и события сверяется с датами проведения в часовом поясе города"""

    def local(self, day, time):
        return f'{day.isoformat()}T{time}'

    def test_add_run_uses_city_timezone(self):
        self.login(self.organizer)
        url = f'/api/convention-events/{self.event.id}/add_run/'
        # 00:30 по Москве в первый день — в UTC это ещё предыдущие сутки
        response = self.client.post(
            url, {'game_id': self.game.id, 'date': self.local(self.event.date_start, '00:30:00')}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['date_local'], self.local(self.event.date_start, '00:30:00'))
        run_id = response.data['id']
        response = self.client.post(
            url, {'game_id': self.game.id, 'date': self.local(self.event.date_end, '23:30:00')}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        # 00:30 следующего дня по Москве — в UTC это ещё последний день конвента
        after = self.event.date_end + timedelta(days=1)
        response = self.client.post(
            url, {'game_id': self.game.id, 'date': self.local(after, '00:30:00')}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(after.strftime('%d.%m.%Y'), response.data['date'][0])

        update_url = f'/api/convention-events/{self.event.id}/update_run/'
        response = self.client.patch(
            update_url, {'run_id': run_id, 'date': self.local(after, '00:30:00')}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            update_url, {'run_id': run_id, 'date': self.local(self.event.date_start, '01:00:00')}, format='json'
        )
        self.assertEqual(response.status_code, 200)

    def test_run_api_uses_city_timezone(self):
        self.login(self.organizer)
        payload = {'game_id': self.game.id, 'city_id': self.moscow.id, 'convention_event_id': self.event.id}
        response = self.client.post(
            '/api/runs/', {**payload, 'date': self.local(self.event.date_start, '00:30:00')}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        before = self.event.date_start - timedelta(days=1)
        response = self.client.post(
            '/api/runs/', {**payload, 'date': self.local(before, '23:30:00')}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('date', response.data)

    def test_common_event_uses_city_timezone(self):
        self.login(self.organizer)
        url = f'/api/convention-events/{self.event.id}/add_common_event/'
        response = self.client.post(
            url, {'name': 'Заезд', 'date': self.local(self.event.date_start, '00:30:00')}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        common_event_id = response.data['id']
        after = self.event.date_end + timedelta(days=1)
        response = self.client.post(url, {'name': 'Отъезд', 'date': self.local(after, '00:30:00')}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(
            f'/api/convention-events/{self.event.id}/update_common_event/',
            {'common_event_id': common_event_id, 'date': self.local(after, '00:30:00')}, format='json'
        )
        self.assertEqual(response.status_code, 400)


class PastRegistrationTests(ApiTestCase):
    """Нельзя зарегистрироваться на прошедший прогон и завершившееся проведение"""

    def test_past_run(self):
        self.login(self.staff)
        response = self.client.post(f'/api/runs/{self.run_past.id}/register/', {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {'error': 'Прогон уже прошёл', 'code': 'run_past'})
        self.assertFalse(Registration.objects.filter(run=self.run_past).exists())

    def test_finished_event(self):
        ConventionEvent.objects.filter(pk=self.event_past.pk).update(registration_open=True)
        self.login(self.staff)
        response = self.client.post(f'/api/convention-events/{self.event_past.id}/register/', {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data, {'error': 'Конвент уже завершился', 'code': 'event_past'})

    def test_event_ending_today_accepts_registration(self):
        today = timezone.localdate()
        ConventionEvent.objects.filter(pk=self.event_past.pk).update(
            registration_open=True, date_start=today - timedelta(days=1), date_end=today + timedelta(days=1)
        )
        self.login(self.staff)
        response = self.client.post(f'/api/convention-events/{self.event_past.id}/register/', {})
        self.assertEqual(response.status_code, 201)


def png_file(name='poster.png', size=(4, 4), image_format='PNG'):
    """Настоящее изображение заданного формата для загрузки постера"""
    import io
    from PIL import Image
    buffer = io.BytesIO()
    Image.new('RGB', size, 'white').save(buffer, image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='application/octet-stream')


class ScheduleDeleteTests(ApiTestCase):
    """Удаление из расписания отвечает 204 без тела"""

    def test_remove_run_has_no_body(self):
        self.login(self.organizer)
        response = self.client.delete(
            f'/api/convention-events/{self.event.id}/remove_run/?run_id={self.run_convention.id}'
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertFalse(Run.objects.filter(pk=self.run_convention.pk).exists())

    def test_remove_common_event_has_no_body(self):
        common_event = CommonEvent.objects.get(convention_event=self.event)
        self.login(self.organizer)
        response = self.client.delete(
            f'/api/convention-events/{self.event.id}/remove_common_event/?common_event_id={common_event.id}'
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertFalse(CommonEvent.objects.filter(pk=common_event.pk).exists())


class EventVenueFilterTests(ApiTestCase):
    def test_venue_filter(self):
        response = self.client.get(f'/api/convention-events/?venue={self.venue.id}')
        self.assertEqual(ids(response), [self.event.id])
        response = self.client.get(f'/api/convention-events/?venue={self.venue_kazan.id}')
        self.assertEqual(ids(response), [])
        self.assertEqual(self.client.get('/api/convention-events/?venue=abc').status_code, 400)


class RejectedRegistrationTests(ApiTestCase):
    """Статус «Отклонена» заявки на прогон"""

    def test_reject_frees_slot_and_allows_reapply(self):
        url = f'/api/runs/{self.run_soon.id}/update_registration/'
        self.login(self.master)
        response = self.client.post(url, {'registration_id': self.registration.id, 'status': 'rejected'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['registration']['status'], 'rejected')
        self.assertEqual(response.data['registration']['status_display'], 'Отклонена')
        # Отклонённая заявка не занимает место
        self.assertEqual(response.data['run']['registered_count'], 1)

        # Игрок видит статус; повторная заявка — только после удаления отклонённой
        self.login(self.player)
        response = self.client.get(f'/api/runs/{self.run_soon.id}/')
        self.assertEqual(response.data['current_user_registration']['status'], 'rejected')
        response = self.client.post(f'/api/runs/{self.run_soon.id}/register/', {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], 'already_registered')
        self.assertEqual(self.client.post(f'/api/runs/{self.run_soon.id}/unregister/').status_code, 200)
        response = self.client.post(f'/api/runs/{self.run_soon.id}/register/', {})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['registration']['status'], 'pending')

    def test_unknown_status(self):
        self.login(self.master)
        response = self.client.post(
            f'/api/runs/{self.run_soon.id}/update_registration/',
            {'registration_id': self.registration.id, 'status': 'declined'},
        )
        self.assertEqual(response.status_code, 400)


class RegisterErrorCodeTests(ApiTestCase):
    """Машинные коды отказа в регистрации"""

    def assert_code(self, url, code):
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['code'], code)
        self.assertTrue(response.data['error'])

    def test_run_codes(self):
        url = f'/api/runs/{self.run_soon.id}/register/'
        self.login(self.master)
        self.assert_code(url, 'is_master')
        self.login(self.player)
        self.assert_code(url, 'already_registered')
        self.login(self.staff)
        self.assert_code(f'/api/runs/{self.run_past.id}/register/', 'run_past')
        self.assert_code(f'/api/runs/{self.run_convention.id}/register/', 'event_registration_required')
        Run.objects.filter(pk=self.run_soon.pk).update(registration_open=False)
        self.assert_code(url, 'registration_closed')

    def test_event_codes(self):
        url = f'/api/convention-events/{self.event.id}/register/'
        self.login(self.player)
        self.assert_code(url, 'already_registered')
        self.login(self.staff)
        self.assert_code(f'/api/convention-events/{self.event_past.id}/register/', 'event_past')
        ConventionEvent.objects.filter(pk=self.event.pk).update(capacity=1)
        self.assert_code(url, 'event_full')
        ConventionEvent.objects.filter(pk=self.event.pk).update(registration_open=False)
        self.assert_code(url, 'registration_closed')


class RoomVenueNameTests(ApiTestCase):
    """Название площадки в кратком описании помещения"""

    def test_run_and_schedule_rooms_have_venue_name(self):
        response = self.client.get(f'/api/runs/{self.run_soon.id}/')
        self.assertEqual(response.data['rooms'][0]['venue_name'], 'Loft Alpha')
        response = self.client.get(f'/api/convention-events/{self.event.id}/schedule/')
        self.assertEqual({room['venue_name'] for room in response.data['runs'][0]['rooms']}, {'Loft Alpha'})
        self.assertEqual({room['venue_name'] for room in response.data['venue_rooms']}, {'Loft Alpha'})

    def test_venue_list_queries_do_not_grow_with_rooms(self):
        with CaptureQueriesContext(connection) as before:
            self.client.get('/api/venues/')
        for i in range(10):
            Room.objects.create(venue=self.venue, name=f'Зал {i + 10}')
        with self.assertNumQueries(len(before)):
            response = self.client.get('/api/venues/')
        venue = next(item for item in response.data['results'] if item['id'] == self.venue.id)
        self.assertEqual({room['venue_name'] for room in venue['rooms']}, {'Loft Alpha'})


class GameValidationTests(ApiTestCase):
    """Диапазоны «минимум — максимум» и постер игры"""

    def test_ranges_on_create(self):
        self.login(self.master)
        response = self.client.post('/api/games/', {
            'name': 'Диапазоны', 'players_min': 5, 'players_max': 3,
            'female_roles_min': 2, 'female_roles_max': 1, 'male_roles_min': 0, 'male_roles_max': 0,
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual({'players_max', 'female_roles_max'}, set(response.data) - {'status_code'})
        # Значение по умолчанию для второго конца диапазона (players_max = 10)
        response = self.client.post('/api/games/', {'name': 'Много игроков', 'players_min': 11}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('players_max', response.data)
        response = self.client.post('/api/games/', {'name': 'Равные', 'players_min': 3, 'players_max': 3}, format='json')
        self.assertEqual(response.status_code, 201)

    def test_ranges_on_partial_update(self):
        self.login(self.master)
        url = f'/api/games/{self.game.id}/'
        # У игры players_max = 4
        response = self.client.patch(url, {'players_min': 5}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('players_max', response.data)
        self.assertEqual(self.client.patch(url, {'players_min': 4}, format='json').status_code, 200)

    def test_poster_format_and_size(self):
        import tempfile
        from django.test import override_settings
        self.login(self.master)
        url = f'/api/games/{self.game.id}/'
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.patch(url, {'poster': png_file('poster.gif', image_format='GIF')}, format='multipart')
            self.assertEqual(response.status_code, 400)
            self.assertIn('JPEG', response.data['poster'][0])
            # Формат определяется по содержимому, а не по имени файла
            response = self.client.patch(url, {'poster': png_file('poster.jpg', image_format='GIF')}, format='multipart')
            self.assertEqual(response.status_code, 400)

            with mock.patch('server.serializers.POSTER_MAX_SIZE', 10):
                response = self.client.patch(url, {'poster': png_file()}, format='multipart')
            self.assertEqual(response.status_code, 400)
            self.assertIn('5 МБ', response.data['poster'][0])

            for image_format in ('PNG', 'JPEG', 'WEBP'):
                with self.subTest(image_format=image_format):
                    response = self.client.patch(
                        url, {'poster': png_file(f'poster.{image_format.lower()}', image_format=image_format)},
                        format='multipart',
                    )
                    self.assertEqual(response.status_code, 200)


class ImportCsvFormatTests(ApiTestCase):
    """Импорт CSV: расширение без учёта регистра и BOM в начале файла"""

    def test_games_uppercase_extension_and_bom(self):
        self.login(self.staff)
        content = '\ufeffНазвание,Анонс\nИгра с BOM,Текст\n'.encode('utf-8')
        response = self.client.post(
            '/api/games/import_csv/', {'file': SimpleUploadedFile('GAMES.CSV', content)}, format='multipart'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['created'], 1)
        self.assertTrue(Game.objects.filter(name='Игра с BOM', announcement='Текст').exists())

    def test_conventions_uppercase_extension_and_bom(self):
        self.login(self.staff)
        content = (
            '\ufeffНазвание мероприятия,Город,Дата начала,Дата конца\n'
            'Конвент с BOM,Москва,01.02.2030,02.02.2030\n'
        ).encode('utf-8')
        response = self.client.post(
            '/api/conventions/import_csv/', {'file': SimpleUploadedFile('Cons.Csv', content)}, format='multipart'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['events_created'], 1)
        self.assertTrue(Convention.objects.filter(name='Конвент с BOM').exists())

    def test_other_extension_rejected(self):
        self.login(self.staff)
        response = self.client.post(
            '/api/games/import_csv/', {'file': SimpleUploadedFile('games.txt', b'x')}, format='multipart'
        )
        self.assertEqual(response.status_code, 400)


class CityApiTests(ApiTestCase):
    """Города: уникальность названия и права на правку"""

    def test_name_is_unique_case_insensitive(self):
        self.login(self.player)
        for name in ('москва', ' МОСКВА '):
            with self.subTest(name=name):
                response = self.client.post('/api/cities/', {'name': name}, format='json')
                self.assertEqual(response.status_code, 400)
                self.assertIn('name', response.data)
        response = self.client.post('/api/cities/', {'name': ' Тверь '}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'Тверь')

    def test_only_staff_edits_city(self):
        url = f'/api/cities/{self.kazan.id}/'
        self.login(self.player)
        self.assertEqual(self.client.patch(url, {'timezone': 'Asia/Omsk'}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(url, {'name': 'Kazan'}, format='json').status_code, 403)
        self.login(self.staff)
        response = self.client.patch(url, {'timezone': 'Asia/Omsk'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['timezone'], 'Asia/Omsk')
        # Своё название (в другом регистре) сохранить можно, чужое — нет
        self.assertEqual(self.client.patch(url, {'name': 'КАЗАНЬ'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'name': 'москва'}, format='json').status_code, 400)


class EventDatesValidationTests(ApiTestCase):
    def test_date_end_not_before_date_start(self):
        self.login(self.conv_organizer)
        today = timezone.localdate()
        payload = {
            'convention_id': self.convention.id, 'city_id': self.moscow.id,
            'date_start': str(today + timedelta(days=40)), 'date_end': str(today + timedelta(days=39)),
        }
        response = self.client.post('/api/convention-events/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('date_end', response.data)
        payload['date_end'] = payload['date_start']
        self.assertEqual(self.client.post('/api/convention-events/', payload, format='json').status_code, 201)

        # Частичная правка сверяется с сохранённой датой начала
        response = self.client.patch(
            f'/api/convention-events/{self.event.id}/',
            {'date_end': str(self.event.date_start - timedelta(days=1))}, format='json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('date_end', response.data)


class EventUnregisterTests(ApiTestCase):
    """Отмена регистрации на проведение снимает заявки на его предстоящие прогоны"""

    def test_unregister_removes_upcoming_run_registrations(self):
        now = timezone.now()
        # Подтверждённое место на заполненном прогоне и очередь за ним
        full_run = Run.objects.create(
            game=self.game, date=now + timedelta(days=11), city=self.moscow,
            convention_event=self.event, max_players=1,
        )
        Registration.objects.create(run=full_run, user=self.player, status='confirmed')
        waiting = Registration.objects.create(run=full_run, user=self.stranger, status='waitlist')
        # Прошедший прогон проведения и прогон вне конвента не затрагиваются
        past_run = Run.objects.create(
            game=self.game, date=now - timedelta(days=1), city=self.moscow, convention_event=self.event,
        )
        Registration.objects.create(run=past_run, user=self.player, status='confirmed')

        self.login(self.player)
        response = self.client.post(f'/api/convention-events/{self.event.id}/unregister/')
        self.assertEqual(response.status_code, 200)
        # run_convention (pending) и full_run (confirmed)
        self.assertEqual(response.data['runs_unregistered'], 2)
        self.assertFalse(Registration.objects.filter(
            user=self.player, run__in=[self.run_convention, full_run]
        ).exists())
        self.assertTrue(Registration.objects.filter(user=self.player, run=past_run).exists())
        self.assertTrue(Registration.objects.filter(user=self.player, run=self.run_soon).exists())
        # Освободившееся место продвинуло лист ожидания
        waiting.refresh_from_db()
        self.assertEqual(waiting.status, 'pending')

    def test_unregister_without_run_registrations(self):
        self.login(self.stranger)
        response = self.client.post(f'/api/convention-events/{self.event.id}/unregister/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['runs_unregistered'], 0)


class ModelCleanTimezoneTests(ApiTestCase):
    """Run.clean и CommonEvent.clean сверяют дату в часовом поясе города проведения"""

    def local_midnight_plus(self, day, minutes):
        """Момент «minutes минут после полуночи» дня day по Москве (в UTC это ещё предыдущий день)"""
        import pytz
        return pytz.timezone('Europe/Moscow').localize(
            datetime.combine(day, datetime.min.time()) + timedelta(minutes=minutes)
        )

    def test_run_clean(self):
        from django.core.exceptions import ValidationError
        run = Run(game=self.game, city=self.moscow, convention_event=self.event)
        run.date = self.local_midnight_plus(self.event.date_start, 30)
        run.clean()
        run.date = self.local_midnight_plus(self.event.date_end + timedelta(days=1), 30)
        with self.assertRaises(ValidationError):
            run.clean()

    def test_common_event_clean(self):
        from django.core.exceptions import ValidationError
        common_event = CommonEvent(convention_event=self.event, name='Заезд')
        common_event.date = self.local_midnight_plus(self.event.date_start, 30)
        common_event.clean()
        common_event.date = self.local_midnight_plus(self.event.date_end + timedelta(days=1), 30)
        with self.assertRaises(ValidationError):
            common_event.clean()
