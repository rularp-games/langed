from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Game
from .serializers import GameSerializer


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра игр"""
    queryset = Game.objects.all()
    serializer_class = GameSerializer
