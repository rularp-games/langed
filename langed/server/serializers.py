from rest_framework import serializers
from .models import Game, Run


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
    
    class Meta:
        model = Run
        fields = [
            'id', 'game', 'game_id', 'date', 'city',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
