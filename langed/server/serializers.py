from rest_framework import serializers
from .models import Game


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
