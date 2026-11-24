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


def choices_list_param(request, name, choices):
    """
    Параметр запроса — одно значение или список через запятую из фиксированного набора
    (?kind=larp,ttrpg). None, если не передан: фильтр не применяется.
    """
    value = request.query_params.get(name)
    if value is None:
        return None
    values = [item.strip() for item in value.split(',') if item.strip()]
    if not values:
        return None
    unknown = [item for item in values if item not in choices]
    if unknown:
        raise ValidationError({name: f'Допустимые значения: {", ".join(choices)}'})
    return values


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
