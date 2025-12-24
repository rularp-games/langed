from rest_framework import serializers
from .models import Game, Run, Convention, ConventionEvent, City


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ['id', 'name', 'region']


class GameSerializer(serializers.ModelSerializer):
    poster_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = [
            'id', 'name', 'poster', 'poster_url', 'announcement', 'red_flags',
            'players_min', 'players_max',
            'female_roles_min', 'female_roles_max',
            'male_roles_min', 'male_roles_max',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'poster_url']
    
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


class ConventionSerializer(serializers.ModelSerializer):
    """Сериализатор конвента (без дат - просто справочник)"""
    events_count = serializers.IntegerField(source='events.count', read_only=True)
    
    class Meta:
        model = Convention
        fields = [
            'id', 'name', 'description', 'events_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RunBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор прогона для вложения в проведение конвента"""
    game_name = serializers.CharField(source='game.name', read_only=True)
    
    class Meta:
        model = Run
        fields = ['id', 'game_name', 'date']


class ConventionEventSerializer(serializers.ModelSerializer):
    """Сериализатор проведения конвента"""
    convention_name = serializers.CharField(source='convention.name', read_only=True)
    city = serializers.CharField(source='city.name', read_only=True)
    city_id = serializers.PrimaryKeyRelatedField(
        queryset=City.objects.all(),
        source='city',
        write_only=True
    )
    games = GameBriefSerializer(many=True, read_only=True)
    runs = RunBriefSerializer(many=True)
    scheduled_runs = RunBriefSerializer(many=True, read_only=True)
    scheduled_runs_count = serializers.IntegerField(source='scheduled_runs.count', read_only=True)
    description = serializers.CharField(source='convention.description', read_only=True)
    
    class Meta:
        model = ConventionEvent
        fields = [
            'id', 'convention', 'convention_name', 'city', 'city_id',
            'date_start', 'date_end', 'description',
            'games', 'runs', 'scheduled_runs', 'scheduled_runs_count',
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
            'id', 'game', 'game_id', 'date', 'city', 'city_id',
            'convention_event', 'convention_event_id', 'convention_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_convention_name(self, obj):
        if obj.convention_event:
            return obj.convention_event.convention.name
        return None
