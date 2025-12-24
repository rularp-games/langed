from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import Game, Run
from .serializers import GameSerializer, RunSerializer


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра игр"""
    queryset = Game.objects.all()
    serializer_class = GameSerializer


class RunViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра прогонов"""
    queryset = Run.objects.select_related('game').all()
    serializer_class = RunSerializer


class AfishaViewSet(viewsets.ViewSet):
    """API для афиши — предстоящие прогоны"""
    
    def list(self, request):
        """Получить список предстоящих прогонов"""
        runs = Run.objects.select_related('game').filter(
            date__gte=timezone.now()
        ).order_by('date')
        serializer = RunSerializer(runs, many=True)
        return Response(serializer.data)
