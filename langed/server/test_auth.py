"""
Тесты авторизации: вход по паролю, регистрация, сброс пароля, выход,
привязка пользователей по sub и соцвход (kc_idp_hint, next).
Keycloak не вызывается — все обращения к нему подменяются.
"""
from unittest import mock
from urllib.parse import parse_qs, urlsplit

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from server import keycloak
from server.models import KeycloakIdentity
from server.oidc import (
    KeycloakOIDCAuthenticationBackend,
    add_auth_error,
    safe_next_path,
)

User = get_user_model()

TOKENS = {'id_token': 'id-token', 'access_token': 'access-token', 'refresh_token': 'refresh-token'}

PROVIDERS = [{'id': 'google', 'name': 'Google'}, {'id': 'vkid', 'name': 'VK ID'}]


def make_claims(**overrides):
    claims = {
        'sub': 'sub-1',
        'preferred_username': 'user@example.com',
        'email': 'user@example.com',
        'email_verified': False,
        'given_name': 'Иван',
        'family_name': 'Петров',
    }
    claims.update(overrides)
    return claims


def fake_response(status_code=200, json_data=None, headers=None):
    response = mock.Mock()
    response.status_code = status_code
    response.headers = headers or {}
    if json_data is None:
        response.json.side_effect = ValueError('no json')
    else:
        response.json.return_value = json_data
    return response


class AuthAPITestCase(TestCase):
    """Общая подготовка: клиент с проверкой CSRF и подмена проверки токена"""

    def setUp(self):
        cache.clear()
        self.client = Client(enforce_csrf_checks=True)
        self.claims = make_claims()

        patcher = mock.patch.object(
            KeycloakOIDCAuthenticationBackend, 'verify_token',
            side_effect=lambda token, **kwargs: {'sub': self.claims['sub']},
        )
        self.verify_token = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = mock.patch.object(
            KeycloakOIDCAuthenticationBackend, 'get_userinfo',
            side_effect=lambda *args: self.claims,
        )
        self.get_userinfo = patcher.start()
        self.addCleanup(patcher.stop)

    def csrf_token(self):
        """Как frontend: GET /api/auth/user/ ставит cookie csrftoken"""
        response = self.client.get('/api/auth/user/')
        self.assertEqual(response.status_code, 200)
        return self.client.cookies['csrftoken'].value

    def post(self, path, data=None):
        token = self.csrf_token()
        return self.client.post(
            path, data or {}, content_type='application/json', HTTP_X_CSRFTOKEN=token,
        )


class LoginTests(AuthAPITestCase):
    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    def test_login_success(self, password_grant):
        response = self.post('/api/auth/login/', {'email': 'user@example.com', 'password': 'secret-password'})

        self.assertEqual(response.status_code, 200)
        password_grant.assert_called_once_with('user@example.com', 'secret-password')
        self.verify_token.assert_called_once_with('id-token', nonce=None)

        # Ответ совпадает с GET /api/auth/user/
        current = self.client.get('/api/auth/user/').json()
        self.assertEqual(response.json(), current)
        self.assertTrue(current['is_authenticated'])
        self.assertEqual(current['email'], 'user@example.com')
        self.assertEqual(current['first_name'], 'Иван')

        user = User.objects.get(keycloak_identity__sub='sub-1')
        self.assertEqual(user.username, 'user@example.com')
        self.assertFalse(user.has_usable_password())
        self.assertEqual(self.client.session['oidc_refresh_token'], 'refresh-token')
        self.assertEqual(self.client.session['oidc_id_token'], 'id-token')

    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    def test_login_requires_csrf_for_anonymous(self, password_grant):
        response = self.client.post(
            '/api/auth/login/', {'email': 'user@example.com', 'password': 'secret-password'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        password_grant.assert_not_called()

    @mock.patch('server.keycloak.password_grant', side_effect=keycloak.InvalidCredentials('bad'))
    def test_login_invalid_password(self, password_grant):
        response = self.post('/api/auth/login/', {'email': 'user@example.com', 'password': 'wrong'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'code': 'invalid_credentials', 'detail': 'Неверная почта или пароль'})
        self.assertFalse(self.client.get('/api/auth/user/').json()['is_authenticated'])

    @mock.patch('server.keycloak.password_grant', side_effect=keycloak.AccountNotReady('not ready'))
    def test_login_account_not_ready(self, password_grant):
        response = self.post('/api/auth/login/', {'email': 'user@example.com', 'password': 'secret-password'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'account_not_ready')
        self.assertTrue(response.json()['detail'])

    @mock.patch('server.keycloak.password_grant', side_effect=keycloak.KeycloakUnavailable('down'))
    def test_login_keycloak_unavailable(self, password_grant):
        response = self.post('/api/auth/login/', {'email': 'user@example.com', 'password': 'secret-password'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'auth_unavailable')

    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    def test_login_userinfo_unavailable(self, password_grant):
        self.get_userinfo.side_effect = requests.ConnectionError('down')
        response = self.post('/api/auth/login/', {'email': 'user@example.com', 'password': 'secret-password'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'auth_unavailable')
        self.assertFalse(User.objects.exists())

    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    def test_login_empty_fields(self, password_grant):
        response = self.post('/api/auth/login/', {'email': '', 'password': ''})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'validation_error')
        self.assertEqual(set(response.json()['errors']), {'email', 'password'})
        password_grant.assert_not_called()

    @mock.patch('server.keycloak.password_grant', side_effect=keycloak.InvalidCredentials('bad'))
    def test_login_throttled(self, password_grant):
        token = self.csrf_token()
        statuses = []
        for _ in range(11):
            response = self.client.post(
                '/api/auth/login/', {'email': 'user@example.com', 'password': 'wrong'},
                content_type='application/json', HTTP_X_CSRFTOKEN=token,
            )
            statuses.append(response.status_code)
        self.assertEqual(statuses, [400] * 10 + [429])
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(response.json()['code'], 'throttled')
        self.assertIn('Retry-After', response)


class KeycloakClientTests(TestCase):
    """Разбор ответов Keycloak в server/keycloak.py"""

    @mock.patch('server.keycloak.requests.request')
    def test_password_grant_sends_expected_request(self, request):
        request.return_value = fake_response(200, TOKENS)
        self.assertEqual(keycloak.password_grant('user@example.com', 'secret-password'), TOKENS)

        args, kwargs = request.call_args
        self.assertEqual(args[0], 'POST')
        self.assertEqual(kwargs['data']['grant_type'], 'password')
        self.assertEqual(kwargs['data']['username'], 'user@example.com')
        self.assertEqual(kwargs['data']['scope'], 'openid email profile')
        self.assertTrue(kwargs['timeout'])

    @mock.patch('server.keycloak.requests.request')
    def test_password_grant_errors(self, request):
        request.return_value = fake_response(
            401, {'error': 'invalid_grant', 'error_description': 'Invalid user credentials'})
        with self.assertRaises(keycloak.InvalidCredentials):
            keycloak.password_grant('user@example.com', 'wrong')

        request.return_value = fake_response(
            400, {'error': 'invalid_grant', 'error_description': 'Account is not fully set up'})
        with self.assertRaises(keycloak.AccountNotReady):
            keycloak.password_grant('user@example.com', 'secret-password')

        request.return_value = fake_response(
            400, {'error': 'unauthorized_client', 'error_description': 'Client not allowed for direct access grants'})
        with self.assertRaises(keycloak.KeycloakUnavailable):
            keycloak.password_grant('user@example.com', 'secret-password')

        request.return_value = fake_response(502)
        with self.assertRaises(keycloak.KeycloakUnavailable):
            keycloak.password_grant('user@example.com', 'secret-password')

        request.side_effect = requests.ConnectionError('down')
        with self.assertRaises(keycloak.KeycloakUnavailable):
            keycloak.password_grant('user@example.com', 'secret-password')

    @mock.patch('server.keycloak.service_token', return_value='service-token')
    @mock.patch('server.keycloak.requests.request')
    def test_create_user(self, request, service_token):
        request.return_value = fake_response(201, headers={'Location': 'https://kc/admin/realms/r/users/kc-id-1'})
        self.assertEqual(keycloak.create_user('new@example.com', 'secret-password', 'Анна', 'Иванова'), 'kc-id-1')

        body = request.call_args.kwargs['json']
        self.assertEqual(body['username'], 'new@example.com')
        self.assertEqual(body['email'], 'new@example.com')
        self.assertIs(body['emailVerified'], False)
        self.assertIs(body['enabled'], True)
        self.assertEqual(body['credentials'], [{'type': 'password', 'value': 'secret-password', 'temporary': False}])
        self.assertEqual(request.call_args.kwargs['headers'], {'Authorization': 'Bearer service-token'})

    @mock.patch('server.keycloak.service_token', return_value='service-token')
    @mock.patch('server.keycloak.requests.request')
    def test_create_user_errors(self, request, service_token):
        request.return_value = fake_response(409, {'errorMessage': 'User exists with same email'})
        with self.assertRaises(keycloak.EmailExists):
            keycloak.create_user('new@example.com', 'secret-password', 'Анна', 'Иванова')

        request.return_value = fake_response(400, {
            'error': 'invalidPasswordMinLengthMessage',
            'error_description': 'Invalid password: minimum length 12.',
        })
        with self.assertRaises(keycloak.ValidationFailed) as ctx:
            keycloak.create_user('new@example.com', 'secret-password', 'Анна', 'Иванова')
        self.assertEqual(ctx.exception.errors, {'password': ['Invalid password: minimum length 12.']})

        request.return_value = fake_response(403)
        with self.assertRaises(keycloak.KeycloakUnavailable):
            keycloak.create_user('new@example.com', 'secret-password', 'Анна', 'Иванова')


class RegisterTests(AuthAPITestCase):
    DATA = {
        'email': 'New@Example.com',
        'password': 'secret-password',
        'first_name': 'Анна',
        'last_name': 'Иванова',
    }

    def setUp(self):
        super().setUp()
        self.claims = make_claims(
            sub='sub-new', preferred_username='new@example.com', email='new@example.com',
            given_name='Анна', family_name='Иванова',
        )

    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    @mock.patch('server.keycloak.send_actions_email')
    @mock.patch('server.keycloak.create_user', return_value='kc-id-1')
    def test_register_success(self, create_user, send_actions_email, password_grant):
        response = self.post('/api/auth/register/', self.DATA)

        self.assertEqual(response.status_code, 201)
        create_user.assert_called_once_with('new@example.com', 'secret-password', 'Анна', 'Иванова')
        send_actions_email.assert_called_once_with('kc-id-1', ['VERIFY_EMAIL'])
        password_grant.assert_called_once_with('new@example.com', 'secret-password')

        current = self.client.get('/api/auth/user/').json()
        self.assertEqual(response.json(), current)
        self.assertTrue(current['is_authenticated'])
        self.assertEqual(current['display_name'], 'Анна Иванова')
        self.assertTrue(KeycloakIdentity.objects.filter(sub='sub-new').exists())

    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    @mock.patch('server.keycloak.send_actions_email', side_effect=keycloak.KeycloakError('smtp'))
    @mock.patch('server.keycloak.create_user', return_value='kc-id-1')
    def test_register_email_failure_does_not_block_login(self, create_user, send_actions_email, password_grant):
        response = self.post('/api/auth/register/', self.DATA)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['is_authenticated'])

    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    @mock.patch('server.keycloak.create_user', side_effect=keycloak.EmailExists('new@example.com'))
    def test_register_duplicate(self, create_user, password_grant):
        response = self.post('/api/auth/register/', self.DATA)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'email_exists')
        password_grant.assert_not_called()

    @mock.patch('server.keycloak.create_user')
    def test_register_validation(self, create_user):
        response = self.post('/api/auth/register/', {
            'email': 'not-an-email', 'password': 'short', 'first_name': ' ', 'last_name': '',
        })
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body['code'], 'validation_error')
        self.assertEqual(set(body['errors']), {'email', 'password', 'first_name', 'last_name'})
        for messages in body['errors'].values():
            self.assertIsInstance(messages, list)
        create_user.assert_not_called()

    @mock.patch('server.keycloak.create_user', side_effect=keycloak.ValidationFailed({'password': ['Слишком простой']}))
    def test_register_keycloak_password_policy(self, create_user):
        response = self.post('/api/auth/register/', self.DATA)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'validation_error')
        self.assertEqual(response.json()['errors'], {'password': ['Слишком простой']})

    @mock.patch('server.keycloak.create_user', side_effect=keycloak.KeycloakUnavailable('down'))
    def test_register_keycloak_unavailable(self, create_user):
        response = self.post('/api/auth/register/', self.DATA)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'auth_unavailable')


class PasswordResetTests(AuthAPITestCase):
    @mock.patch('server.keycloak.send_actions_email')
    @mock.patch('server.keycloak.find_user_id_by_email', return_value='kc-id-1')
    @mock.patch('server.keycloak.service_token', return_value='service-token')
    def test_existing_email(self, service_token, find_user, send_actions_email):
        response = self.post('/api/auth/password-reset/', {'email': 'User@example.com'})
        self.assertEqual(response.status_code, 204)
        find_user.assert_called_once_with('user@example.com', token='service-token')
        send_actions_email.assert_called_once_with('kc-id-1', ['UPDATE_PASSWORD'], token='service-token')

    @mock.patch('server.keycloak.send_actions_email')
    @mock.patch('server.keycloak.find_user_id_by_email', return_value=None)
    @mock.patch('server.keycloak.service_token', return_value='service-token')
    def test_unknown_email(self, service_token, find_user, send_actions_email):
        response = self.post('/api/auth/password-reset/', {'email': 'nobody@example.com'})
        self.assertEqual(response.status_code, 204)
        send_actions_email.assert_not_called()

    @mock.patch('server.keycloak.service_token', side_effect=keycloak.KeycloakUnavailable('down'))
    def test_keycloak_unavailable(self, service_token):
        response = self.post('/api/auth/password-reset/', {'email': 'user@example.com'})
        self.assertEqual(response.status_code, 204)

    def test_empty_body(self):
        response = self.post('/api/auth/password-reset/', {})
        self.assertEqual(response.status_code, 204)


class LogoutTests(AuthAPITestCase):
    @mock.patch('server.keycloak.logout')
    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    def test_logout_revokes_keycloak_session(self, password_grant, kc_logout):
        self.post('/api/auth/login/', {'email': 'user@example.com', 'password': 'secret-password'})

        response = self.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 204)
        kc_logout.assert_called_once_with(refresh_token='refresh-token', id_token='id-token')
        self.assertFalse(self.client.get('/api/auth/user/').json()['is_authenticated'])

    @mock.patch('server.keycloak.logout', side_effect=keycloak.KeycloakUnavailable('down'))
    @mock.patch('server.keycloak.password_grant', return_value=TOKENS)
    def test_logout_survives_keycloak_failure(self, password_grant, kc_logout):
        self.post('/api/auth/login/', {'email': 'user@example.com', 'password': 'secret-password'})
        response = self.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(self.client.get('/api/auth/user/').json()['is_authenticated'])

    @mock.patch('server.keycloak.logout', return_value=False)
    def test_logout_anonymous(self, kc_logout):
        response = self.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 204)


@override_settings(AUTH_PROVIDERS=PROVIDERS)
class ProvidersTests(TestCase):
    def test_providers(self):
        response = self.client.get('/api/auth/providers/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), PROVIDERS)


class IdentityLinkTests(TestCase):
    """Поиск и создание пользователя по claims"""

    def setUp(self):
        self.backend = KeycloakOIDCAuthenticationBackend()

    def resolve(self, claims):
        with mock.patch.object(self.backend, 'get_userinfo', return_value=claims):
            return self.backend.get_or_create_user('access-token', 'id-token', {'sub': claims['sub']})

    def test_found_by_sub_even_if_username_and_email_changed(self):
        user = User.objects.create_user(username='old-name', email='old@example.com')
        KeycloakIdentity.objects.create(user=user, sub='sub-1')

        found = self.resolve(make_claims(preferred_username='new-name', email='new@example.com'))

        self.assertEqual(found.pk, user.pk)
        self.assertEqual(found.email, 'new@example.com')
        self.assertEqual(User.objects.count(), 1)

    def test_creates_user_with_identity(self):
        user = self.resolve(make_claims())
        self.assertEqual(user.username, 'user@example.com')
        self.assertEqual(user.keycloak_identity.sub, 'sub-1')
        self.assertFalse(user.has_usable_password())

    def test_links_by_verified_email(self):
        existing = User.objects.create_user(username='ivan', email='User@example.com')

        user = self.resolve(make_claims(email_verified=True))

        self.assertEqual(user.pk, existing.pk)
        self.assertEqual(existing.keycloak_identity.sub, 'sub-1')
        self.assertEqual(User.objects.count(), 1)

    def test_does_not_link_by_unverified_email(self):
        existing = User.objects.create_user(username='ivan', email='user@example.com')

        user = self.resolve(make_claims(email_verified=False))

        self.assertNotEqual(user.pk, existing.pk)
        self.assertFalse(KeycloakIdentity.objects.filter(user=existing).exists())
        self.assertEqual(user.keycloak_identity.sub, 'sub-1')

    def test_does_not_link_without_email_verified_claim(self):
        existing = User.objects.create_user(username='ivan', email='user@example.com')
        claims = make_claims()
        del claims['email_verified']

        user = self.resolve(claims)

        self.assertNotEqual(user.pk, existing.pk)

    def test_does_not_take_over_user_linked_to_another_sub(self):
        existing = User.objects.create_user(username='user@example.com', email='user@example.com')
        KeycloakIdentity.objects.create(user=existing, sub='sub-owner')

        user = self.resolve(make_claims(sub='sub-attacker', email_verified=True))

        self.assertNotEqual(user.pk, existing.pk)
        self.assertEqual(existing.keycloak_identity.sub, 'sub-owner')
        # Username занят — новому пользователю выдаётся уникальный
        self.assertEqual(user.username, 'user@example.com-2')

    def test_legacy_user_linked_once_by_username(self):
        legacy = User.objects.create_user(username='ivan', email='other@example.com')

        user = self.resolve(make_claims(preferred_username='ivan'))
        self.assertEqual(user.pk, legacy.pk)
        self.assertEqual(legacy.keycloak_identity.sub, 'sub-1')

        # Привязка разовая: другой sub с тем же preferred_username получает новую учётку
        other = self.resolve(make_claims(sub='sub-2', preferred_username='ivan', email='x@example.com'))
        self.assertNotEqual(other.pk, legacy.pk)
        self.assertEqual(other.username, 'ivan-2')

    def test_local_user_with_password_is_not_linked_by_username(self):
        admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='local-password')

        user = self.resolve(make_claims(preferred_username='admin', email='attacker@example.com'))

        self.assertNotEqual(user.pk, admin.pk)
        self.assertFalse(user.is_superuser)
        self.assertFalse(KeycloakIdentity.objects.filter(user=admin).exists())

    @override_settings(OIDC_LEGACY_USERNAME_LINK=False)
    def test_legacy_link_can_be_disabled(self):
        legacy = User.objects.create_user(username='ivan', email='other@example.com')
        user = self.resolve(make_claims(preferred_username='ivan'))
        self.assertNotEqual(user.pk, legacy.pk)

    def test_claims_without_sub_rejected(self):
        from django.core.exceptions import SuspiciousOperation
        claims = make_claims()
        claims['sub'] = ''
        with self.assertRaises(SuspiciousOperation):
            self.resolve(claims)


@override_settings(AUTH_PROVIDERS=PROVIDERS)
class SocialLoginTests(TestCase):
    """/oidc/authenticate/ и /oidc/callback/"""

    def authenticate(self, query):
        response = self.client.get('/oidc/authenticate/' + query)
        self.assertEqual(response.status_code, 302)
        return parse_qs(urlsplit(response['Location']).query)

    def test_idp_hint_for_allowed_alias(self):
        params = self.authenticate('?idp=google&next=/games')
        self.assertEqual(params['kc_idp_hint'], ['google'])
        self.assertEqual(params['redirect_uri'], ['http://testserver/oidc/callback/'])
        self.assertEqual(self.client.session['oidc_login_next'], '/games')

    def test_idp_hint_ignored_for_unknown_alias(self):
        for query in ('?idp=evil', '?idp=', ''):
            params = self.authenticate(query)
            self.assertNotIn('kc_idp_hint', params)

    def test_redirect_uri_is_https_behind_proxy(self):
        response = self.client.get('/oidc/authenticate/', HTTP_X_FORWARDED_PROTO='https', HTTP_X_FORWARDED_HOST='langed.example.com')
        params = parse_qs(urlsplit(response['Location']).query)
        self.assertEqual(params['redirect_uri'], ['https://langed.example.com/oidc/callback/'])

    def test_next_must_be_relative(self):
        for bad in ('https://evil.example/', '//evil.example/', 'http://testserver/games',
                    '/\\evil.example', 'games', 'javascript:alert(1)'):
            self.client.get('/oidc/authenticate/', {'next': bad})
            self.assertIsNone(self.client.session['oidc_login_next'], bad)

        self.client.get('/oidc/authenticate/', {'next': '/games/5?tab=runs'})
        self.assertEqual(self.client.session['oidc_login_next'], '/games/5?tab=runs')

    def test_safe_next_path(self):
        self.assertEqual(safe_next_path('/games'), '/games')
        self.assertIsNone(safe_next_path('//evil.example'))
        self.assertIsNone(safe_next_path('https://evil.example'))
        self.assertIsNone(safe_next_path(None))

    def test_add_auth_error(self):
        self.assertEqual(add_auth_error('/games?tab=runs#top', 'access_denied'),
                         '/games?tab=runs&auth_error=access_denied#top')
        self.assertEqual(add_auth_error('/?auth_error=old', 'new'), '/?auth_error=new')

    def test_callback_error_returns_to_next(self):
        self.authenticate('?idp=google&next=/games')
        state = next(iter(self.client.session['oidc_states']))

        response = self.client.get('/oidc/callback/', {'error': 'access_denied', 'state': state})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/games?auth_error=access_denied')

    def test_callback_unknown_state_does_not_restart_login(self):
        self.authenticate('?next=/games')

        response = self.client.get('/oidc/callback/', {'code': 'code', 'state': 'unknown-state'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/games?auth_error=invalid_state')

    def test_callback_without_session_does_not_restart_login(self):
        response = self.client.get('/oidc/callback/', {'code': 'code', 'state': 'state'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/?auth_error=invalid_state')

    def test_callback_keycloak_unavailable(self):
        self.authenticate('?next=/games')
        state = next(iter(self.client.session['oidc_states']))

        with mock.patch.object(KeycloakOIDCAuthenticationBackend, 'get_token',
                               side_effect=requests.ConnectionError('down')):
            response = self.client.get('/oidc/callback/', {'code': 'code', 'state': state})

        self.assertEqual(response['Location'], '/games?auth_error=auth_unavailable')

    def test_callback_success_redirects_to_next_and_stores_refresh_token(self):
        self.authenticate('?idp=google&next=/games')
        state = next(iter(self.client.session['oidc_states']))
        claims = make_claims()

        with mock.patch('mozilla_django_oidc.auth.requests.post',
                        return_value=fake_response(200, TOKENS)), \
                mock.patch.object(KeycloakOIDCAuthenticationBackend, 'verify_token',
                                  return_value={'sub': 'sub-1'}), \
                mock.patch.object(KeycloakOIDCAuthenticationBackend, 'get_userinfo',
                                  return_value=claims):
            response = self.client.get('/oidc/callback/', {'code': 'code', 'state': state})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/games')
        self.assertEqual(self.client.session['oidc_refresh_token'], 'refresh-token')
        self.assertTrue(KeycloakIdentity.objects.filter(sub='sub-1').exists())
        self.assertTrue(self.client.get('/api/auth/user/').json()['is_authenticated'])


class ProfileUpdateTests(AuthAPITestCase):
    """PATCH /api/auth/user/: правка имени в Langed и в Keycloak"""

    def patch(self, data):
        token = self.csrf_token()
        return self.client.patch(
            '/api/auth/user/', data, content_type='application/json', HTTP_X_CSRFTOKEN=token,
        )

    def make_user(self, linked=True):
        user = User.objects.create(username='ivan', first_name='Иван', last_name='Петров')
        if linked:
            KeycloakIdentity.objects.create(user=user, sub='sub-1')
        self.client.force_login(user)
        return user

    def test_anonymous(self):
        self.assertEqual(self.patch({'first_name': 'Пётр'}).status_code, 403)

    @mock.patch('server.keycloak.update_user_name')
    def test_updates_keycloak_and_local_user(self, update_user_name):
        user = self.make_user()
        response = self.patch({'first_name': ' Пётр ', 'last_name': 'Иванов'})
        self.assertEqual(response.status_code, 200)
        update_user_name.assert_called_once_with('sub-1', 'Пётр', 'Иванов')
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.last_name), ('Пётр', 'Иванов'))
        self.assertEqual(response.json()['display_name'], 'Пётр Иванов')
        self.assertEqual(response.json(), self.client.get('/api/auth/user/').json())

    @mock.patch('server.keycloak.update_user_name')
    def test_partial_update_keeps_other_field(self, update_user_name):
        user = self.make_user()
        self.assertEqual(self.patch({'last_name': ''}).status_code, 200)
        update_user_name.assert_called_once_with('sub-1', 'Иван', '')
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.last_name), ('Иван', ''))

    @mock.patch('server.keycloak.update_user_name')
    def test_user_without_identity_is_updated_locally(self, update_user_name):
        user = self.make_user(linked=False)
        self.assertEqual(self.patch({'first_name': 'Пётр'}).status_code, 200)
        update_user_name.assert_not_called()
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Пётр')

    @mock.patch('server.keycloak.update_user_name')
    def test_validation(self, update_user_name):
        user = self.make_user()
        cases = [
            ({'first_name': '', 'last_name': ' '}, 'first_name'),
            ({'first_name': 'а' * 151}, 'first_name'),
            ({'last_name': 'а' * 151}, 'last_name'),
            ({'last_name': 5}, 'last_name'),
        ]
        for data, field in cases:
            with self.subTest(data=data):
                response = self.patch(data)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()['code'], 'validation_error')
                self.assertIn(field, response.json()['errors'])
        update_user_name.assert_not_called()
        user.refresh_from_db()
        self.assertEqual((user.first_name, user.last_name), ('Иван', 'Петров'))

    @mock.patch('server.keycloak.update_user_name', side_effect=keycloak.KeycloakUnavailable('down'))
    def test_keycloak_unavailable_keeps_local_name(self, update_user_name):
        user = self.make_user()
        response = self.patch({'first_name': 'Пётр'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'auth_unavailable')
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Иван')

    @mock.patch('server.keycloak.service_token', return_value='service-token')
    @mock.patch('server.keycloak.requests.request')
    def test_keycloak_client_sends_full_representation(self, request, service_token):
        representation = {'id': 'sub-1', 'email': 'user@example.com', 'firstName': 'Иван', 'attributes': {'a': ['b']}}
        request.side_effect = [fake_response(200, representation), fake_response(204)]
        keycloak.update_user_name('sub-1', 'Пётр', 'Иванов')
        (method, url), kwargs = request.call_args
        self.assertEqual(method, 'PUT')
        self.assertTrue(url.endswith('/users/sub-1'))
        self.assertEqual(kwargs['json'], {**representation, 'firstName': 'Пётр', 'lastName': 'Иванов'})

        request.side_effect = [fake_response(404, {'error': 'User not found'})]
        with self.assertRaises(keycloak.KeycloakUnavailable):
            keycloak.update_user_name('sub-1', 'Пётр', 'Иванов')


class PasswordChangeTests(AuthAPITestCase):
    """POST /api/auth/password-change/"""

    URL = '/api/auth/password-change/'
    DATA = {'current_password': 'old-password', 'new_password': 'new-password'}

    def login_by_password(self):
        with mock.patch('server.keycloak.password_grant', return_value=TOKENS):
            response = self.post('/api/auth/login/', {'email': 'user@example.com', 'password': 'old-password'})
        self.assertEqual(response.status_code, 200)

    def test_has_password_login_flag(self):
        self.assertNotIn('has_password_login', self.client.get('/api/auth/user/').json())
        user = User.objects.create(username='social')
        self.client.force_login(user)
        self.assertFalse(self.client.get('/api/auth/user/').json()['has_password_login'])
        self.client.logout()
        self.login_by_password()
        self.assertTrue(self.client.get('/api/auth/user/').json()['has_password_login'])

    def test_anonymous(self):
        self.assertEqual(self.post(self.URL, self.DATA).status_code, 403)

    @mock.patch('server.keycloak.logout')
    @mock.patch('server.keycloak.reset_password')
    def test_success(self, reset_password, kc_logout):
        self.login_by_password()
        check_tokens = {**TOKENS, 'refresh_token': 'check-refresh-token'}
        with mock.patch('server.keycloak.password_grant', return_value=check_tokens) as password_grant:
            response = self.post(self.URL, self.DATA)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        password_grant.assert_called_once_with('user@example.com', 'old-password')
        reset_password.assert_called_once_with('sub-1', 'new-password')
        # Сессия Keycloak, созданная проверкой пароля, завершена; сессия Langed осталась
        kc_logout.assert_called_once_with(refresh_token='check-refresh-token')
        self.assertTrue(self.client.get('/api/auth/user/').json()['is_authenticated'])

    @mock.patch('server.keycloak.reset_password')
    def test_wrong_current_password(self, reset_password):
        self.login_by_password()
        with mock.patch('server.keycloak.password_grant', side_effect=keycloak.InvalidCredentials('bad')):
            response = self.post(self.URL, self.DATA)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'invalid_credentials')
        self.assertIn('current_password', response.json()['errors'])
        reset_password.assert_not_called()

    @mock.patch('server.keycloak.password_grant')
    def test_validation(self, password_grant):
        self.login_by_password()
        password_grant.reset_mock()
        response = self.post(self.URL, {'current_password': '', 'new_password': 'short'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'validation_error')
        self.assertEqual(set(response.json()['errors']), {'current_password', 'new_password'})
        password_grant.assert_not_called()

    @mock.patch('server.keycloak.logout')
    @mock.patch(
        'server.keycloak.reset_password',
        side_effect=keycloak.ValidationFailed({'password': ['Invalid password: must contain a digit.']}),
    )
    def test_keycloak_password_policy(self, reset_password, kc_logout):
        self.login_by_password()
        with mock.patch('server.keycloak.password_grant', return_value=TOKENS):
            response = self.post(self.URL, self.DATA)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'validation_error')
        self.assertEqual(response.json()['errors'], {'new_password': ['Invalid password: must contain a digit.']})

    @mock.patch('server.keycloak.logout')
    def test_keycloak_unavailable(self, kc_logout):
        self.login_by_password()
        with mock.patch('server.keycloak.password_grant', side_effect=keycloak.KeycloakUnavailable('down')):
            response = self.post(self.URL, self.DATA)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['code'], 'auth_unavailable')
        with mock.patch('server.keycloak.password_grant', return_value=TOKENS), \
                mock.patch('server.keycloak.reset_password', side_effect=keycloak.KeycloakUnavailable('down')):
            response = self.post(self.URL, self.DATA)
        self.assertEqual(response.status_code, 503)

    @mock.patch('server.keycloak.password_grant')
    def test_social_login_cannot_change_password(self, password_grant):
        user = User.objects.create(username='social', email='user@example.com')
        KeycloakIdentity.objects.create(user=user, sub='sub-1')
        self.client.force_login(user)
        response = self.post(self.URL, self.DATA)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['code'], 'password_login_required')
        password_grant.assert_not_called()

    def test_throttled_like_login(self):
        self.login_by_password()
        token = self.csrf_token()
        statuses = []
        with mock.patch('server.keycloak.password_grant', side_effect=keycloak.InvalidCredentials('bad')):
            for _ in range(11):
                response = self.client.post(
                    self.URL, self.DATA, content_type='application/json', HTTP_X_CSRFTOKEN=token,
                )
                statuses.append(response.status_code)
        self.assertEqual(statuses, [400] * 10 + [429])
        self.assertEqual(response.json()['code'], 'throttled')

    @mock.patch('server.keycloak.service_token', return_value='service-token')
    @mock.patch('server.keycloak.requests.request')
    def test_keycloak_client_reset_password(self, request, service_token):
        request.return_value = fake_response(204)
        keycloak.reset_password('sub-1', 'new-password')
        (method, url), kwargs = request.call_args
        self.assertEqual(method, 'PUT')
        self.assertTrue(url.endswith('/users/sub-1/reset-password'))
        self.assertEqual(kwargs['json'], {'type': 'password', 'value': 'new-password', 'temporary': False})

        request.return_value = fake_response(400, {
            'error': 'invalidPasswordMinLengthMessage', 'error_description': 'Invalid password: minimum length 12.',
        })
        with self.assertRaises(keycloak.ValidationFailed) as raised:
            keycloak.reset_password('sub-1', 'short')
        self.assertEqual(raised.exception.errors, {'password': ['Invalid password: minimum length 12.']})
