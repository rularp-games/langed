from rest_framework import serializers
from .models import Game, Run, Convention


class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = [
            'id', 'name', 'announcement', 'red_flags',
            'players_min', 'players_max',
            'female_roles_min', 'female_roles_max',
            'male_roles_min', 'male_roles_max',
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
    convention_id = serializers.PrimaryKeyRelatedField(
        queryset=Convention.objects.all(),
        source='convention',
        write_only=True,
        required=False,
        allow_null=True
    )
    convention_name = serializers.CharField(source='convention.name', read_only=True, default=None)
    
    class Meta:
        model = Run
        fields = [
            'id', 'game', 'game_id', 'date', 'city', 
            'convention', 'convention_id', 'convention_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RunBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор прогона для вложения в конвент"""
    game_name = serializers.CharField(source='game.name', read_only=True)
    
    class Meta:
        model = Run
        fields = ['id', 'game_name', 'date', 'city']


class ConventionSerializer(serializers.ModelSerializer):
    runs = RunBriefSerializer(many=True, read_only=True)
    runs_count = serializers.IntegerField(source='runs.count', read_only=True)
    
    class Meta:
        model = Convention
        fields = [
            'id', 'name', 'city', 'date_start', 'date_end', 'description',
            'runs', 'runs_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConventionBriefSerializer(serializers.ModelSerializer):
    """Краткий сериализатор конвента для вложения в прогон"""
    
    class Meta:
        model = Convention
        fields = ['id', 'name', 'city', 'date_start', 'date_end']
