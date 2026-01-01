from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Game, Run, Convention, ConventionEvent, City, ConventionLink, Region

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
    
    class Meta:
        model = Run
        fields = [
            'id', 'game', 'game_id', 'masters', 'date', 'city', 'city_id', 'city_timezone',
            'convention_event', 'convention_event_id', 'convention_name',
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
