from mcp_server import ModelQueryToolset

from .models import (
    Region,
    City,
    Game,
    Convention,
    ConventionLink,
    ConventionEvent,
    Venue,
    Room,
    Run,
    CommonEvent,
    Registration,
    ConventionEventRegistration,
)


class RegionTool(ModelQueryToolset):
    model = Region


class CityTool(ModelQueryToolset):
    model = City
    extra_instructions = 'Города с привязкой к региону и часовому поясу.'


class GameTool(ModelQueryToolset):
    model = Game
    search_fields = ['name', 'announcement']
    extra_instructions = 'Каталог настольных ролевых игр с лимитами игроков и ролей.'


class ConventionTool(ModelQueryToolset):
    model = Convention
    search_fields = ['name', 'description']


class ConventionLinkTool(ModelQueryToolset):
    model = ConventionLink
    extra_instructions = 'Внешние ссылки конвента (VK, Telegram, сайт и т.д.).'


class ConventionEventTool(ModelQueryToolset):
    model = ConventionEvent
    extra_instructions = (
        'Конкретное проведение конвента в городе: даты, площадка, лимит участников, '
        'статус регистрации.'
    )


class VenueTool(ModelQueryToolset):
    model = Venue
    search_fields = ['name', 'address', 'description']


class RoomTool(ModelQueryToolset):
    model = Room
    extra_instructions = 'Помещения на площадке; blackbox=True — универсальная комната без фиксированной декорации.'


class RunTool(ModelQueryToolset):
    model = Run
    extra_instructions = (
        'Сеанс (прогон) игры: дата, длительность, мастера, помещения, '
        'привязка к проведению конвента, лимит игроков.'
    )


class CommonEventTool(ModelQueryToolset):
    model = CommonEvent
    extra_instructions = 'Общие события расписания конвента (ужин, заезд и т.п.), видны во всех помещениях площадки.'


class RegistrationTool(ModelQueryToolset):
    model = Registration
    extra_instructions = 'Регистрация игрока на прогон игры.'


class ConventionEventRegistrationTool(ModelQueryToolset):
    model = ConventionEventRegistration
    extra_instructions = 'Регистрация участника на проведение конвента.'
