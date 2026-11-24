import datetime

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone as django_timezone
from .models import (
    Game, Run, Convention, ConventionEvent, City, ConventionLink, Region, Venue, Room, Registration,
    CommonEvent, ConventionEventRegistration, date_outside_event_error
)

User = get_user_model()


class NaiveDateTimeField(serializers.DateTimeField):
    """
    DateTimeField, который не добавляет таймзону автоматически.
    Позволяет обработать таймзону вручную в validate методе сериализатора.
    """
    def default_timezone(self):
        return None

    def enforce_timezone(self, value):
        # Значение с таймзоной сохраняем как есть (иначе DRF отбросил бы таймзону и оно
        # было бы принято за локальное время города); без таймзоны — обработает validate
        return value

    def to_representation(self, value):
        # Наружу отдаём UTC с суффиксом Z (как created_at): строку без таймзоны
        # браузер прочитал бы как локальное время
        if value is not None and django_timezone.is_aware(value):
            return value.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
        return super().to_representation(value)


EXCERPT_LENGTH = 200
# Сколько символов анонса забирать из БД для построения выдержки в списке
EXCERPT_SOURCE_LENGTH = 400


def make_excerpt(text, limit=EXCERPT_LENGTH, truncated=False):
    """
    Короткая выдержка из текста: не длиннее limit символов, без обрыва слова.
    truncated — исходный текст уже был обрезан (например, при выборке из БД).
    """
    text = ' '.join((text or '').split())
    if len(text) <= limit:
        return f'{text}…' if truncated and text else text
    cut = text[:limit]
    if text[limit] != ' ' and ' ' in cut:
        cut = cut.rsplit(' ', 1)[0]
    return f'{cut.rstrip(" ,;:—-")}…'


def get_request_user(serializer):
    """Аутентифицированный пользователь текущего запроса (или None)"""
    request = serializer.context.get('request')
    if not request or not request.user.is_authenticated:
        return None
    return request.user


def is_event_organizer(user, event):
    """
    Является ли пользователь организатором проведения или его конвента.
    В списках используется аннотация _user_is_organizer (без запросов на каждый объект).
    """
    flag = getattr(event, '_user_is_organizer', None)
    if flag is not None:
        return flag
    return user in event.organizers.all() or user in event.convention.organizers.all()


def can_manage_event(user, event):
    """Может ли пользователь редактировать проведение и управлять заявками на него"""
    if user is None or not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    return is_event_organizer(user, event)


def can_manage_run_registrations(user, run):
    """Может ли пользователь управлять заявками на прогон (подтверждать/отклонять)"""
    if user is None or not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    # Может управлять мастер прогона
    if user in run.masters.all():
        return True
    # Или организатор конвента (если игра на конвенте)
    flag = getattr(run, '_user_is_event_organizer', None)
    if flag is not None:
        return flag
    if run.convention_event:
        return is_event_organizer(user, run.convention_event)
    return False


def get_display_name(user):
    """Отображаемое имя пользователя"""
    if user.first_name or user.last_name:
        return f'{user.first_name} {user.last_name}'.strip()
    return user.username


class UserBriefSerializer(serializers.ModelSerializer):
    """
    Краткий сериализатор пользователя с username.
    Только для данных, которые видит сам пользователь или тот, кто управляет заявками.
    """
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name']

    def get_display_name(self, obj):
        return get_display_name(obj)


class UserPublicSerializer(serializers.ModelSerializer):
    """Публичный сериализатор пользователя (мастера, авторы, организаторы): без username"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'display_name']

    def get_display_name(self, obj):
        return get_display_name(obj)


class RunCountersMixin:
    """
    Счётчики мест прогона. В списках берутся из аннотации _registered_count,
    иначе считаются одним запросом на объект.
    """

    def _registered(self, obj):
        count = getattr(obj, '_registered_count', None)
        if count is None:
            cache = self.__dict__.setdefault('_registered_cache', {})
            if obj.pk not in cache:
                cache[obj.pk] = obj.get_registered_count()
            count = cache[obj.pk]
        return count

    def get_registered_count(self, obj):
        """Количество зарегистрированных игроков"""
        return self._registered(obj)

    def get_available_slots(self, obj):
        """Количество свободных мест (None — лимита нет)"""
        max_players = obj.get_max_players()
        if max_players is None:
            return None
        return max(0, max_players - self._registered(obj))

    def get_is_full(self, obj):
        """Заполнен ли прогон (без лимита — никогда)"""
        return self.get_available_slots(obj) == 0

    def get_effective_max_players(self, obj):
        """Эффективный максимум игроков (None — лимита нет)"""
        return obj.get_max_players()


class EventCountersMixin:
    """
    Счётчики регистраций проведения конвента. В списках берутся из аннотаций
    _confirmed_count / _pending_count, иначе считаются одним запросом на объект.
    """

    def _status_count(self, obj, status):
        count = getattr(obj, f'_{status}_count', None)
        if count is None:
            cache = self.__dict__.setdefault('_status_count_cache', {})
            key = (obj.pk, status)
            if key not in cache:
                cache[key] = obj.event_registrations.filter(status=status).count()
            count = cache[key]
        return count

    def get_registrations_count(self, obj):
        """Количество подтверждённых регистраций"""
        return self._status_count(obj, 'confirmed')

    def get_pending_registrations_count(self, obj):
        """Количество ожидающих регистраций"""
        return self._status_count(obj, 'pending')

    def get_available_slots(self, obj):
        """Количество свободных мест (None если без ограничений)"""
        if obj.capacity is None:
            return None
        return max(0, obj.capacity - self._status_count(obj, 'confirmed'))

    def get_is_full(self, obj):
        """Заполнен ли конвент"""
        if obj.capacity is None:
            return False
        return self.get_available_slots(obj) == 0

    def get_can_edit(self, obj):
        """Проверяем, может ли текущий пользователь редактировать проведение"""
        return can_manage_event(get_request_user(self), obj)

    def get_current_user_registration(self, obj):
        """Регистрация текущего пользователя на этот конвент"""
        user = get_request_user(self)
        if user is None:
            return None
        prefetched = getattr(obj, '_my_registrations', None)
        if prefetched is not None:
            registration = prefetched[0] if prefetched else None
        else:
            registration = obj.event_registrations.filter(user=user).select_related('user').first()
        if registration is None:
            return None
        return ConventionEventRegistrationBriefSerializer(registration, context=self.context).data


class RegionSerializer(serializers.ModelSerializer):
    """Сериализатор региона"""
    class Meta:
        model = Region
        fields = ['id', 'name']


class CitySerializer(serializers.ModelSerializer):
    region = RegionSerializer(read_only=True)
    
    class Meta:
        model = City
        fields = ['id', 'name', 'region', 'timezone']

    def validate_name(self, value):
        """Название города уникально без учёта регистра"""
        value = value.strip()
        cities = City.objects.all()
        if self.instance is not None:
            cities = cities.exclude(pk=self.instance.pk)
        # Сравниваем в Python: в SQLite iexact не учитывает регистр кириллицы
        folded = value.casefold()
        if any(name.casefold() == folded for name in cities.values_list('name', flat=True)):
            raise serializers.ValidationError('Город с таким названием уже есть')
        return value


class RoomSerializer(serializers.ModelSerializer):
    """Сериализатор помещения"""
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(),
        source='venue'
    )
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    
    class Meta:
        model = Room
        fields = ['id', 'venue_id', 'venue_name', 'name', 'blackbox', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoomBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор помещения"""
    venue_id = serializers.IntegerField(read_only=True)
    # Площадку помещения загружают заранее (select_related / prefetch) все места использования
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'name', 'blackbox', 'venue_id', 'venue_name']


class VenueSerializer(serializers.ModelSerializer):
    """Сериализатор площадки"""
    city = CitySerializer(read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True
    )
    rooms = RoomBriefSerializer(many=True, read_only=True)
    
    class Meta:
        model = Venue
        fields = ['id', 'name', 'address', 'city', 'city_id', 'description', 'capacity', 'rooms', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class VenueBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор площадки"""
    class Meta:
        model = Venue
        fields = ['id', 'name', 'address']


class GameListSerializer(serializers.ModelSerializer):
    """Лёгкий сериализатор игры для списка (без полных текстов анонса и красных флагов)"""
    creators = UserPublicSerializer(many=True, read_only=True)
    announcement_excerpt = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            'id', 'name', 'creators', 'authors_text', 'source_url', 'poster', 'announcement_excerpt',
            'players_min', 'players_max',
            'female_roles_min', 'female_roles_max',
            'male_roles_min', 'male_roles_max',
            'technicians', 'can_edit'
        ]

    def get_announcement_excerpt(self, obj):
        """Первые ~200 символов анонса без обрыва слова"""
        head = getattr(obj, '_announcement_head', None)
        if head is None:
            return make_excerpt(obj.announcement)
        return make_excerpt(head, truncated=len(head) >= EXCERPT_SOURCE_LENGTH)

    def get_can_edit(self, obj):
        """Проверяем, может ли текущий пользователь редактировать игру"""
        user = get_request_user(self)
        if user is None:
            return False
        if user.is_staff:
            return True
        return user in obj.creators.all()


class GameCompactSerializer(serializers.ModelSerializer):
    """Компактный сериализатор игры для карточки прогона"""
    class Meta:
        model = Game
        fields = ['id', 'name', 'poster']


POSTER_MAX_SIZE = 5 * 1024 * 1024
POSTER_CONTENT_TYPES = ('image/jpeg', 'image/png', 'image/webp')

# Диапазоны «минимум — максимум» игры: префикс полей → текст ошибки
RANGE_ERRORS = {
    'players': 'Максимум игроков не может быть меньше минимума',
    'female_roles': 'Максимум женских ролей не может быть меньше минимума',
    'male_roles': 'Максимум мужских ролей не может быть меньше минимума',
}


class GameSerializer(serializers.ModelSerializer):
    poster_url = serializers.SerializerMethodField()
    creators = UserPublicSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = [
            'id', 'name', 'creators', 'authors_text', 'source_url',
            'poster', 'poster_url', 'announcement', 'red_flags',
            'players_min', 'players_max',
            'female_roles_min', 'female_roles_max',
            'male_roles_min', 'male_roles_max',
            'technicians',
            'can_edit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'creators', 'created_at', 'updated_at', 'poster_url', 'can_edit']
    
    def get_poster_url(self, obj):
        if obj.poster:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.poster.url)
            return obj.poster.url
        return None
    
    def get_can_edit(self, obj):
        """Проверяем, может ли текущий пользователь редактировать игру"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.user in obj.creators.all()

    def validate_poster(self, value):
        """Постер — JPEG, PNG или WebP не больше 5 МБ"""
        if not value:
            return value
        if value.size > POSTER_MAX_SIZE:
            raise serializers.ValidationError('Размер файла не должен превышать 5 МБ')
        # content_type выставлен по фактическому формату изображения (Pillow), а не по заголовку запроса
        if getattr(value, 'content_type', None) not in POSTER_CONTENT_TYPES:
            raise serializers.ValidationError('Постер должен быть в формате JPEG, PNG или WebP')
        return value

    def validate(self, attrs):
        """
        Минимум не больше максимума — для игроков, женских и мужских ролей.
        Незаполненная граница (null — не указано) не сравнивается.
        """
        def current(field_name):
            # Значение из запроса, иначе сохранённое (у новой игры — не указано)
            if field_name in attrs:
                return attrs[field_name]
            if self.instance is not None:
                return getattr(self.instance, field_name)
            return None

        errors = {}
        for prefix, message in RANGE_ERRORS.items():
            low, high = current(f'{prefix}_min'), current(f'{prefix}_max')
            if low is not None and high is not None and low > high:
                errors[f'{prefix}_max'] = [message]
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class GameBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор игры"""
    class Meta:
        model = Game
        fields = ['id', 'name', 'players_min', 'players_max']


class ConventionLinkSerializer(serializers.ModelSerializer):
    """Сериализатор ссылки конвента"""
    display_title = serializers.SerializerMethodField()
    link_type_display = serializers.CharField(source='get_link_type_display', read_only=True)
    convention_id = serializers.PrimaryKeyRelatedField(
        queryset=Convention.objects.all(),
        source='convention'
    )
    
    class Meta:
        model = ConventionLink
        fields = ['id', 'convention_id', 'url', 'link_type', 'link_type_display', 'title', 'display_title']
        read_only_fields = ['id']
    
    def get_display_title(self, obj):
        return obj.get_display_title()


class ConventionSerializer(serializers.ModelSerializer):
    """Сериализатор конвента (без дат - просто справочник)"""
    organizers = UserPublicSerializer(many=True, read_only=True)
    events_count = serializers.SerializerMethodField()
    links = ConventionLinkSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = Convention
        fields = [
            'id', 'name', 'organizers', 'description', 'source_url', 'events_count', 'links',
            'can_edit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organizers', 'created_at', 'updated_at', 'can_edit']

    def get_events_count(self, obj):
        """Количество проведений конвента"""
        count = getattr(obj, '_events_count', None)
        if count is None:
            count = obj.events.count()
        return count

    def get_can_edit(self, obj):
        """Проверяем, может ли текущий пользователь редактировать конвент"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.user in obj.organizers.all()


class RunBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор прогона для вложения в проведение конвента"""
    game_name = serializers.CharField(source='game.name', read_only=True)
    
    class Meta:
        model = Run
        fields = ['id', 'game_name', 'date']


class ScheduleRunSerializer(RunCountersMixin, serializers.ModelSerializer):
    """Сериализатор прогона для расписания конвента"""
    game = GameBriefSerializer(read_only=True)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.all(),
        source='game',
        write_only=True
    )
    game_name = serializers.CharField(source='game.name', read_only=True)
    masters = UserPublicSerializer(many=True, read_only=True)
    rooms = RoomBriefSerializer(many=True, read_only=True)
    room_ids = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        source='rooms',
        write_only=True,
        many=True,
        required=False
    )
    city_timezone = serializers.CharField(source='city.timezone', read_only=True)
    date_local = serializers.SerializerMethodField()
    # Используем NaiveDateTimeField чтобы DRF не добавлял UTC автоматически
    date = NaiveDateTimeField()
    registered_count = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    effective_max_players = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_manage_registrations = serializers.SerializerMethodField()
    
    class Meta:
        model = Run
        fields = [
            'id', 'game', 'game_id', 'game_name', 'masters', 
            'date', 'date_local', 'duration', 'city_timezone',
            'rooms', 'room_ids',
            'max_players', 'registration_open',
            'registered_count', 'available_slots', 'is_full', 
            'effective_max_players', 'can_edit', 'can_manage_registrations'
        ]
        read_only_fields = ['id', 'masters', 'can_edit', 'can_manage_registrations']
    
    def get_date_local(self, obj):
        """Возвращает дату и время в локальной таймзоне города"""
        import pytz
        if obj.date and obj.city and obj.city.timezone:
            try:
                tz = pytz.timezone(obj.city.timezone)
                local_dt = obj.date.astimezone(tz)
                return local_dt.strftime('%Y-%m-%dT%H:%M:%S')
            except Exception:
                pass
        return obj.date.isoformat() if obj.date else None
    
    def validate_date(self, value):
        """
        Конвертирует локальное время в UTC с учётом таймзоны города.
        Дата приходит с фронтенда в формате без таймзоны (например 2026-01-15T14:00:00),
        интерпретируется как локальное время в таймзоне города конвента.
        """
        import pytz
        from django.utils import timezone as django_timezone
        
        # Если дата уже aware (с таймзоной), возвращаем как есть
        if django_timezone.is_aware(value):
            return value
        
        # Получаем таймзону из контекста (передаётся явно из view)
        city_timezone = self.context.get('city_timezone')
        
        # Если нет в контексте, пробуем из существующего прогона
        if not city_timezone and self.instance and self.instance.city:
            city_timezone = self.instance.city.timezone
        
        if city_timezone:
            try:
                tz = pytz.timezone(city_timezone)
                # Интерпретируем naive datetime как локальное время в этой таймзоне
                local_dt = tz.localize(value)
                # Конвертируем в UTC
                return local_dt.astimezone(pytz.UTC)
            except Exception:
                pass
        
        # Если не удалось определить таймзону, используем дефолтную (Москва)
        try:
            default_tz = pytz.timezone('Europe/Moscow')
            local_dt = default_tz.localize(value)
            return local_dt.astimezone(pytz.UTC)
        except Exception:
            return value
    
    def validate(self, attrs):
        """Проверяем, что дата прогона попадает в даты проведения конвента"""
        # Получаем convention_event из контекста view (add_run передаёт его при save)
        # Для update_run проверяем существующий instance
        convention_event = None
        if self.instance and self.instance.convention_event:
            convention_event = self.instance.convention_event
        
        date_value = attrs.get('date')
        if convention_event and date_value:
            error = date_outside_event_error(date_value, convention_event, 'прогона')
            if error:
                raise serializers.ValidationError({'date': error})
        
        return attrs

    def get_can_edit(self, obj):
        # Может редактировать мастер прогона или организатор конвента
        return can_manage_run_registrations(get_request_user(self), obj)

    def get_can_manage_registrations(self, obj):
        """Может ли пользователь управлять заявками на прогон (подтверждать/отклонять)"""
        return can_manage_run_registrations(get_request_user(self), obj)


class CommonEventSerializer(serializers.ModelSerializer):
    """Сериализатор общего события расписания"""
    convention_event_id = serializers.PrimaryKeyRelatedField(
        queryset=ConventionEvent.objects.all(),
        source='convention_event',
        write_only=True,
        required=False
    )
    date_local = serializers.SerializerMethodField()
    # Используем NaiveDateTimeField чтобы DRF не добавлял UTC автоматически
    date = NaiveDateTimeField()
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = CommonEvent
        fields = [
            'id', 'convention_event_id', 'name', 'date', 'date_local', 
            'duration', 'description', 'can_edit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'can_edit']
    
    def get_date_local(self, obj):
        """Возвращает дату и время в локальной таймзоне города"""
        import pytz
        city = obj.convention_event.city if obj.convention_event else None
        if obj.date and city and city.timezone:
            try:
                tz = pytz.timezone(city.timezone)
                local_dt = obj.date.astimezone(tz)
                return local_dt.strftime('%Y-%m-%dT%H:%M:%S')
            except Exception:
                pass
        return obj.date.isoformat() if obj.date else None
    
    def validate_date(self, value):
        """
        Конвертирует локальное время в UTC с учётом таймзоны города.
        """
        import pytz
        from django.utils import timezone as django_timezone
        
        # Если дата уже aware (с таймзоной), возвращаем как есть
        if django_timezone.is_aware(value):
            return value
        
        # Получаем таймзону из контекста (передаётся явно из view)
        city_timezone = self.context.get('city_timezone')
        
        # Если нет в контексте, пробуем из существующего события
        if not city_timezone and self.instance and self.instance.convention_event:
            city_timezone = self.instance.convention_event.city.timezone
        
        if city_timezone:
            try:
                tz = pytz.timezone(city_timezone)
                # Интерпретируем naive datetime как локальное время в этой таймзоне
                local_dt = tz.localize(value)
                # Конвертируем в UTC
                return local_dt.astimezone(pytz.UTC)
            except Exception:
                pass
        
        # Если не удалось определить таймзону, используем дефолтную (Москва)
        try:
            default_tz = pytz.timezone('Europe/Moscow')
            local_dt = default_tz.localize(value)
            return local_dt.astimezone(pytz.UTC)
        except Exception:
            return value
    
    def validate(self, attrs):
        """Проверяем, что дата события попадает в даты проведения конвента"""
        convention_event = attrs.get('convention_event')
        if not convention_event and self.instance:
            convention_event = self.instance.convention_event
        
        date_value = attrs.get('date')
        if convention_event and date_value:
            error = date_outside_event_error(date_value, convention_event, 'события')
            if error:
                raise serializers.ValidationError({'date': error})
        
        return attrs
    
    def get_can_edit(self, obj):
        # Может редактировать организатор проведения или конвента
        if not obj.convention_event:
            return False
        return can_manage_event(get_request_user(self), obj.convention_event)


class ConventionScheduleSerializer(EventCountersMixin, serializers.ModelSerializer):
    """Сериализатор расписания проведения конвента"""
    convention = serializers.PrimaryKeyRelatedField(read_only=True)
    convention_name = serializers.CharField(source='convention.name', read_only=True)
    convention_description = serializers.CharField(source='convention.description', read_only=True)
    city = CitySerializer(read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    city_timezone = serializers.CharField(source='city.timezone', read_only=True)
    venue = VenueBriefSerializer(read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True, allow_null=True)
    venue_rooms = serializers.SerializerMethodField()
    organizers = UserPublicSerializer(many=True, read_only=True)
    convention_organizers = UserPublicSerializer(source='convention.organizers', many=True, read_only=True)
    links = serializers.SerializerMethodField()
    runs = ScheduleRunSerializer(source='scheduled_runs', many=True, read_only=True)
    common_events = CommonEventSerializer(many=True, read_only=True)
    venues = serializers.SerializerMethodField()
    games = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    # Поля регистрации на конвент
    registration_open = serializers.BooleanField(read_only=True)
    capacity = serializers.IntegerField(read_only=True, allow_null=True)
    registrations_count = serializers.SerializerMethodField()
    pending_registrations_count = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    current_user_registration = serializers.SerializerMethodField()
    
    class Meta:
        model = ConventionEvent
        fields = [
            'id', 'convention', 'convention_name', 'convention_description',
            'city', 'city_name', 'city_timezone', 'date_start', 'date_end',
            'venue', 'venue_name', 'venue_rooms',
            'organizers', 'convention_organizers', 'links',
            'runs', 'common_events', 'venues', 'games', 'can_edit', 'source_url',
            # Поля регистрации
            'registration_open', 'capacity', 'registrations_count', 
            'pending_registrations_count', 'available_slots', 'is_full',
            'current_user_registration'
        ]
    
    def get_links(self, obj):
        return ConventionLinkSerializer(obj.convention.links.all(), many=True, context=self.context).data
    
    def get_venue_rooms(self, obj):
        """Получить помещения площадки конвента"""
        if obj.venue:
            return RoomBriefSerializer(obj.venue.rooms.all(), many=True, context=self.context).data
        return []
    
    def get_venues(self, obj):
        """Получить уникальные площадки из всех прогонов конвента (через помещения)"""
        venues = set()
        for run in obj.scheduled_runs.all():
            for room in run.rooms.all():
                venues.add(room.venue)
        return VenueBriefSerializer(list(venues), many=True, context=self.context).data
    
    def get_games(self, obj):
        """Получить уникальные игры из всех прогонов конвента"""
        games = {run.game for run in obj.scheduled_runs.all()}
        return GameBriefSerializer(list(games), many=True, context=self.context).data


class ConventionEventListSerializer(EventCountersMixin, serializers.ModelSerializer):
    """Лёгкий сериализатор проведения конвента для списка (без вложенных прогонов и игр)"""
    convention = serializers.PrimaryKeyRelatedField(read_only=True)
    convention_name = serializers.CharField(source='convention.name', read_only=True)
    city = CitySerializer(read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    venue = VenueBriefSerializer(read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True, allow_null=True)
    runs_count = serializers.SerializerMethodField()
    registrations_count = serializers.SerializerMethodField()
    pending_registrations_count = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    current_user_registration = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = ConventionEvent
        fields = [
            'id', 'convention', 'convention_name',
            'city', 'city_name',
            'venue', 'venue_name',
            'date_start', 'date_end',
            'capacity', 'registration_open',
            'runs_count',
            'registrations_count', 'pending_registrations_count',
            'available_slots', 'is_full', 'current_user_registration',
            'can_edit'
        ]

    def get_runs_count(self, obj):
        """Количество прогонов в расписании"""
        count = getattr(obj, '_runs_count', None)
        if count is None:
            count = obj.scheduled_runs.count()
        return count


class ConventionEventSerializer(EventCountersMixin, serializers.ModelSerializer):
    """Сериализатор проведения конвента"""
    convention = serializers.PrimaryKeyRelatedField(read_only=True)
    convention_name = serializers.CharField(source='convention.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True
    )
    convention_id = serializers.PrimaryKeyRelatedField(
        queryset=Convention.objects.all(),
        source='convention',
        write_only=True
    )
    venue = VenueBriefSerializer(read_only=True)
    venue_name = serializers.CharField(source='venue.name', read_only=True, allow_null=True)
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(),
        source='venue',
        write_only=True,
        required=False,
        allow_null=True
    )
    organizers = UserPublicSerializer(many=True, read_only=True)
    games = serializers.SerializerMethodField()
    runs = RunBriefSerializer(source='scheduled_runs', many=True, read_only=True)
    runs_count = serializers.IntegerField(source='scheduled_runs.count', read_only=True)
    description = serializers.CharField(source='convention.description', read_only=True)
    city = CitySerializer(read_only=True)
    links = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    # Поля регистрации
    registrations_count = serializers.SerializerMethodField()
    pending_registrations_count = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    current_user_registration = serializers.SerializerMethodField()

    def get_games(self, obj):
        """Получить уникальные игры из всех прогонов конвента"""
        games = {run.game for run in obj.scheduled_runs.all()}
        return GameBriefSerializer(list(games), many=True, context=self.context).data
    
    def get_links(self, obj):
        """Получить ссылки конвента"""
        return ConventionLinkSerializer(obj.convention.links.all(), many=True, context=self.context).data

    class Meta:
        model = ConventionEvent
        fields = [
            'id', 'convention', 'convention_id', 'convention_name', 
            'city', 'city_name', 'city_id',
            'venue', 'venue_name', 'venue_id',
            'date_start', 'date_end', 'description', 'links', 'source_url',
            'capacity', 'registration_open',
            'organizers', 'games', 'runs', 'runs_count',
            'registrations_count', 'pending_registrations_count', 
            'available_slots', 'is_full', 'current_user_registration',
            'can_edit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organizers', 'created_at', 'updated_at', 'can_edit']

    def validate(self, attrs):
        """Дата окончания не раньше даты начала"""
        date_start = attrs.get('date_start', getattr(self.instance, 'date_start', None))
        date_end = attrs.get('date_end', getattr(self.instance, 'date_end', None))
        if date_start and date_end and date_end < date_start:
            raise serializers.ValidationError({'date_end': ['Дата окончания не может быть раньше даты начала']})
        return attrs


class RegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор регистрации на прогон"""
    user = UserBriefSerializer(read_only=True)
    run_id = serializers.PrimaryKeyRelatedField(
        queryset=Run.objects.all(),
        source='run',
        write_only=True
    )
    role_preference_display = serializers.CharField(source='get_role_preference_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Registration
        fields = [
            'id', 'run_id', 'user', 'role_preference', 'role_preference_display',
            'is_technician', 'status', 'status_display', 'comment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class RegistrationBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор регистрации для списка участников"""
    user = UserBriefSerializer(read_only=True)
    
    class Meta:
        model = Registration
        fields = ['id', 'user', 'role_preference', 'is_technician', 'status']


class ConventionEventRegistrationSerializer(serializers.ModelSerializer):
    """Полный сериализатор регистрации на проведение конвента"""
    user = UserBriefSerializer(read_only=True)
    convention_event_id = serializers.PrimaryKeyRelatedField(
        queryset=ConventionEvent.objects.all(),
        source='convention_event',
        write_only=True
    )
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ConventionEventRegistration
        fields = [
            'id', 'convention_event_id', 'user', 
            'status', 'status_display', 
            'comment', 'admin_comment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ConventionEventRegistrationBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор регистрации на конвент для списков"""
    user = UserBriefSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ConventionEventRegistration
        fields = ['id', 'user', 'status', 'status_display', 'created_at']


class RunComputedFieldsMixin:
    """Общие вычисляемые поля прогона: площадка, конвент, права, своя регистрация"""

    def get_date_local(self, obj):
        """Возвращает дату и время в локальной таймзоне города"""
        import pytz
        if obj.date and obj.city and obj.city.timezone:
            try:
                tz = pytz.timezone(obj.city.timezone)
                local_dt = obj.date.astimezone(tz)
                return local_dt.strftime('%Y-%m-%dT%H:%M:%S')
            except Exception:
                pass
        return obj.date.isoformat() if obj.date else None

    def get_convention_name(self, obj):
        if obj.convention_event:
            return obj.convention_event.convention.name
        return None

    def get_venue_name(self, obj):
        """Возвращает название площадки (из помещений прогона)"""
        rooms = obj.rooms.all()
        if not rooms:
            return None
        # Собираем уникальные названия площадок
        venue_names = set(room.venue.name for room in rooms if room.venue)
        if len(venue_names) == 1:
            return venue_names.pop()
        elif len(venue_names) > 1:
            return ', '.join(sorted(venue_names))
        return None

    def get_can_edit(self, obj):
        """Проверяем, может ли текущий пользователь редактировать прогон"""
        # Мастер прогона, организатор проведения/конвента или staff
        return can_manage_run_registrations(get_request_user(self), obj)

    def get_current_user_registration(self, obj):
        """Регистрация текущего пользователя на этот прогон"""
        user = get_request_user(self)
        if user is None:
            return None
        prefetched = getattr(obj, '_my_registrations', None)
        if prefetched is not None:
            registration = prefetched[0] if prefetched else None
        else:
            registration = obj.registrations.filter(user=user).select_related('user').first()
        if registration is None:
            return None
        return RegistrationBriefSerializer(registration, context=self.context).data

    def get_can_manage_registrations(self, obj):
        """Может ли пользователь управлять заявками на прогон (подтверждать/отклонять)"""
        return can_manage_run_registrations(get_request_user(self), obj)


class RunListSerializer(RunComputedFieldsMixin, RunCountersMixin, serializers.ModelSerializer):
    """Лёгкий сериализатор прогона для списка (без списка регистраций и текстов игры)"""
    game = GameCompactSerializer(read_only=True)
    masters = UserPublicSerializer(many=True, read_only=True)
    city = serializers.CharField(source='city.name', read_only=True)
    city_id = serializers.IntegerField(read_only=True)
    city_timezone = serializers.CharField(source='city.timezone', read_only=True)
    rooms = RoomBriefSerializer(many=True, read_only=True)
    venue_name = serializers.SerializerMethodField()
    convention_event = serializers.PrimaryKeyRelatedField(read_only=True)
    convention_name = serializers.SerializerMethodField()
    date_local = serializers.SerializerMethodField()
    registered_count = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    current_user_registration = serializers.SerializerMethodField()
    effective_max_players = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_manage_registrations = serializers.SerializerMethodField()

    class Meta:
        model = Run
        fields = [
            'id', 'game', 'masters', 'date', 'date_local', 'duration',
            'city', 'city_id', 'city_timezone',
            'rooms', 'venue_name',
            'convention_event', 'convention_name',
            'max_players', 'registration_open',
            'registered_count', 'available_slots', 'is_full',
            'current_user_registration', 'effective_max_players',
            'can_edit', 'can_manage_registrations'
        ]


class RunSerializer(RunComputedFieldsMixin, RunCountersMixin, serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.all(),
        source='game',
        write_only=True
    )
    masters = UserPublicSerializer(many=True, read_only=True)
    city = serializers.CharField(source='city.name', read_only=True)
    city_timezone = serializers.CharField(source='city.timezone', read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city'
    )
    rooms = RoomBriefSerializer(many=True, read_only=True)
    room_ids = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        source='rooms',
        write_only=True,
        many=True,
        required=False
    )
    venue_name = serializers.SerializerMethodField()
    convention_event = serializers.PrimaryKeyRelatedField(read_only=True)
    convention_event_id = serializers.PrimaryKeyRelatedField(
        queryset=ConventionEvent.objects.all(),
        source='convention_event',
        write_only=True,
        required=False,
        allow_null=True
    )
    convention_name = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    date_local = serializers.SerializerMethodField()
    # Используем NaiveDateTimeField чтобы DRF не добавлял UTC автоматически
    date = NaiveDateTimeField()
    
    # Поля регистрации
    registrations = serializers.SerializerMethodField()
    registered_count = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    current_user_registration = serializers.SerializerMethodField()
    effective_max_players = serializers.SerializerMethodField()
    can_manage_registrations = serializers.SerializerMethodField()
    
    class Meta:
        model = Run
        fields = [
            'id', 'game', 'game_id', 'masters', 'date', 'date_local', 'duration',
            'city', 'city_id', 'city_timezone',
            'rooms', 'room_ids', 'venue_name',
            'convention_event', 'convention_event_id', 'convention_name',
            'max_players', 'registration_open',
            'registrations', 'registered_count', 'available_slots', 'is_full',
            'current_user_registration', 'effective_max_players',
            'can_edit', 'can_manage_registrations', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'masters', 'created_at', 'updated_at', 'can_edit', 'can_manage_registrations']

    def get_registrations(self, obj):
        """
        Список заявок с данными пользователей — только для тех, кто управляет заявками
        (мастер прогона, организатор конвента, staff). Остальным — None.
        """
        if not can_manage_run_registrations(get_request_user(self), obj):
            return None
        registrations = obj.registrations.select_related('user').all()
        return RegistrationSerializer(registrations, many=True, context=self.context).data

    def validate(self, attrs):
        """
        Конвертирует локальное время в UTC с учётом таймзоны города.
        Дата приходит с фронтенда в формате без таймзоны (например 2026-01-15T14:00:00),
        интерпретируется как локальное время в таймзоне города.
        Также проверяет, что дата прогона попадает в даты проведения конвента.
        """
        import pytz
        from django.utils import timezone as django_timezone
        
        date_value = attrs.get('date')
        if date_value and not django_timezone.is_aware(date_value):
            city_timezone = None
            
            # Получаем таймзону из города в данных запроса
            city = attrs.get('city')
            if city and hasattr(city, 'timezone'):
                city_timezone = city.timezone
            
            # Если нет в данных, пробуем из существующего прогона
            if not city_timezone and self.instance and self.instance.city:
                city_timezone = self.instance.city.timezone
            
            if city_timezone:
                try:
                    tz = pytz.timezone(city_timezone)
                    # Интерпретируем naive datetime как локальное время в этой таймзоне
                    local_dt = tz.localize(date_value)
                    # Конвертируем в UTC
                    attrs['date'] = local_dt.astimezone(pytz.UTC)
                except Exception:
                    pass
            else:
                # Если не удалось определить таймзону, используем дефолтную (Москва)
                try:
                    default_tz = pytz.timezone('Europe/Moscow')
                    local_dt = default_tz.localize(date_value)
                    attrs['date'] = local_dt.astimezone(pytz.UTC)
                except Exception:
                    pass
        
        # Проверяем, что дата прогона попадает в даты проведения конвента
        convention_event = attrs.get('convention_event')
        if not convention_event and self.instance:
            convention_event = self.instance.convention_event
        
        date_to_check = attrs.get('date', self.instance.date if self.instance else None)
        if convention_event and date_to_check:
            error = date_outside_event_error(date_to_check, convention_event, 'прогона')
            if error:
                raise serializers.ValidationError({'date': error})
        
        return attrs
