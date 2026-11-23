"""
OIDC/Keycloak utilities for authentication.
"""
import logging
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView,
    OIDCAuthenticationRequestView,
)

from .models import KeycloakIdentity

logger = logging.getLogger('mozilla_django_oidc')

# Ключи сессии
SESSION_NEXT = 'oidc_login_next'
SESSION_ID_TOKEN = 'oidc_id_token'
SESSION_REFRESH_TOKEN = 'oidc_refresh_token'
# Признак «вошёл по почте и паролю» (ставится при входе через /api/auth/login/)
SESSION_PASSWORD_LOGIN = 'password_login'

# Параметр, с которым пользователь возвращается на next при ошибке входа
AUTH_ERROR_PARAM = 'auth_error'

USERNAME_MAX_LENGTH = 150


def allowed_idp_aliases():
    """Alias провайдеров, которые разрешено передавать в kc_idp_hint"""
    return {provider['id'] for provider in getattr(settings, 'AUTH_PROVIDERS', [])}


def safe_next_path(next_url):
    """
    Возвращает next_url, только если это относительный путь внутри сайта
    (защита от open redirect), иначе None.
    """
    if not next_url or not isinstance(next_url, str):
        return None
    if not next_url.startswith('/') or next_url.startswith('//') or '\\' in next_url:
        return None
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts=None):
        return None
    return next_url


def add_auth_error(url, code):
    """Добавляет к адресу параметр auth_error=<code>"""
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key != AUTH_ERROR_PARAM]
    query.append((AUTH_ERROR_PARAM, code))
    return urlunsplit(('', '', parts.path or '/', urlencode(query), parts.fragment))


class KeycloakAuthenticationRequestView(OIDCAuthenticationRequestView):
    """
    Начало входа через Keycloak: /oidc/authenticate/?idp=<alias>&next=<путь>.
    idp передаётся в Keycloak как kc_idp_hint — пользователь сразу попадает
    к внешнему провайдеру, минуя страницу входа Keycloak.
    """

    def get_extra_params(self, request):
        params = dict(super().get_extra_params(request))
        idp = request.GET.get('idp')
        if idp and idp in allowed_idp_aliases():
            params['kc_idp_hint'] = idp
        return params

    def get(self, request):
        response = super().get(request)
        # Базовый класс допускает абсолютные ссылки на свой хост — оставляем только относительные пути
        redirect_field_name = self.get_settings('OIDC_REDIRECT_FIELD_NAME', 'next')
        request.session[SESSION_NEXT] = safe_next_path(request.GET.get(redirect_field_name))
        return response


class SafeOIDCCallbackView(OIDCAuthenticationCallbackView):
    """
    Callback OIDC: при любой ошибке (отказ пользователя, просроченный state,
    недоступность Keycloak) возвращает на next с ?auth_error=<code>.
    Повторный вход автоматически не запускается, чтобы не получить бесконечный цикл.
    """

    error_code = 'auth_failed'

    @property
    def failure_url(self):
        return add_auth_error(self.next_path or '/', self.error_code)

    def get(self, request):
        self.next_path = safe_next_path(request.session.get(SESSION_NEXT))

        error = request.GET.get('error')
        if error:
            # Код ошибки от Keycloak (access_denied, login_required и т.п.)
            self.error_code = error if re.fullmatch(r'[a-z_]{1,64}', error) else 'auth_failed'
        elif 'code' in request.GET and 'state' in request.GET and 'oidc_states' not in request.session:
            self.error_code = 'invalid_state'

        try:
            return super().get(request)
        except SuspiciousOperation as e:
            # State не найден в сессии — просрочен или вкладка слишком долго была в фоне
            logger.warning(f"OIDC callback state error: {e}")
            self.error_code = 'invalid_state'
        except requests.RequestException as e:
            logger.error(f"OIDC callback failed, Keycloak request error: {e}")
            self.error_code = 'auth_unavailable'
        return self.login_failure()


def generate_username(claims):
    """
    Generate a username from Keycloak claims.
    Uses 'preferred_username' from Keycloak token claims.
    Falls back to email or subject ID if preferred_username is not available.
    """
    # Try preferred_username first (standard Keycloak claim)
    if claims.get('preferred_username'):
        return claims['preferred_username']

    # Fallback to email
    if claims.get('email'):
        return claims['email'].split('@')[0]

    # Last resort: use the subject ID
    return claims.get('sub', '')


class KeycloakOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """
    Custom OIDC authentication backend for Keycloak.

    Пользователь ищется по claim sub (модель KeycloakIdentity). Этот же путь
    используется и для соцвхода (callback), и для входа по паролю
    (user_from_token_response).
    """

    def unique_username(self, claims):
        """Username из claims; при коллизии добавляется числовой суффикс."""
        base = generate_username(claims)[:USERNAME_MAX_LENGTH]
        username = base
        suffix = 2
        while self.UserModel.objects.filter(username=username).exists():
            tail = f'-{suffix}'
            username = f'{base[:USERNAME_MAX_LENGTH - len(tail)]}{tail}'
            suffix += 1
        return username

    def filter_users_by_claims(self, claims):
        """
        Ищет пользователя по sub. Если привязки ещё нет — подбирает пользователя
        без привязки: по username (разово, для заведённых до появления
        KeycloakIdentity) или по почте, подтверждённой в Keycloak.
        """
        sub = claims.get('sub')
        users = self.UserModel.objects.filter(keycloak_identity__sub=sub)
        if users.exists():
            return users

        unlinked = self.UserModel.objects.filter(keycloak_identity__isnull=True)

        # Старые пользователи: создавались с username == preferred_username.
        # Локальные учётки с паролем (createsuperuser) так не привязываются.
        username = claims.get('preferred_username')
        if username and getattr(settings, 'OIDC_LEGACY_USERNAME_LINK', True):
            for user in unlinked.filter(username=username):
                if not user.has_usable_password():
                    logger.info(f"Linking legacy user by username: {username}")
                    return self.UserModel.objects.filter(pk=user.pk)

        # По почте — только если Keycloak подтвердил, что она принадлежит пользователю
        email = claims.get('email')
        if email and claims.get('email_verified') is True:
            users = unlinked.filter(email__iexact=email)
            if users.count() == 1:
                logger.info(f"Linking user by verified email: {users[0].username}")
                return users

        return self.UserModel.objects.none()

    def create_user(self, claims):
        """Create a new user from Keycloak claims."""
        try:
            with transaction.atomic():
                user = self.UserModel.objects.create_user(
                    username=self.unique_username(claims),
                    email=claims.get('email', ''),
                    first_name=claims.get('given_name', ''),
                    last_name=claims.get('family_name', ''),
                )
                KeycloakIdentity.objects.create(user=user, sub=claims['sub'])
        except IntegrityError:
            # Параллельный вход того же пользователя уже создал учётку
            return self.UserModel.objects.get(keycloak_identity__sub=claims['sub'])

        logger.info(f"Created new user: {user.username}")
        return user

    def update_user(self, user, claims):
        """Update existing user with latest Keycloak claims."""
        KeycloakIdentity.objects.get_or_create(user=user, defaults={'sub': claims['sub']})

        user.email = claims.get('email', user.email)
        user.first_name = claims.get('given_name', user.first_name)
        user.last_name = claims.get('family_name', user.last_name)
        user.save()
        return user

    def verify_claims(self, claims):
        """Verify the claims are valid."""
        # Check that we have required claims
        if not claims.get('sub'):
            logger.error("Missing 'sub' claim")
            return False

        return True

    def get_token(self, payload):
        """Запоминает refresh token — он нужен для завершения сессии в Keycloak при выходе."""
        token_info = super().get_token(payload)
        self.refresh_token = token_info.get('refresh_token')
        return token_info

    def store_tokens(self, access_token, id_token):
        super().store_tokens(access_token, id_token)
        refresh_token = getattr(self, 'refresh_token', None)
        if refresh_token:
            self.request.session[SESSION_REFRESH_TOKEN] = refresh_token

    def user_from_token_response(self, token_info):
        """
        Возвращает пользователя по ответу token endpoint (вход по паролю).
        Токен проверяется и пользователь создаётся/обновляется так же,
        как при входе через callback.
        """
        id_token = token_info.get('id_token')
        access_token = token_info.get('access_token')
        # При grant_type=password nonce не передаётся — в токене его тоже нет
        payload = self.verify_token(id_token, nonce=None)
        return self.get_or_create_user(access_token, id_token, payload)
