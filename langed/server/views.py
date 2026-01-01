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

from .models import Game, Run, Convention, ConventionEvent, City, ConventionLink, Venue, Registration, Region
from .serializers import (
    GameSerializer, RunSerializer, 
    ConventionSerializer, ConventionEventSerializer,
    CitySerializer, ConventionLinkSerializer,
    VenueSerializer, RegistrationSerializer,
    ConventionScheduleSerializer, ScheduleRunSerializer
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


class CityViewSet(viewsets.ModelViewSet):
    """API для городов"""
    queryset = City.objects.all()
    serializer_class = CitySerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]


class GameViewSet(viewsets.ModelViewSet):
    """API для игр (просмотр, создание, редактирование)"""
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'import_csv']:
            # Для создания/изменения требуется авторизация
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def check_object_permissions(self, request, obj):
        """Проверяем, что пользователь — создатель игры или staff"""
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if not request.user.is_staff and request.user not in obj.creators.all():
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Только создатель игры может её редактировать')
    
    def perform_create(self, serializer):
        """При создании игры автоматически добавляем текущего пользователя как создателя"""
        game = serializer.save()
        game.creators.add(self.request.user)
    
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
                # Нормализуем ключи к нижнему регистру для совместимости с разными CSV
                row_lower = {k.lower(): v for k, v in row.items()}
                
                name = row_lower.get('название', '').strip()
                if not name:
                    continue
                
                announcement = row_lower.get('анонс', '').strip()
                red_flags = row_lower.get('красные флаги', '').strip()
                
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
    """API для прогонов (просмотр, создание, редактирование)"""
    serializer_class = RunSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def check_object_permissions(self, request, obj):
        """Проверяем, что пользователь — мастер прогона или staff"""
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if not request.user.is_staff and request.user not in obj.masters.all():
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Только мастер прогона может его редактировать')
    
    def get_queryset(self):
        queryset = Run.objects.select_related(
            'game', 'city', 'venue', 'convention_event', 'convention_event__convention'
        ).prefetch_related('masters', 'registrations', 'registrations__user').all()
        
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
        
        return queryset.order_by('-date')
    
    @action(detail=False, methods=['get'])
    def cities(self, request):
        """Получить список уникальных городов"""
        cities = City.objects.filter(
            runs__isnull=False
        ).distinct().values_list('name', flat=True).order_by('name')
        return Response(list(cities))
    
    def perform_create(self, serializer):
        """При создании прогона автоматически устанавливаем текущего пользователя как мастера"""
        run = serializer.save()
        run.masters.add(self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_master(self, request, pk=None):
        """Добавить мастера к прогону"""
        run = self.get_object()
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Укажите имя пользователя'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        if user in run.masters.all():
            return Response({'error': 'Пользователь уже является мастером'}, status=status.HTTP_400_BAD_REQUEST)
        
        run.masters.add(user)
        return Response(RunSerializer(run, context={'request': request}).data)
    
    @action(detail=True, methods=['post'])
    def remove_master(self, request, pk=None):
        """Удалить мастера из прогона"""
        run = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'Укажите ID пользователя'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        if user not in run.masters.all():
            return Response({'error': 'Пользователь не является мастером'}, status=status.HTTP_400_BAD_REQUEST)
        
        if run.masters.count() == 1:
            return Response({'error': 'Нельзя удалить последнего мастера'}, status=status.HTTP_400_BAD_REQUEST)
        
        run.masters.remove(user)
        return Response(RunSerializer(run, context={'request': request}).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request, pk=None):
        """Зарегистрироваться на прогон как игрок"""
        run = self.get_object()
        
        # Проверяем, открыта ли регистрация
        if not run.registration_open:
            return Response(
                {'error': 'Регистрация на этот прогон закрыта'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, не является ли пользователь мастером
        if request.user in run.masters.all():
            return Response(
                {'error': 'Мастер не может зарегистрироваться как игрок на свой прогон'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, не зарегистрирован ли уже
        if Registration.objects.filter(run=run, user=request.user).exists():
            return Response(
                {'error': 'Вы уже зарегистрированы на этот прогон'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем данные регистрации
        role_preference = request.data.get('role_preference', 'any')
        is_technician = request.data.get('is_technician', False)
        comment = request.data.get('comment', '')
        
        # Определяем статус регистрации
        if is_technician:
            # Игротехники регистрируются отдельно
            registration_status = 'confirmed'
        elif run.is_full():
            # Если прогон заполнен, добавляем в лист ожидания
            registration_status = 'waitlist'
        else:
            registration_status = 'confirmed'
        
        # Создаём регистрацию
        registration = Registration.objects.create(
            run=run,
            user=request.user,
            role_preference=role_preference,
            is_technician=is_technician,
            status=registration_status,
            comment=comment
        )
        
        return Response({
            'registration': RegistrationSerializer(registration, context={'request': request}).data,
            'run': RunSerializer(run, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unregister(self, request, pk=None):
        """Отменить регистрацию на прогон"""
        run = self.get_object()
        
        try:
            registration = Registration.objects.get(run=run, user=request.user)
        except Registration.DoesNotExist:
            return Response(
                {'error': 'Вы не зарегистрированы на этот прогон'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Запоминаем, был ли это подтверждённый игрок (не игротехник)
        was_confirmed_player = (
            registration.status == 'confirmed' and 
            not registration.is_technician
        )
        
        registration.delete()
        
        # Если освободилось место, переводим первого из waitlist в confirmed
        if was_confirmed_player:
            waitlist_registration = Registration.objects.filter(
                run=run,
                status='waitlist',
                is_technician=False
            ).order_by('created_at').first()
            
            if waitlist_registration:
                waitlist_registration.status = 'confirmed'
                waitlist_registration.save()
        
        return Response({
            'message': 'Регистрация отменена',
            'run': RunSerializer(run, context={'request': request}).data
        })
    
    @action(detail=True, methods=['get'])
    def registrations(self, request, pk=None):
        """Получить список регистраций на прогон"""
        run = self.get_object()
        registrations = run.registrations.select_related('user').all()
        return Response(RegistrationSerializer(registrations, many=True, context={'request': request}).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_registration(self, request, pk=None):
        """Обновить статус регистрации (только для мастера/staff)"""
        run = self.get_object()
        
        # Проверяем права
        if not request.user.is_staff and request.user not in run.masters.all():
            return Response(
                {'error': 'Только мастер прогона может изменять регистрации'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        registration_id = request.data.get('registration_id')
        new_status = request.data.get('status')
        
        if not registration_id or not new_status:
            return Response(
                {'error': 'Укажите registration_id и status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in ['pending', 'confirmed', 'cancelled', 'waitlist']:
            return Response(
                {'error': 'Недопустимый статус'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            registration = Registration.objects.get(id=registration_id, run=run)
        except Registration.DoesNotExist:
            return Response(
                {'error': 'Регистрация не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        registration.status = new_status
        registration.save()
        
        return Response({
            'registration': RegistrationSerializer(registration, context={'request': request}).data,
            'run': RunSerializer(run, context={'request': request}).data
        })


class VenueViewSet(viewsets.ModelViewSet):
    """API для площадок"""
    queryset = Venue.objects.select_related('city').all()
    serializer_class = VenueSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по городу
        city_id = self.request.query_params.get('city')
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        
        return queryset.order_by('name')


class ConventionViewSet(viewsets.ModelViewSet):
    """API для конвентов (просмотр, создание, редактирование)"""
    serializer_class = ConventionSerializer
    queryset = Convention.objects.prefetch_related('events', 'organizers').all()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'import_csv']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def check_object_permissions(self, request, obj):
        """Проверяем, что пользователь — организатор конвента или staff"""
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if not request.user.is_staff and request.user not in obj.organizers.all():
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Только организатор конвента может его редактировать')
    
    def perform_create(self, serializer):
        """При создании конвента автоматически устанавливаем текущего пользователя как организатора"""
        convention = serializer.save()
        convention.organizers.add(self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_organizer(self, request, pk=None):
        """Добавить организатора к конвенту"""
        convention = self.get_object()
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Укажите имя пользователя'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        if user in convention.organizers.all():
            return Response({'error': 'Пользователь уже является организатором'}, status=status.HTTP_400_BAD_REQUEST)
        
        convention.organizers.add(user)
        return Response(ConventionSerializer(convention, context={'request': request}).data)
    
    @action(detail=True, methods=['post'])
    def remove_organizer(self, request, pk=None):
        """Удалить организатора из конвента"""
        convention = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'Укажите ID пользователя'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        if user not in convention.organizers.all():
            return Response({'error': 'Пользователь не является организатором'}, status=status.HTTP_400_BAD_REQUEST)
        
        if convention.organizers.count() == 1:
            return Response({'error': 'Нельзя удалить последнего организатора'}, status=status.HTTP_400_BAD_REQUEST)
        
        convention.organizers.remove(user)
        return Response(ConventionSerializer(convention, context={'request': request}).data)

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
                # Нормализуем ключи к нижнему регистру для совместимости с разными CSV
                row_lower = {k.lower(): v for k, v in row.items()}
                
                name = row_lower.get('название мероприятия', '').strip()
                city_name = row_lower.get('город', '').strip()
                date_start_str = row_lower.get('дата начала', '').strip()
                date_end_str = row_lower.get('дата конца', '').strip()
                
                if not name or not city_name or not date_start_str or not date_end_str:
                    continue
                
                try:
                    from datetime import datetime
                    # Поддержка форматов ДД.ММ.ГГГГ и ГГГГ-ММ-ДД
                    if '.' in date_start_str:
                        date_start = datetime.strptime(date_start_str, '%d.%m.%Y').date()
                        date_end = datetime.strptime(date_end_str, '%d.%m.%Y').date()
                    else:
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


class ConventionEventViewSet(viewsets.ModelViewSet):
    """API для проведений конвентов (просмотр, создание, редактирование)"""
    serializer_class = ConventionEventSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def check_object_permissions(self, request, obj):
        """Проверяем, что пользователь — организатор проведения/конвента или staff"""
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if not request.user.is_staff:
                is_event_organizer = request.user in obj.organizers.all()
                is_convention_organizer = request.user in obj.convention.organizers.all()
                if not is_event_organizer and not is_convention_organizer:
                    from rest_framework.exceptions import PermissionDenied
                    raise PermissionDenied('Только организатор может редактировать проведение')
    
    def get_queryset(self):
        queryset = ConventionEvent.objects.select_related(
            'convention', 'city'
        ).prefetch_related('scheduled_runs', 'scheduled_runs__game').all()
        
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
        
        return queryset.order_by('-date_start')
    
    @action(detail=False, methods=['get'])
    def cities(self, request):
        """Получить список уникальных городов проведений конвентов"""
        cities = City.objects.filter(
            convention_events__isnull=False
        ).distinct().values_list('name', flat=True).order_by('name')
        return Response(list(cities))
    
    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        """Получить полное расписание проведения конвента"""
        event = self.get_object()
        serializer = ConventionScheduleSerializer(event, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_run(self, request, pk=None):
        """Добавить прогон в расписание конвента"""
        event = self.get_object()
        
        # Проверяем права
        if not request.user.is_staff:
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Только организатор может добавлять прогоны в расписание'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Создаём прогон
        serializer = ScheduleRunSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        run = serializer.save(
            convention_event=event,
            city=event.city
        )
        run.masters.add(request.user)
        
        return Response(
            ScheduleRunSerializer(run, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_run(self, request, pk=None):
        """Обновить прогон в расписании конвента"""
        event = self.get_object()
        run_id = request.data.get('run_id')
        
        if not run_id:
            return Response({'error': 'run_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            run = Run.objects.get(id=run_id, convention_event=event)
        except Run.DoesNotExist:
            return Response({'error': 'Прогон не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем права
        if not request.user.is_staff:
            is_master = request.user in run.masters.all()
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_master and not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Нет прав для редактирования этого прогона'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Обновляем прогон
        update_data = {k: v for k, v in request.data.items() if k != 'run_id'}
        serializer = ScheduleRunSerializer(run, data=update_data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_run(self, request, pk=None):
        """Удалить прогон из расписания конвента"""
        event = self.get_object()
        run_id = request.query_params.get('run_id')
        
        if not run_id:
            return Response({'error': 'run_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            run = Run.objects.get(id=run_id, convention_event=event)
        except Run.DoesNotExist:
            return Response({'error': 'Прогон не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем права
        if not request.user.is_staff:
            is_master = request.user in run.masters.all()
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_master and not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Нет прав для удаления этого прогона'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        run.delete()
        return Response({'message': 'Прогон удалён'}, status=status.HTTP_204_NO_CONTENT)


class ConventionLinkViewSet(viewsets.ModelViewSet):
    """API для ссылок конвентов"""
    serializer_class = ConventionLinkSerializer
    queryset = ConventionLink.objects.all()
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def check_object_permissions(self, request, obj):
        """Проверяем, что пользователь — организатор конвента или staff"""
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if not request.user.is_staff and request.user not in obj.convention.organizers.all():
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Только организатор конвента может редактировать ссылки')
    
    def perform_create(self, serializer):
        """При создании ссылки проверяем права на конвент"""
        convention = serializer.validated_data.get('convention')
        if not self.request.user.is_staff and self.request.user not in convention.organizers.all():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Только организатор конвента может добавлять ссылки')
        serializer.save()
