from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import date

from .models import Game, Run, Convention, ConventionEvent, City
from .serializers import (
    GameSerializer, RunSerializer, 
    ConventionSerializer, ConventionEventSerializer
)


class GameViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра игр"""
    queryset = Game.objects.all()
    serializer_class = GameSerializer


class RunViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра прогонов с фильтрацией"""
    serializer_class = RunSerializer
    
    def get_queryset(self):
        queryset = Run.objects.select_related(
            'game', 'city', 'convention_event', 'convention_event__convention'
        ).all()
        
        # Фильтр по городу
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__name__iexact=city)
        
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
        cities = City.objects.filter(
            runs__isnull=False
        ).distinct().values_list('name', flat=True).order_by('name')
        return Response(list(cities))


class ConventionViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра конвентов (справочник)"""
    serializer_class = ConventionSerializer
    queryset = Convention.objects.prefetch_related('events').all()


class ConventionEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API для просмотра проведений конвентов с фильтрацией"""
    serializer_class = ConventionEventSerializer
    
    def get_queryset(self):
        queryset = ConventionEvent.objects.select_related(
            'convention', 'city'
        ).prefetch_related('scheduled_runs', 'scheduled_runs__game', 'runs', 'runs__game').all()
        
        # Фильтр по конвенту
        convention_id = self.request.query_params.get('convention')
        if convention_id:
            queryset = queryset.filter(convention_id=convention_id)
        
        # Фильтр по городу
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__name__iexact=city)
        
        # Фильтр по времени: upcoming (предстоящие) или past (прошедшие)
        time_filter = self.request.query_params.get('time')
        today = date.today()
        if time_filter == 'upcoming':
            queryset = queryset.filter(date_end__gte=today)
        elif time_filter == 'past':
            queryset = queryset.filter(date_end__lt=today)
        
        return queryset.order_by('date_start')
    
    @action(detail=False, methods=['get'])
    def cities(self, request):
        """Получить список уникальных городов проведений конвентов"""
        cities = City.objects.filter(
            convention_events__isnull=False
        ).distinct().values_list('name', flat=True).order_by('name')
        return Response(list(cities))
