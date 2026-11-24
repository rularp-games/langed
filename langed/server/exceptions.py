"""Ответы API на исключения, которые стандартный обработчик DRF не знает"""
from collections import Counter

from django.db.models import ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.response import Response


def related_objects_summary(objects):
    """Строка «Площадки: 2, Прогоны: 1» — типы связанных объектов и их количество"""
    counts = Counter(str(obj._meta.verbose_name_plural) for obj in objects)
    return ', '.join(f'{name}: {count}' for name, count in sorted(counts.items()))


def in_use_response(exc):
    """409 на удаление записи, на которую ссылаются другие (on_delete=PROTECT/RESTRICT)"""
    if isinstance(exc, ProtectedError):
        objects = exc.protected_objects
    elif isinstance(exc, RestrictedError):
        objects = exc.restricted_objects
    else:
        return None
    return Response(
        {
            'code': 'in_use',
            'detail': f'Нельзя удалить: есть связанные записи ({related_objects_summary(objects)})',
            'status_code': status.HTTP_409_CONFLICT,
        },
        status=status.HTTP_409_CONFLICT,
    )
