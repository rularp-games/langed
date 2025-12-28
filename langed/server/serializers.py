from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Game, Run, Convention, ConventionEvent, City, ConventionLink

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


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'region']


class GameSerializer(serializers.ModelSerializer):
    poster_url = serializers.SerializerMethodField()
    master = UserBriefSerializer(read_only=True)
    
    class Meta:
        model = Game
        fields = [
            'id', 'name', 'master', 'poster', 'poster_url', 'announcement', 'red_flags',
            'players_min', 'players_max',
            'female_roles_min', 'female_roles_max',
            'male_roles_min', 'male_roles_max',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'master', 'created_at', 'updated_at', 'poster_url']
    
    def get_poster_url(self, obj):
        if obj.poster:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.poster.url)
            return obj.poster.url
        return None


class GameBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор игры"""
    class Meta:
        model = Game
        fields = ['id', 'name', 'players_min', 'players_max']


class ConventionLinkSerializer(serializers.ModelSerializer):
    """Сериализатор ссылки конвента"""
    display_title = serializers.SerializerMethodField()
    link_type_display = serializers.CharField(source='get_link_type_display', read_only=True)
    
    class Meta:
        model = ConventionLink
        fields = ['id', 'url', 'link_type', 'link_type_display', 'title', 'display_title']
        read_only_fields = ['id']
    
    def get_display_title(self, obj):
        return obj.get_display_title()


class ConventionSerializer(serializers.ModelSerializer):
    """Сериализатор конвента (без дат - просто справочник)"""
    organizer = UserBriefSerializer(read_only=True)
    events_count = serializers.IntegerField(source='events.count', read_only=True)
    links = ConventionLinkSerializer(many=True, read_only=True)
    
    class Meta:
        model = Convention
        fields = [
            'id', 'name', 'organizer', 'description', 'events_count', 'links',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'organizer', 'created_at', 'updated_at']


class RunBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор прогона для вложения в проведение конвента"""
    game_name = serializers.CharField(source='game.name', read_only=True)
    
    class Meta:
        model = Run
        fields = ['id', 'game_name', 'date']


class ConventionEventSerializer(serializers.ModelSerializer):
    """Сериализатор проведения конвента"""
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
    games = serializers.SerializerMethodField()
    runs = RunBriefSerializer(many=True, read_only=True)
    scheduled_runs = RunBriefSerializer(many=True, read_only=True)
    scheduled_runs_count = serializers.IntegerField(source='scheduled_runs.count', read_only=True)
    runs_count = serializers.SerializerMethodField()
    description = serializers.CharField(source='convention.description', read_only=True)
    city = CitySerializer(read_only=True)
    links = serializers.SerializerMethodField()

    def get_games(self, obj):
        """Получить уникальные игры из всех прогонов конвента"""
        games = set()
        # Игры из runs (ManyToMany)
        for run in obj.runs.all():
            games.add(run.game)
        # Игры из scheduled_runs (reverse FK)
        for run in obj.scheduled_runs.all():
            games.add(run.game)
        return GameBriefSerializer(list(games), many=True, context=self.context).data
    
    def get_runs_count(self, obj):
        """Получить общее количество прогонов"""
        return obj.runs.count() + obj.scheduled_runs.count()
    
    def get_links(self, obj):
        """Получить ссылки конвента"""
        return ConventionLinkSerializer(obj.convention.links.all(), many=True, context=self.context).data

    class Meta:
        model = ConventionEvent
        fields = [
            'id', 'convention', 'convention_id', 'convention_name', 
            'city', 'city_name', 'city_id',
            'date_start', 'date_end', 'description', 'links',
            'games', 'runs', 'scheduled_runs', 'scheduled_runs_count', 'runs_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RunSerializer(serializers.ModelSerializer):
    game = GameSerializer(read_only=True)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=Game.objects.all(),
        source='game',
        write_only=True
    )
    master = UserBriefSerializer(read_only=True)
    city = serializers.CharField(source='city.name', read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True
    )
    convention_event_id = serializers.PrimaryKeyRelatedField(
        queryset=ConventionEvent.objects.all(),
        source='convention_event',
        write_only=True,
        required=False,
        allow_null=True
    )
    convention_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Run
        fields = [
            'id', 'game', 'game_id', 'master', 'date', 'city', 'city_id',
            'convention_event', 'convention_event_id', 'convention_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'master', 'created_at', 'updated_at']
    
    def get_convention_name(self, obj):
        if obj.convention_event:
            return obj.convention_event.convention.name
        return None
