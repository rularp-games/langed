from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Game, Run, Convention, ConventionEvent, City, ConventionLink, Region, Venue, Room, Registration

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор пользователя"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'display_name']
    
    def get_display_name(self, obj):
        if obj.first_name or obj.last_name:
            return f'{obj.first_name} {obj.last_name}'.strip()
        return obj.username


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


class RoomSerializer(serializers.ModelSerializer):
    """Сериализатор помещения"""
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.all(),
        source='venue',
        write_only=True
    )
    venue_name = serializers.CharField(source='venue.name', read_only=True)
    
    class Meta:
        model = Room
        fields = ['id', 'venue_id', 'venue_name', 'name', 'blackbox', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RoomBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор помещения"""
    class Meta:
        model = Room
        fields = ['id', 'name', 'blackbox']


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


class GameSerializer(serializers.ModelSerializer):
    poster_url = serializers.SerializerMethodField()
    creators = UserBriefSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = [
            'id', 'name', 'creators', 'poster', 'poster_url', 'announcement', 'red_flags',
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
        source='convention',
        write_only=True
    )
    
    class Meta:
        model = ConventionLink
        fields = ['id', 'convention_id', 'url', 'link_type', 'link_type_display', 'title', 'display_title']
        read_only_fields = ['id']
    
    def get_display_title(self, obj):
        return obj.get_display_title()


class ConventionSerializer(serializers.ModelSerializer):
    """Сериализатор конвента (без дат - просто справочник)"""
    organizers = UserBriefSerializer(many=True, read_only=True)
    events_count = serializers.IntegerField(source='events.count', read_only=True)
    links = ConventionLinkSerializer(many=True, read_only=True)
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = Convention
        fields = [
            'id', 'name', 'organizers', 'description', 'events_count', 'links',
            'can_edit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organizers', 'created_at', 'updated_at', 'can_edit']
    
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


class ScheduleRunSerializer(serializers.ModelSerializer):
    """Сериализатор прогона для расписания конвента"""
    game = GameBriefSerializer(read_only=True)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.all(),
        source='game',
        write_only=True
    )
    game_name = serializers.CharField(source='game.name', read_only=True)
    masters = UserBriefSerializer(many=True, read_only=True)
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
    registered_count = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    effective_max_players = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = Run
        fields = [
            'id', 'game', 'game_id', 'game_name', 'masters', 
            'date', 'date_local', 'duration', 'city_timezone',
            'rooms', 'room_ids',
            'max_players', 'registration_open',
            'registered_count', 'available_slots', 'is_full', 
            'effective_max_players', 'can_edit'
        ]
        read_only_fields = ['id', 'masters', 'can_edit']
    
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
    
    def get_registered_count(self, obj):
        return obj.get_registered_count()
    
    def get_available_slots(self, obj):
        return obj.get_available_slots()
    
    def get_is_full(self, obj):
        return obj.is_full()
    
    def get_effective_max_players(self, obj):
        return obj.get_max_players()
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        # Может редактировать мастер прогона или организатор конвента
        if request.user in obj.masters.all():
            return True
        if obj.convention_event:
            if request.user in obj.convention_event.organizers.all():
                return True
            if request.user in obj.convention_event.convention.organizers.all():
                return True
        return False


class ConventionScheduleSerializer(serializers.ModelSerializer):
    """Сериализатор расписания проведения конвента"""
    convention = serializers.PrimaryKeyRelatedField(read_only=True)
    convention_name = serializers.CharField(source='convention.name', read_only=True)
    convention_description = serializers.CharField(source='convention.description', read_only=True)
    city = CitySerializer(read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    city_timezone = serializers.CharField(source='city.timezone', read_only=True)
    organizers = UserBriefSerializer(many=True, read_only=True)
    convention_organizers = UserBriefSerializer(source='convention.organizers', many=True, read_only=True)
    links = serializers.SerializerMethodField()
    runs = ScheduleRunSerializer(source='scheduled_runs', many=True, read_only=True)
    venues = serializers.SerializerMethodField()
    games = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    class Meta:
        model = ConventionEvent
        fields = [
            'id', 'convention', 'convention_name', 'convention_description',
            'city', 'city_name', 'city_timezone', 'date_start', 'date_end',
            'organizers', 'convention_organizers', 'links',
            'runs', 'venues', 'games', 'can_edit'
        ]
    
    def get_links(self, obj):
        return ConventionLinkSerializer(obj.convention.links.all(), many=True, context=self.context).data
    
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
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        is_event_organizer = request.user in obj.organizers.all()
        is_convention_organizer = request.user in obj.convention.organizers.all()
        return is_event_organizer or is_convention_organizer


class ConventionEventSerializer(serializers.ModelSerializer):
    """Сериализатор проведения конвента"""
    convention = serializers.PrimaryKeyRelatedField(read_only=True)
    convention_name = serializers.CharField(source='convention.name', read_only=True)
    city_name = serializers.CharField(source='city.name', read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True,
        required=False
    )
    convention_id = serializers.PrimaryKeyRelatedField(
        queryset=Convention.objects.all(),
        source='convention',
        write_only=True,
        required=False
    )
    organizers = UserBriefSerializer(many=True, read_only=True)
    games = serializers.SerializerMethodField()
    runs = RunBriefSerializer(source='scheduled_runs', many=True, read_only=True)
    runs_count = serializers.IntegerField(source='scheduled_runs.count', read_only=True)
    description = serializers.CharField(source='convention.description', read_only=True)
    city = CitySerializer(read_only=True)
    links = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    def get_games(self, obj):
        """Получить уникальные игры из всех прогонов конвента"""
        games = {run.game for run in obj.scheduled_runs.all()}
        return GameBriefSerializer(list(games), many=True, context=self.context).data
    
    def get_links(self, obj):
        """Получить ссылки конвента"""
        return ConventionLinkSerializer(obj.convention.links.all(), many=True, context=self.context).data
    
    def get_can_edit(self, obj):
        """Проверяем, может ли текущий пользователь редактировать проведение"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        is_event_organizer = request.user in obj.organizers.all()
        is_convention_organizer = request.user in obj.convention.organizers.all()
        return is_event_organizer or is_convention_organizer

    class Meta:
        model = ConventionEvent
        fields = [
            'id', 'convention', 'convention_id', 'convention_name', 
            'city', 'city_name', 'city_id',
            'date_start', 'date_end', 'description', 'links',
            'organizers', 'games', 'runs', 'runs_count',
            'can_edit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organizers', 'created_at', 'updated_at', 'can_edit']


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


class RunSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.all(),
        source='game',
        write_only=True
    )
    masters = UserBriefSerializer(many=True, read_only=True)
    city = serializers.CharField(source='city.name', read_only=True)
    city_timezone = serializers.CharField(source='city.timezone', read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True
    )
    rooms = RoomBriefSerializer(many=True, read_only=True)
    room_ids = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        source='rooms',
        write_only=True,
        many=True,
        required=False
    )
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
    
    # Поля регистрации
    registrations = RegistrationBriefSerializer(many=True, read_only=True)
    registered_count = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()
    current_user_registration = serializers.SerializerMethodField()
    effective_max_players = serializers.SerializerMethodField()
    
    class Meta:
        model = Run
        fields = [
            'id', 'game', 'game_id', 'masters', 'date', 'duration',
            'city', 'city_id', 'city_timezone',
            'rooms', 'room_ids',
            'convention_event', 'convention_event_id', 'convention_name',
            'max_players', 'registration_open',
            'registrations', 'registered_count', 'available_slots', 'is_full',
            'current_user_registration', 'effective_max_players',
            'can_edit', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'masters', 'created_at', 'updated_at', 'can_edit']
    
    def get_convention_name(self, obj):
        if obj.convention_event:
            return obj.convention_event.convention.name
        return None
    
    def get_can_edit(self, obj):
        """Проверяем, может ли текущий пользователь редактировать прогон"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        if request.user.is_staff:
            return True
        return request.user in obj.masters.all()
    
    def get_registered_count(self, obj):
        """Количество зарегистрированных игроков"""
        return obj.get_registered_count()
    
    def get_available_slots(self, obj):
        """Количество свободных мест"""
        return obj.get_available_slots()
    
    def get_is_full(self, obj):
        """Заполнен ли прогон"""
        return obj.is_full()
    
    def get_effective_max_players(self, obj):
        """Эффективный максимум игроков"""
        return obj.get_max_players()
    
    def get_current_user_registration(self, obj):
        """Регистрация текущего пользователя на этот прогон"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        try:
            registration = obj.registrations.get(user=request.user)
            return RegistrationBriefSerializer(registration, context=self.context).data
        except Registration.DoesNotExist:
            return None
