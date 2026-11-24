"""
Тесты общих обработчиков: удаление записей со связями (PROTECT/RESTRICT) отвечает 409
"""
from django.contrib.auth import get_user_model
from django.db.models import RestrictedError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import City, Game, Run, Venue
from .views import custom_exception_handler

User = get_user_model()


class InUseDeleteTests(TestCase):
    """Удаление города с площадками и прогонами — 409 in_use вместо 500"""

    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create(username='staff', is_staff=True)
        cls.city = City.objects.create(name='Москва')
        Venue.objects.create(name='Loft Alpha', city=cls.city)
        Venue.objects.create(name='Beta Hall', city=cls.city)
        game = Game.objects.create(name='Alpha Station')
        Run.objects.create(game=game, date=timezone.now(), city=cls.city)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.staff)

    def test_delete_city_in_use_returns_409(self):
        response = self.client.delete(f'/api/cities/{self.city.id}/')

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['code'], 'in_use')
        self.assertEqual(
            response.json()['detail'],
            'Нельзя удалить: есть связанные записи (Площадки: 2, Прогоны: 1)',
        )
        self.assertTrue(City.objects.filter(id=self.city.id).exists())

    def test_delete_unused_city_succeeds(self):
        city = City.objects.create(name='Казань')

        response = self.client.delete(f'/api/cities/{city.id}/')

        self.assertEqual(response.status_code, 204)
        self.assertFalse(City.objects.filter(id=city.id).exists())

    def test_restricted_error_returns_409(self):
        venue = Venue.objects.filter(city=self.city).first()
        exc = RestrictedError('restricted', {venue})

        response = custom_exception_handler(exc, {})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data['code'], 'in_use')
        self.assertEqual(response.data['detail'], 'Нельзя удалить: есть связанные записи (Площадки: 1)')
