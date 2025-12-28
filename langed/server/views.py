import csv
import io
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from datetime import date

from .models import Game, Run, Convention, ConventionEvent, City
from .serializers import (
    GameSerializer, RunSerializer, 
    ConventionSerializer, ConventionEventSerializer
)


@api_view(['GET'])
@permission_classes([AllowAny])
def current_user(request):
    """Возвращает информацию о текущем пользователе"""
    if request.user.is_authenticated:
        return Response({
            'is_authenticated': True,
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'is_staff': request.user.is_staff,
        })
    return Response({
        'is_authenticated': False,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def auth_urls(request):
    """Возвращает URLs для авторизации через Keycloak"""
    return Response({
        'login_url': '/oidc/authenticate/',
        'logout_url': '/oidc/logout/',
    })


class GameViewSet(viewsets.ModelViewSet):
    """API для игр (просмотр и создание)"""
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'import_csv']:
            # Для создания/изменения требуется авторизация
            return [IsAuthenticated()]
        return [AllowAny()]
    
    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        """Импорт игр из CSV файла"""
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response(
                {'error': 'Файл не предоставлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем расширение
        if not csv_file.name.endswith('.csv'):
            return Response(
                {'error': 'Файл должен быть в формате CSV'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Читаем файл
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))
            
            created_count = 0
            skipped_count = 0
            created_games = []
            
            for row in reader:
                name = row.get('название', '').strip()
                if not name:
                    continue
                
                announcement = row.get('анонс', '').strip()
                red_flags = row.get('красные флаги', '').strip()
                
                # Создаем только если игры с таким именем нет
                game, created = Game.objects.get_or_create(
                    name=name,
                    defaults={
                        'announcement': announcement,
                        'red_flags': red_flags,
                    }
                )
                
                if created:
                    created_count += 1
                    created_games.append(GameSerializer(game, context={'request': request}).data)
                else:
                    skipped_count += 1
            
            return Response({
                'created': created_count,
                'skipped': skipped_count,
                'games': created_games
            })
            
        except UnicodeDecodeError:
            return Response(
                {'error': 'Файл должен быть в кодировке UTF-8'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка при обработке файла: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RunViewSet(viewsets.ModelViewSet):
    """API для прогонов (просмотр и создание)"""
    serializer_class = RunSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = Run.objects.select_related(
            'game', 'city', 'convention_event', 'convention_event__convention', 'master'
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
    
    def perform_create(self, serializer):
        """При создании прогона автоматически устанавливаем текущего пользователя как мастера"""
        serializer.save(master=self.request.user)


class ConventionViewSet(viewsets.ModelViewSet):
    """API для конвентов (просмотр и создание)"""
    serializer_class = ConventionSerializer
    queryset = Convention.objects.prefetch_related('events').all()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'import_csv']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def perform_create(self, serializer):
        """При создании конвента автоматически устанавливаем текущего пользователя как организатора"""
        serializer.save(organizer=self.request.user)
    
    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        """Импорт конвентов и проведений из CSV файла"""
        csv_file = request.FILES.get('file')
        if not csv_file:
            return Response(
                {'error': 'Файл не предоставлен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not csv_file.name.endswith('.csv'):
            return Response(
                {'error': 'Файл должен быть в формате CSV'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            decoded = csv_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(decoded))
            
            conventions_created = 0
            events_created = 0
            events_skipped = 0
            
            for row in reader:
                name = row.get('название мероприятия', '').strip()
                city_name = row.get('город', '').strip()
                date_start_str = row.get('дата начала', '').strip()
                date_end_str = row.get('дата конца', '').strip()
                
                if not name or not city_name or not date_start_str or not date_end_str:
                    continue
                
                try:
                    from datetime import datetime
                    date_start = datetime.strptime(date_start_str, '%Y-%m-%d').date()
                    date_end = datetime.strptime(date_end_str, '%Y-%m-%d').date()
                except ValueError:
                    continue
                
                # Создаём или получаем конвент
                convention, conv_created = Convention.objects.get_or_create(name=name)
                if conv_created:
                    conventions_created += 1
                
                # Создаём или получаем город
                city, _ = City.objects.get_or_create(name=city_name)
                
                # Проверяем, есть ли уже такое проведение
                event_exists = ConventionEvent.objects.filter(
                    convention=convention,
                    city=city,
                    date_start=date_start,
                    date_end=date_end
                ).exists()
                
                if not event_exists:
                    ConventionEvent.objects.create(
                        convention=convention,
                        city=city,
                        date_start=date_start,
                        date_end=date_end
                    )
                    events_created += 1
                else:
                    events_skipped += 1
            
            return Response({
                'conventions_created': conventions_created,
                'events_created': events_created,
                'events_skipped': events_skipped
            })
            
        except UnicodeDecodeError:
            return Response(
                {'error': 'Файл должен быть в кодировке UTF-8'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка при обработке файла: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


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
