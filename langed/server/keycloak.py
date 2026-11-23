"""
Тонкий клиент Keycloak: вход по паролю, Admin REST API (создание пользователя,
письма с действиями) и завершение сессии.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Названия полей профиля Keycloak → поля API Langed
FIELD_NAMES = {
    'email': 'email',
    'username': 'email',
    'firstName': 'first_name',
    'lastName': 'last_name',
    'password': 'password',
}


class KeycloakError(Exception):
    """Базовая ошибка обращения к Keycloak"""


class KeycloakUnavailable(KeycloakError):
    """Keycloak недоступен, ответил ошибкой сервера или клиент langed настроен неверно"""


class InvalidCredentials(KeycloakError):
    """Неверная почта или пароль"""


class AccountNotReady(KeycloakError):
    """Вход невозможен, пока пользователь не выполнит обязательные действия в Keycloak"""


class AccountDisabled(KeycloakError):
    """Учётная запись отключена"""


class EmailExists(KeycloakError):
    """Пользователь с такой почтой уже есть"""


class ValidationFailed(KeycloakError):
    """Keycloak отклонил данные пользователя (например, парольная политика)"""

    def __init__(self, errors):
        super().__init__(errors)
        self.errors = errors


def _realm_url():
    return f'{settings.KEYCLOAK_SERVER_URL.rstrip("/")}/realms/{settings.KEYCLOAK_REALM}'


def _admin_url():
    return f'{settings.KEYCLOAK_SERVER_URL.rstrip("/")}/admin/realms/{settings.KEYCLOAK_REALM}'


def _logout_url():
    return f'{_realm_url()}/protocol/openid-connect/logout'


def _request(method, url, **kwargs):
    """Запрос к Keycloak с таймаутом; сетевые ошибки и 5xx превращаются в KeycloakUnavailable"""
    kwargs.setdefault('timeout', getattr(settings, 'KEYCLOAK_TIMEOUT', 10))
    kwargs.setdefault('verify', getattr(settings, 'OIDC_VERIFY_SSL', True))
    try:
        response = requests.request(method, url, **kwargs)
    except requests.RequestException as exc:
        logger.error('Keycloak request failed: %s %s: %s', method, url, exc)
        raise KeycloakUnavailable(str(exc)) from exc
    if response.status_code >= 500:
        logger.error('Keycloak server error: %s %s: %s', method, url, response.status_code)
        raise KeycloakUnavailable(f'HTTP {response.status_code}')
    return response


def _json(response):
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _client_credentials():
    return {
        'client_id': settings.OIDC_RP_CLIENT_ID,
        'client_secret': settings.OIDC_RP_CLIENT_SECRET,
    }


def password_grant(email, password):
    """
    Обменивает почту и пароль на токены (grant_type=password).
    Возвращает ответ token endpoint: id_token, access_token, refresh_token.
    """
    response = _request('POST', settings.OIDC_OP_TOKEN_ENDPOINT, data={
        **_client_credentials(),
        'grant_type': 'password',
        'username': email,
        'password': password,
        'scope': settings.OIDC_RP_SCOPES,
    })
    data = _json(response)
    if response.status_code == 200:
        if not data.get('id_token'):
            logger.error('Keycloak password grant returned no id_token')
            raise KeycloakUnavailable('no id_token')
        return data

    error = data.get('error', '')
    description = data.get('error_description', '')
    if error == 'invalid_grant':
        lowered = description.lower()
        if 'not fully set up' in lowered:
            raise AccountNotReady(description)
        if 'disabled' in lowered:
            raise AccountDisabled(description)
        raise InvalidCredentials(description)

    # invalid_client, unauthorized_client и т.п. — ошибка настройки клиента, а не пользователя
    logger.error(
        'Keycloak password grant rejected: HTTP %s %s: %s',
        response.status_code, error, description,
    )
    raise KeycloakUnavailable(error or f'HTTP {response.status_code}')


def service_token():
    """Токен service account клиента langed для Admin REST API (grant_type=client_credentials)"""
    response = _request('POST', settings.OIDC_OP_TOKEN_ENDPOINT, data={
        **_client_credentials(),
        'grant_type': 'client_credentials',
    })
    token = _json(response).get('access_token')
    if response.status_code != 200 or not token:
        logger.error('Keycloak client_credentials grant failed: HTTP %s', response.status_code)
        raise KeycloakUnavailable(f'HTTP {response.status_code}')
    return token


def _admin_request(method, path, token=None, **kwargs):
    token = token or service_token()
    headers = {'Authorization': f'Bearer {token}'}
    response = _request(method, f'{_admin_url()}{path}', headers=headers, **kwargs)
    if response.status_code in (401, 403):
        # У service account нет нужных ролей (manage-users)
        logger.error('Keycloak admin API denied: %s %s: HTTP %s', method, path, response.status_code)
        raise KeycloakUnavailable(f'HTTP {response.status_code}')
    return response


def _validation_errors(data):
    """Переводит ответ Keycloak 400 в словарь {поле: [сообщения]}"""
    errors = {}
    items = data.get('errors') if isinstance(data.get('errors'), list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        message = item.get('error_description') or item.get('errorMessage') or item.get('error') or ''
        field = FIELD_NAMES.get(item.get('field'))
        if not field:
            is_password = 'password' in f'{item.get("error", "")} {message}'.lower()
            field = 'password' if is_password else 'non_field_errors'
        errors.setdefault(field, []).append(message or 'Некорректное значение')
    return errors or {'non_field_errors': ['Некорректные данные']}


def create_user(email, password, first_name, last_name):
    """
    Создаёт пользователя в Keycloak (username = email, почта не подтверждена).
    Возвращает id пользователя в Keycloak.
    """
    token = service_token()
    response = _admin_request('POST', '/users', token=token, json={
        'username': email,
        'email': email,
        'firstName': first_name,
        'lastName': last_name,
        'enabled': True,
        'emailVerified': False,
        'credentials': [{'type': 'password', 'value': password, 'temporary': False}],
    })
    if response.status_code == 201:
        location = response.headers.get('Location', '')
        user_id = location.rstrip('/').rsplit('/', 1)[-1] if location else None
        return user_id or find_user_id_by_email(email, token=token)
    if response.status_code == 409:
        raise EmailExists(email)
    if response.status_code == 400:
        raise ValidationFailed(_validation_errors(_json(response)))
    logger.error('Keycloak create user failed: HTTP %s', response.status_code)
    raise KeycloakUnavailable(f'HTTP {response.status_code}')


def find_user_id_by_email(email, token=None):
    """Возвращает id включённого пользователя Keycloak с такой почтой или None"""
    response = _admin_request(
        'GET', '/users', token=token,
        params={'email': email, 'exact': 'true', 'max': 2},
    )
    if response.status_code != 200:
        logger.error('Keycloak user search failed: HTTP %s', response.status_code)
        raise KeycloakUnavailable(f'HTTP {response.status_code}')
    try:
        users = response.json()
    except ValueError:
        users = []
    for user in users if isinstance(users, list) else []:
        if user.get('enabled', True) and (user.get('email') or '').lower() == email.lower():
            return user.get('id')
    return None


def send_actions_email(user_id, actions, token=None):
    """
    Отправляет пользователю письмо со ссылкой на выполнение действий
    (VERIFY_EMAIL, UPDATE_PASSWORD) — execute-actions-email.
    """
    path = f'/users/{user_id}/execute-actions-email'
    token = token or service_token()
    site_url = getattr(settings, 'SITE_URL', None)
    response = None
    if site_url:
        # Ссылка «вернуться в приложение» после выполнения действия
        response = _admin_request('PUT', path, token=token, json=actions, params={
            'client_id': settings.OIDC_RP_CLIENT_ID,
            'redirect_uri': f'{site_url.rstrip("/")}/',
        })
    if response is None or response.status_code == 400:
        # redirect_uri не разрешён у клиента — отправляем письмо без ссылки возврата
        response = _admin_request('PUT', path, token=token, json=actions)
    if response.status_code not in (200, 204):
        logger.error('Keycloak execute-actions-email failed: HTTP %s', response.status_code)
        raise KeycloakError(f'HTTP {response.status_code}')


def update_user_name(user_id, first_name, last_name):
    """
    Меняет имя и фамилию пользователя Keycloak. Представление пользователя сначала
    читается и отправляется обратно целиком: частичный PUT Keycloak может отклонить
    (обязательные поля профиля) или стереть им остальные атрибуты.
    """
    token = service_token()
    path = f'/users/{user_id}'
    response = _admin_request('GET', path, token=token)
    representation = _json(response)
    if response.status_code != 200 or not representation:
        logger.error('Keycloak get user failed: HTTP %s', response.status_code)
        raise KeycloakUnavailable(f'HTTP {response.status_code}')
    representation.update({'firstName': first_name, 'lastName': last_name})
    response = _admin_request('PUT', path, token=token, json=representation)
    if response.status_code == 400:
        raise ValidationFailed(_validation_errors(_json(response)))
    if response.status_code not in (200, 204):
        logger.error('Keycloak update user failed: HTTP %s', response.status_code)
        raise KeycloakUnavailable(f'HTTP {response.status_code}')


def reset_password(user_id, password):
    """Задаёт пользователю Keycloak новый постоянный пароль (reset-password)"""
    response = _admin_request('PUT', f'/users/{user_id}/reset-password', json={
        'type': 'password',
        'value': password,
        'temporary': False,
    })
    if response.status_code == 400:
        raise ValidationFailed(_validation_errors(_json(response)))
    if response.status_code not in (200, 204):
        logger.error('Keycloak reset-password failed: HTTP %s', response.status_code)
        raise KeycloakUnavailable(f'HTTP {response.status_code}')


def logout(refresh_token=None, id_token=None):
    """
    Завершает сессию пользователя в Keycloak: по refresh_token, а если его нет —
    по id_token (id_token_hint). Возвращает True, если Keycloak принял запрос.
    """
    if refresh_token:
        response = _request('POST', _logout_url(), data={
            **_client_credentials(),
            'refresh_token': refresh_token,
        })
    elif id_token:
        response = _request('POST', _logout_url(), data={
            'client_id': settings.OIDC_RP_CLIENT_ID,
            'id_token_hint': id_token,
        })
    else:
        return False
    return response.status_code < 400
