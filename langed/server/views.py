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
    """API для просмотра прогонов с фильтрацией"""
    serializer_class = RunSerializer
    
    def get_queryset(self):
        queryset = Run.objects.select_related('game').all()
        
        # Фильтр по городу
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__iexact=city)
        
        # Фильтр по времени: upcoming (предстоящие) или past (прошедшие)
        time_filter = self.request.query_params.get('time')
        if time_filter == 'upcoming':
            queryset = queryset.filter(date__gte=timezone.now())
        elif time_filter == 'past':
            queryset = queryset.filter(date__lt=timezone.now())
        
        return queryset.order_by('date')
    
    @action(detail=False, methods=['get'])
    def cities(self, request):
        """Получить список уникальных городов"""
        cities = Run.objects.values_list('city', flat=True).distinct().order_by('city')
        return Response(list(cities))
