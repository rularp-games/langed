"""Настройки для тестов: без private_settings, секретов и внешних сервисов.

Запуск: DJANGO_SETTINGS_MODULE=langed.test_settings python manage.py test server
Этими настройками тесты гоняются при сборке образа (werf.yaml), где реальных секретов нет.
"""
import sys
import types

# settings.py берёт обязательные значения из langed.private_settings. Подставляем вместо него
# модуль с фиктивными значениями, чтобы настоящий файл (с секретами) не импортировался вовсе.
_KEYCLOAK_SERVER_URL = 'http://keycloak.test'
_KEYCLOAK_REALM = 'langed-test'
_OIDC_BASE = f'{_KEYCLOAK_SERVER_URL}/realms/{_KEYCLOAK_REALM}/protocol/openid-connect'

_private = types.ModuleType('langed.private_settings')
_private.SECRET_KEY = 'langed-test-secret-key'
_private.DEBUG = False
# Тесты ходят с разными Host / X-Forwarded-Host (проверка redirect_uri за прокси)
_private.ALLOWED_HOSTS = ['*']
_private.DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}
_private.KEYCLOAK_SERVER_URL = _KEYCLOAK_SERVER_URL
_private.KEYCLOAK_REALM = _KEYCLOAK_REALM
_private.OIDC_RP_CLIENT_ID = 'langed-test'
_private.OIDC_RP_CLIENT_SECRET = 'langed-test-client-secret'
_private.OIDC_OP_AUTHORIZATION_ENDPOINT = f'{_OIDC_BASE}/auth'
_private.OIDC_OP_TOKEN_ENDPOINT = f'{_OIDC_BASE}/token'
_private.OIDC_OP_USER_ENDPOINT = f'{_OIDC_BASE}/userinfo'
_private.OIDC_OP_JWKS_ENDPOINT = f'{_OIDC_BASE}/certs'
_private.OIDC_OP_LOGOUT_ENDPOINT = f'{_OIDC_BASE}/logout'
_private.SITE_URL = 'http://testserver'
_private.CSRF_TRUSTED_ORIGINS = ['http://testserver']
_private.SESSION_COOKIE_SECURE = False
_private.CSRF_COOKIE_SECURE = False
# Без Sentry и S3: события не отправляются, media — в локальном MEDIA_ROOT
_private.SENTRY_DSN = ''
_private.MEDIA_S3 = None
sys.modules['langed.private_settings'] = _private

from langed.settings import *  # noqa: E402,F401,F403

# Отдельный кэш в памяти процесса: троттлинг не зависит от таблицы кэша в БД
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}
