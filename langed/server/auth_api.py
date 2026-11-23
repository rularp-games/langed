"""
API авторизации без перехода в Keycloak: вход по почте и паролю, регистрация,
сброс пароля, выход. Keycloak остаётся хранилищем учётных записей.
"""
import logging

import requests
from django.conf import settings
from django.contrib.auth import login, logout
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.core.validators import validate_email
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import Throttled
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import keycloak
from .models import KeycloakIdentity
from .oidc import (
    SESSION_ID_TOKEN,
    SESSION_PASSWORD_LOGIN,
    SESSION_REFRESH_TOKEN,
    KeycloakOIDCAuthenticationBackend,
)
from .views import current_user

logger = logging.getLogger(__name__)

PASSWORD_MIN_LENGTH = 8
# Ограничение длины полей first_name / last_name модели пользователя
NAME_MAX_LENGTH = 150

# Вход по паролю — это сессия Langed, а не браузерная SSO-сессия Keycloak.
# С этим backend её не трогает mozilla_django_oidc.middleware.SessionRefresh
# (тихий повторный вход через Keycloak для такой сессии всегда неуспешен).
PASSWORD_LOGIN_BACKEND = 'django.contrib.auth.backends.ModelBackend'


class AuthError(Exception):
    """Ошибка авторизации с готовым телом ответа"""

    def __init__(self, code, detail, status_code=status.HTTP_400_BAD_REQUEST, errors=None):
        super().__init__(code)
        self.body = {'code': code, 'detail': detail}
        if errors is not None:
            self.body['errors'] = errors
        self.status_code = status_code


class CsrfSessionAuthentication(SessionAuthentication):
    """
    Сессионная аутентификация с проверкой CSRF и для анонимных запросов:
    стандартная SessionAuthentication проверяет CSRF только у вошедших пользователей,
    а вход и регистрацию вызывает как раз аноним.
    """

    def authenticate(self, request):
        self.enforce_csrf(request)
        user = getattr(request._request, 'user', None)
        if not user or not user.is_active:
            return None
        return (user, None)


class AuthAPIView(APIView):
    """Базовый класс эндпоинтов авторизации"""

    authentication_classes = [CsrfSessionAuthentication]
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]

    def handle_exception(self, exc):
        if isinstance(exc, AuthError):
            return Response(exc.body, status=exc.status_code)
        if isinstance(exc, Throttled):
            response = Response(
                {
                    'code': 'throttled',
                    'detail': 'Слишком много попыток. Повторите позже.',
                    'retry_after': exc.wait,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            if exc.wait:
                response['Retry-After'] = '%d' % exc.wait
            return response
        return super().handle_exception(exc)


def text_field(data, name, strip=True):
    """Строковое поле из тела запроса (пустая строка, если поля нет или оно не строка)"""
    value = data.get(name) if hasattr(data, 'get') else None
    if not isinstance(value, str):
        return ''
    return value.strip() if strip else value


def user_payload(request):
    """Объект пользователя — тот же, что отдаёт GET /api/auth/user/"""
    django_request = request._request
    method = django_request.method
    django_request.method = 'GET'
    try:
        return current_user(django_request).data
    finally:
        django_request.method = method


def password_login(request, email, password):
    """Вход по почте и паролю через Keycloak; при неудаче бросает AuthError"""
    unavailable = AuthError(
        'auth_unavailable',
        'Сервис авторизации недоступен. Попробуйте позже.',
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )
    try:
        token_info = keycloak.password_grant(email, password)
        user = KeycloakOIDCAuthenticationBackend().user_from_token_response(token_info)
    except keycloak.InvalidCredentials:
        raise AuthError('invalid_credentials', 'Неверная почта или пароль')
    except keycloak.AccountNotReady:
        raise AuthError(
            'account_not_ready',
            'Учётная запись настроена не полностью: подтвердите почту по ссылке из письма '
            'или завершите настройку учётной записи.',
        )
    except keycloak.AccountDisabled:
        raise AuthError('account_disabled', 'Учётная запись отключена')
    except keycloak.KeycloakError:
        raise unavailable
    except (requests.RequestException, SuspiciousOperation) as exc:
        # Не удалось проверить id_token или получить userinfo
        logger.error('Password login failed after token exchange: %s', exc)
        raise unavailable

    if user is None or not user.is_active:
        raise AuthError('account_disabled', 'Учётная запись отключена')

    django_request = request._request
    login(django_request, user, backend=PASSWORD_LOGIN_BACKEND)
    # Токены сохраняем после login(): при смене пользователя login() очищает сессию
    django_request.session[SESSION_ID_TOKEN] = token_info.get('id_token')
    django_request.session[SESSION_REFRESH_TOKEN] = token_info.get('refresh_token')
    django_request.session[SESSION_PASSWORD_LOGIN] = True
    return user


def auth_unavailable():
    return AuthError(
        'auth_unavailable',
        'Сервис авторизации недоступен. Попробуйте позже.',
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def keycloak_user_id(user):
    """Id пользователя в Keycloak (claim sub) или None, если учётная запись не привязана"""
    identity = KeycloakIdentity.objects.filter(user=user).first()
    return identity.sub if identity else None


class CurrentUserView(AuthAPIView):
    """Текущий пользователь (GET, заодно ставит CSRF cookie) и правка его имени (PATCH)"""

    throttle_classes = []

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsAuthenticated()]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response(user_payload(request))

    def patch(self, request):
        user = request.user
        errors = {}
        names = {}
        for field, label in (('first_name', 'Имя'), ('last_name', 'Фамилия')):
            if field not in request.data:
                names[field] = getattr(user, field)
                continue
            value = request.data.get(field)
            if not isinstance(value, str):
                errors[field] = ['Некорректное значение']
                continue
            names[field] = value.strip()
            if len(names[field]) > NAME_MAX_LENGTH:
                errors[field] = [f'{label} не длиннее {NAME_MAX_LENGTH} символов']
        if not errors and not names['first_name'] and not names['last_name']:
            errors['first_name'] = ['Укажите имя или фамилию']
        if errors:
            raise AuthError('validation_error', 'Проверьте заполнение полей', errors=errors)

        # Сначала Keycloak: при следующем входе имя берётся оттуда (update_user),
        # так что локальная правка без него была бы затёрта
        user_id = keycloak_user_id(user)
        if user_id:
            try:
                keycloak.update_user_name(user_id, names['first_name'], names['last_name'])
            except keycloak.ValidationFailed as exc:
                raise AuthError('validation_error', 'Проверьте заполнение полей', errors=exc.errors)
            except keycloak.KeycloakError:
                raise auth_unavailable()

        user.first_name = names['first_name']
        user.last_name = names['last_name']
        user.save(update_fields=['first_name', 'last_name'])
        return Response(user_payload(request))


class PasswordChangeView(AuthAPIView):
    """Смена пароля вошедшим по почте и паролю: проверка текущего пароля и запись нового в Keycloak"""

    permission_classes = [IsAuthenticated]
    throttle_scope = 'auth_login'

    def post(self, request):
        current_password = text_field(request.data, 'current_password', strip=False)
        new_password = text_field(request.data, 'new_password', strip=False)

        errors = {}
        if not current_password:
            errors['current_password'] = ['Укажите текущий пароль']
        if not new_password:
            errors['new_password'] = ['Укажите новый пароль']
        elif len(new_password) < PASSWORD_MIN_LENGTH:
            errors['new_password'] = [f'Пароль должен быть не короче {PASSWORD_MIN_LENGTH} символов']
        if errors:
            raise AuthError('validation_error', 'Проверьте заполнение полей', errors=errors)

        user_id = keycloak_user_id(request.user)
        if not user_id or not request._request.session.get(SESSION_PASSWORD_LOGIN):
            raise AuthError(
                'password_login_required',
                'Сменить пароль можно, только войдя по почте и паролю. '
                'Если вы входите через внешний сервис, пароль меняется в нём.',
            )

        try:
            # Проверка текущего пароля — тем же способом, что и вход
            token_info = keycloak.password_grant(request.user.email, current_password)
        except (keycloak.InvalidCredentials, keycloak.AccountNotReady, keycloak.AccountDisabled):
            raise AuthError(
                'invalid_credentials', 'Неверный текущий пароль',
                errors={'current_password': ['Неверный текущий пароль']},
            )
        except keycloak.KeycloakError:
            raise auth_unavailable()

        try:
            keycloak.reset_password(user_id, new_password)
        except keycloak.ValidationFailed as exc:
            # Парольная политика Keycloak
            messages = [message for field_messages in exc.errors.values() for message in field_messages]
            raise AuthError('validation_error', 'Проверьте заполнение полей', errors={'new_password': messages})
        except keycloak.KeycloakError:
            raise auth_unavailable()
        finally:
            # Сессия Keycloak, созданная проверкой пароля, больше не нужна
            try:
                keycloak.logout(refresh_token=token_info.get('refresh_token'))
            except keycloak.KeycloakError as exc:
                logger.warning('Keycloak logout after password check failed: %s', exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProvidersView(APIView):
    """Список внешних провайдеров входа"""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response([
            {'id': provider['id'], 'name': provider['name']}
            for provider in settings.AUTH_PROVIDERS
        ])


class LoginView(AuthAPIView):
    """Вход по почте и паролю"""

    throttle_scope = 'auth_login'

    def post(self, request):
        email = text_field(request.data, 'email')
        password = text_field(request.data, 'password', strip=False)

        errors = {}
        if not email:
            errors['email'] = ['Укажите почту']
        if not password:
            errors['password'] = ['Укажите пароль']
        if errors:
            raise AuthError('validation_error', 'Проверьте заполнение полей', errors=errors)

        password_login(request, email, password)
        return Response(user_payload(request))


class RegisterView(AuthAPIView):
    """Регистрация: создание пользователя в Keycloak и вход"""

    throttle_scope = 'auth_register'

    def post(self, request):
        email = text_field(request.data, 'email').lower()
        password = text_field(request.data, 'password', strip=False)
        first_name = text_field(request.data, 'first_name')
        last_name = text_field(request.data, 'last_name')

        errors = {}
        if not email:
            errors['email'] = ['Укажите почту']
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors['email'] = ['Некорректный адрес почты']
        if not password:
            errors['password'] = ['Укажите пароль']
        elif len(password) < PASSWORD_MIN_LENGTH:
            errors['password'] = [f'Пароль должен быть не короче {PASSWORD_MIN_LENGTH} символов']
        if not first_name:
            errors['first_name'] = ['Укажите имя']
        if not last_name:
            errors['last_name'] = ['Укажите фамилию']
        if errors:
            raise AuthError('validation_error', 'Проверьте заполнение полей', errors=errors)

        try:
            user_id = keycloak.create_user(email, password, first_name, last_name)
        except keycloak.EmailExists:
            raise AuthError('email_exists', 'Пользователь с такой почтой уже зарегистрирован')
        except keycloak.ValidationFailed as exc:
            raise AuthError('validation_error', 'Проверьте заполнение полей', errors=exc.errors)
        except keycloak.KeycloakError:
            raise AuthError(
                'auth_unavailable',
                'Сервис авторизации недоступен. Попробуйте позже.',
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Письмо подтверждения почты — не блокирует регистрацию и вход
        try:
            if user_id:
                keycloak.send_actions_email(user_id, ['VERIFY_EMAIL'])
        except keycloak.KeycloakError as exc:
            logger.warning('Failed to send verification email: %s', exc)

        password_login(request, email, password)
        return Response(user_payload(request), status=status.HTTP_201_CREATED)


class PasswordResetView(AuthAPIView):
    """Письмо со ссылкой на смену пароля. Ответ не зависит от того, есть ли такая почта."""

    throttle_scope = 'auth_password_reset'

    def post(self, request):
        email = text_field(request.data, 'email').lower()
        if email:
            try:
                token = keycloak.service_token()
                user_id = keycloak.find_user_id_by_email(email, token=token)
                if user_id:
                    keycloak.send_actions_email(user_id, ['UPDATE_PASSWORD'], token=token)
            except keycloak.KeycloakError as exc:
                logger.warning('Password reset email was not sent: %s', exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutView(AuthAPIView):
    """Выход из Langed и завершение сессии в Keycloak (если получится)"""

    throttle_classes = []

    def post(self, request):
        django_request = request._request
        refresh_token = django_request.session.get(SESSION_REFRESH_TOKEN)
        id_token = django_request.session.get(SESSION_ID_TOKEN)

        logout(django_request)

        try:
            keycloak.logout(refresh_token=refresh_token, id_token=id_token)
        except keycloak.KeycloakError as exc:
            logger.warning('Keycloak logout failed: %s', exc)
        return Response(status=status.HTTP_204_NO_CONTENT)
