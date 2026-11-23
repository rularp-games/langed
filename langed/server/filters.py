"""
Разбор параметров фильтрации списков и вспомогательные выражения для запросов
"""
from django.db.models import Count, IntegerField, OuterRef, Subquery
from django.db.models.functions import Coalesce
from rest_framework.exceptions import ValidationError

TRUE_VALUES = {'1', 'true', 'yes', 'on'}


def int_param(request, name):
    """Целочисленный параметр запроса (None, если не передан)"""
    value = request.query_params.get(name)
    if value is None or value == '':
        return None
    try:
        return int(value)
    except ValueError:
        raise ValidationError({name: 'Ожидается целое число'})


def bool_param(request, name):
    """Параметр-флаг запроса (1/true/yes/on)"""
    return request.query_params.get(name, '').lower() in TRUE_VALUES


def choice_param(request, name, choices, default):
    """Параметр запроса с фиксированным набором значений"""
    value = request.query_params.get(name)
    if value is None or value == '':
        return default
    if value not in choices:
        raise ValidationError({name: f'Допустимые значения: {", ".join(choices)}'})
    return value


def count_subquery(queryset, outer_field):
    """
    Счётчик связанных объектов подзапросом: не размножает строки основного
    запроса и не зависит от остальных фильтров.
    """
    return Coalesce(
        Subquery(
            queryset.filter(**{outer_field: OuterRef('pk')})
            .order_by()
            .values(outer_field)
            .annotate(total=Count('pk'))
            .values('total'),
            output_field=IntegerField(),
        ),
        0,
    )
