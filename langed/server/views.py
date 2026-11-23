import csv
import io
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import exception_handler
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Кастомный обработчик исключений для DRF.
    Гарантирует, что все ошибки возвращаются как JSON.
    """
    # Сначала вызываем стандартный обработчик DRF
    response = exception_handler(exc, context)
    
    if response is not None:
        # Добавляем код ошибки для удобства отладки
        response.data['status_code'] = response.status_code
        return response
    
    # Если стандартный обработчик не обработал исключение,
    # логируем его и возвращаем generic JSON ответ
    logger.exception("Unhandled exception in API view", exc_info=exc)
    
    return Response(
        {
            'detail': 'Внутренняя ошибка сервера',
            'status_code': 500,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

from django.db.models import BooleanField, Exists, ExpressionWrapper, OuterRef, Prefetch, Q
from django.db.models.functions import Substr
from .models import (
    Game, Run, Convention, ConventionEvent, City, ConventionLink, Venue, Room, Registration, Region,
    CommonEvent, ConventionEventRegistration, date_outside_event_error, event_local_date
)
from .serializers import (
    GameSerializer, GameListSerializer, RunSerializer, RunListSerializer,
    ConventionSerializer, ConventionEventSerializer, ConventionEventListSerializer,
    CitySerializer, ConventionLinkSerializer,
    VenueSerializer, RoomSerializer, RegistrationSerializer,
    ConventionScheduleSerializer, ScheduleRunSerializer,
    CommonEventSerializer, ConventionEventRegistrationSerializer,
    EXCERPT_SOURCE_LENGTH, can_manage_event, can_manage_run_registrations
)
from .oidc import SESSION_PASSWORD_LOGIN
from .filters import bool_param, choice_param, count_subquery, int_param
from .pagination import StandardPagination

TIME_CHOICES = ('upcoming', 'past', 'all')


def active_registrations_count():
    """Аннотация: число занятых мест прогона (подтверждённые и ожидающие игроки, без игротехников)"""
    return count_subquery(
        Registration.objects.filter(status__in=['confirmed', 'pending'], is_technician=False),
        'run'
    )


def event_organizer_exists(user, event_ref, convention_ref):
    """Аннотация: является ли пользователь организатором проведения или его конвента"""
    return ExpressionWrapper(
        Q(Exists(ConventionEvent.organizers.through.objects.filter(
            conventionevent_id=OuterRef(event_ref), user_id=user.id
        ))) |
        Q(Exists(Convention.organizers.through.objects.filter(
            convention_id=OuterRef(convention_ref), user_id=user.id
        ))),
        output_field=BooleanField()
    )


@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def current_user(request):
    """Возвращает информацию о текущем пользователе и устанавливает CSRF cookie"""
    if request.user.is_authenticated:
        # Формируем display_name
        display_name = f'{request.user.first_name} {request.user.last_name}'.strip()
        if not display_name:
            display_name = request.user.username
        return Response({
            'is_authenticated': True,
            'id': request.user.id,
            'username': request.user.username,
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'display_name': display_name,
            'is_staff': request.user.is_staff,
            # Вошёл по почте и паролю (а не через внешнего провайдера) — может сменить пароль
            'has_password_login': bool(request.session.get(SESSION_PASSWORD_LOGIN)),
        })
    return Response({
        'is_authenticated': False,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    """Поиск пользователей по имени/username для автодополнения"""
    query = request.query_params.get('q', '').strip()
    if len(query) < 2:
        return Response([])
    
    from django.contrib.auth import get_user_model
    from django.db.models import Q, Value, CharField
    from django.db.models.functions import Concat
    
    User = get_user_model()
    
    # Ищем по username, first_name и last_name; по email — только точное совпадение,
    # чтобы адреса нельзя было перебирать по подстроке
    users = User.objects.annotate(
        full_name=Concat('first_name', Value(' '), 'last_name', output_field=CharField())
    ).filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__iexact=query) |
        Q(full_name__icontains=query)
    ).distinct()[:10]
    
    results = []
    for user in users:
        display_name = f'{user.first_name} {user.last_name}'.strip()
        if not display_name:
            display_name = user.username
        result = {
            'id': user.id,
            'username': user.username,
            'display_name': display_name,
        }
        # Email виден только staff
        if request.user.is_staff:
            result['email'] = user.email
        results.append(result)
    
    return Response(results)


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
        if self.action in ['update', 'partial_update', 'destroy']:
            # Править название и часовой пояс и удалять может только staff
            return [IsAdminUser()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return [AllowAny()]


class GameViewSet(viewsets.ModelViewSet):
    """API для игр (просмотр, создание, редактирование)"""
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    pagination_class = StandardPagination
    ORDERING_CHOICES = ('name', '-name', 'created_at', '-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return GameListSerializer
        return GameSerializer

    def get_queryset(self):
        queryset = Game.objects.prefetch_related('creators')
        if self.action != 'list':
            return queryset

        # В списке полные тексты не нужны: берём из БД только начало анонса
        queryset = queryset.defer('announcement', 'red_flags').annotate(
            _announcement_head=Substr('announcement', 1, EXCERPT_SOURCE_LENGTH)
        )

        # Поиск по названию
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Фильтр по автору
        creator_id = int_param(self.request, 'creator')
        if creator_id is not None:
            queryset = queryset.filter(creators__id=creator_id)

        # Только игры текущего пользователя
        if bool_param(self.request, 'mine'):
            if not self.request.user.is_authenticated:
                return queryset.none()
            queryset = queryset.filter(creators=self.request.user)

        ordering = choice_param(self.request, 'ordering', self.ORDERING_CHOICES, '-created_at')
        return queryset.order_by(ordering, 'id')

    def get_permissions(self):
        if self.action == 'import_csv':
            # Импорт доступен только staff
            return [IsAdminUser()]
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'add_creator', 'remove_creator']:
            # Для создания/изменения требуется авторизация
            return [IsAuthenticated()]
        return [AllowAny()]

    def check_object_permissions(self, request, obj):
        """Проверяем, что пользователь — создатель игры или staff"""
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE'] or self.action in ['add_creator', 'remove_creator']:
            if not request.user.is_staff and request.user not in obj.creators.all():
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('Только создатель игры может её редактировать')
    
    def perform_create(self, serializer):
        """При создании игры автоматически добавляем текущего пользователя как создателя"""
        game = serializer.save()
        game.creators.add(self.request.user)
    
    @action(detail=True, methods=['post'])
    def add_creator(self, request, pk=None):
        """Добавить создателя к игре"""
        game = self.get_object()
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Укажите имя пользователя'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        if user in game.creators.all():
            return Response({'error': 'Пользователь уже является создателем'}, status=status.HTTP_400_BAD_REQUEST)
        
        game.creators.add(user)
        return Response(GameSerializer(game, context={'request': request}).data)
    
    @action(detail=True, methods=['post'])
    def remove_creator(self, request, pk=None):
        """Удалить создателя из игры"""
        game = self.get_object()
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'Укажите ID пользователя'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        if user not in game.creators.all():
            return Response({'error': 'Пользователь не является создателем'}, status=status.HTTP_400_BAD_REQUEST)
        
        if game.creators.count() == 1:
            return Response({'error': 'Нельзя удалить последнего создателя'}, status=status.HTTP_400_BAD_REQUEST)
        
        game.creators.remove(user)
        return Response(GameSerializer(game, context={'request': request}).data)

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
        if not csv_file.name.lower().endswith('.csv'):
            return Response(
                {'error': 'Файл должен быть в формате CSV'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Читаем файл
            decoded = csv_file.read().decode('utf-8-sig')
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


def delete_run_registration(registration):
    """Удаляет заявку на прогон и продвигает лист ожидания, если освободилось место"""
    run = registration.run
    # Запоминаем, был ли это подтверждённый игрок (не игротехник)
    was_confirmed_player = (
        registration.status == 'confirmed' and
        not registration.is_technician
    )

    registration.delete()

    # Если освободилось место, переводим первого из waitlist в pending
    # (мастер должен будет подтвердить его вручную)
    if was_confirmed_player:
        waitlist_registration = Registration.objects.filter(
            run=run,
            status='waitlist',
            is_technician=False
        ).order_by('created_at').first()

        if waitlist_registration:
            waitlist_registration.status = 'pending'
            waitlist_registration.save()


class RunViewSet(viewsets.ModelViewSet):
    """API для прогонов (просмотр, создание, редактирование)"""
    serializer_class = RunSerializer
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return RunListSerializer
        return RunSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'add_master', 'remove_master', 'registrations']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def check_object_permissions(self, request, obj):
        """Проверяем, что пользователь — мастер прогона, организатор проведения/конвента или staff"""
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE'] or self.action in ['add_master', 'remove_master']:
            if not can_manage_run_registrations(request.user, obj):
                raise PermissionDenied('Только мастер прогона или организатор конвента может его редактировать')

    def get_queryset(self):
        queryset = Run.objects.select_related(
            'game', 'city', 'convention_event', 'convention_event__convention'
        ).prefetch_related(
            'masters',
            Prefetch('rooms', queryset=Room.objects.select_related('venue'))
        )
        if self.action != 'list':
            return queryset.order_by('-date')

        user = self.request.user
        # В списке тексты игры не нужны, счётчик мест считаем подзапросом
        queryset = queryset.defer('game__announcement', 'game__red_flags').annotate(
            _registered_count=active_registrations_count()
        )
        if user.is_authenticated:
            # Собственная регистрация пользователя — одним запросом на всю страницу
            queryset = queryset.prefetch_related(Prefetch(
                'registrations',
                queryset=Registration.objects.filter(user=user).select_related('user'),
                to_attr='_my_registrations'
            ))
            if not user.is_staff:
                queryset = queryset.annotate(_user_is_event_organizer=event_organizer_exists(
                    user, 'convention_event_id', 'convention_event__convention_id'
                ))

        # Фильтр по городу
        city_id = int_param(self.request, 'city')
        if city_id is not None:
            queryset = queryset.filter(city_id=city_id)

        # Фильтр по игре
        game_id = int_param(self.request, 'game')
        if game_id is not None:
            queryset = queryset.filter(game_id=game_id)

        # Фильтр по проведению конвента
        convention_event_id = int_param(self.request, 'convention_event')
        if convention_event_id is not None:
            queryset = queryset.filter(convention_event_id=convention_event_id)

        # Только прогоны вне конвентов
        if bool_param(self.request, 'standalone'):
            queryset = queryset.filter(convention_event__isnull=True)

        # Фильтр по мастеру
        master_id = int_param(self.request, 'master')
        if master_id is not None:
            queryset = queryset.filter(masters__id=master_id)

        # Прогоны, где текущий пользователь мастер или имеет регистрацию
        if bool_param(self.request, 'mine'):
            if not user.is_authenticated:
                return queryset.none()
            queryset = queryset.filter(
                Q(pk__in=Run.masters.through.objects.filter(user_id=user.id).values('run_id')) |
                Q(pk__in=Registration.objects.filter(user=user).values('run_id'))
            )

        # Фильтр по времени: upcoming (предстоящие, по умолчанию), past (прошедшие), all (все)
        time_filter = choice_param(self.request, 'time', TIME_CHOICES, 'upcoming')
        if time_filter == 'upcoming':
            queryset = queryset.filter(date__gte=timezone.now())
            return queryset.order_by('date', 'id')  # Ближайшие первыми
        elif time_filter == 'past':
            queryset = queryset.filter(date__lt=timezone.now())

        return queryset.order_by('-date', '-id')  # Недавно прошедшие первыми

    @action(detail=False, methods=['get'])
    def cities(self, request):
        """Получить список городов, в которых есть прогоны"""
        cities = City.objects.filter(
            runs__isnull=False
        ).distinct().order_by('name').values('id', 'name')
        return Response(list(cities))
    
    def perform_create(self, serializer):
        """При создании прогона автоматически устанавливаем текущего пользователя как мастера"""
        self.check_convention_event_permission(serializer.validated_data.get('convention_event'))
        run = serializer.save()
        run.masters.add(self.request.user)

    def perform_update(self, serializer):
        """При переносе прогона в другое проведение проверяем права на это проведение"""
        if 'convention_event' in serializer.validated_data:
            convention_event = serializer.validated_data['convention_event']
            if convention_event != serializer.instance.convention_event:
                self.check_convention_event_permission(convention_event)
        serializer.save()

    def check_convention_event_permission(self, convention_event):
        """Включать прогон в расписание конвента может только организатор проведения/конвента или staff"""
        if convention_event is not None and not can_manage_event(self.request.user, convention_event):
            raise PermissionDenied('Только организатор может добавлять прогоны в расписание конвента')
    
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

        # На прошедший прогон зарегистрироваться нельзя
        if run.date < timezone.now():
            return Response(
                {'error': 'Прогон уже прошёл', 'code': 'run_past'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, открыта ли регистрация
        if not run.registration_open:
            return Response(
                {'error': 'Регистрация на этот прогон закрыта', 'code': 'registration_closed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, не является ли пользователь мастером
        if request.user in run.masters.all():
            return Response(
                {'error': 'Мастер не может зарегистрироваться как игрок на свой прогон', 'code': 'is_master'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, не зарегистрирован ли уже
        if Registration.objects.filter(run=run, user=request.user).exists():
            return Response(
                {'error': 'Вы уже зарегистрированы на этот прогон', 'code': 'already_registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Если прогон привязан к проведению конвента, проверяем подтверждённую регистрацию
        if run.convention_event:
            has_confirmed_registration = ConventionEventRegistration.objects.filter(
                convention_event=run.convention_event,
                user=request.user,
                status='confirmed'
            ).exists()
            if not has_confirmed_registration:
                return Response(
                    {'error': 'Для регистрации на игры конвента необходимо быть подтверждённым участником конвента', 'code': 'event_registration_required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Получаем данные регистрации
        role_preference = request.data.get('role_preference', 'any')
        is_technician = request.data.get('is_technician', False)
        comment = request.data.get('comment', '')
        
        # Определяем статус регистрации
        if is_technician:
            # Игротехники регистрируются отдельно, их не нужно подтверждать
            registration_status = 'pending'
        elif run.is_full():
            # Если прогон заполнен, добавляем в лист ожидания
            registration_status = 'waitlist'
        else:
            # По умолчанию заявка ожидает подтверждения мастером
            registration_status = 'pending'
        
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
        
        delete_run_registration(registration)

        return Response({
            'message': 'Регистрация отменена',
            'run': RunSerializer(run, context={'request': request}).data
        })
    
    @action(detail=True, methods=['get'])
    def registrations(self, request, pk=None):
        """Получить список регистраций на прогон (для мастера/организатора конвента/staff)"""
        run = self.get_object()
        if not can_manage_run_registrations(request.user, run):
            return Response(
                {'error': 'Только мастер прогона или организатор конвента может просматривать регистрации'},
                status=status.HTTP_403_FORBIDDEN
            )
        registrations = run.registrations.select_related('user').all()
        return Response(RegistrationSerializer(registrations, many=True, context={'request': request}).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_registration(self, request, pk=None):
        """Обновить статус регистрации (для мастера/организатора конвента/staff)"""
        run = self.get_object()
        
        # Проверяем права: staff, мастер прогона или организатор конвента (если игра на конвенте)
        can_manage = False
        if request.user.is_staff:
            can_manage = True
        elif request.user in run.masters.all():
            can_manage = True
        elif run.convention_event:
            if request.user in run.convention_event.organizers.all():
                can_manage = True
            elif request.user in run.convention_event.convention.organizers.all():
                can_manage = True
        
        if not can_manage:
            return Response(
                {'error': 'Только мастер прогона или организатор конвента может изменять регистрации'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        registration_id = request.data.get('registration_id')
        new_status = request.data.get('status')
        
        if not registration_id or not new_status:
            return Response(
                {'error': 'Укажите registration_id и status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status not in ['pending', 'confirmed', 'rejected', 'cancelled', 'waitlist']:
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
    queryset = Venue.objects.select_related('city', 'city__region').prefetch_related('rooms').all()
    serializer_class = VenueSerializer
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.action == 'destroy':
            # Удалять может только staff
            return [IsAdminUser()]
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != 'list':
            return queryset

        # Поиск по названию и адресу
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(address__icontains=search))

        # Фильтр по городу
        city_id = int_param(self.request, 'city')
        if city_id is not None:
            queryset = queryset.filter(city_id=city_id)

        return queryset.order_by('name', 'id')


class RoomViewSet(viewsets.ModelViewSet):
    """API для помещений"""
    queryset = Room.objects.select_related('venue', 'venue__city').all()
    serializer_class = RoomSerializer
    
    def get_permissions(self):
        if self.action == 'destroy':
            # Удалять может только staff
            return [IsAdminUser()]
        if self.action in ['create', 'update', 'partial_update']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по площадке
        venue_id = self.request.query_params.get('venue')
        if venue_id:
            queryset = queryset.filter(venue_id=venue_id)
        
        # Фильтр по blackbox
        blackbox = self.request.query_params.get('blackbox')
        if blackbox is not None:
            queryset = queryset.filter(blackbox=blackbox.lower() == 'true')
        
        return queryset.order_by('venue__name', 'name')


class ConventionViewSet(viewsets.ModelViewSet):
    """API для конвентов (просмотр, создание, редактирование)"""
    serializer_class = ConventionSerializer
    queryset = Convention.objects.prefetch_related('organizers', 'links').all()
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != 'list':
            return queryset

        queryset = queryset.annotate(_events_count=count_subquery(ConventionEvent.objects.all(), 'convention'))

        # Поиск по названию
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset.order_by('name', 'id')

    def get_permissions(self):
        if self.action == 'import_csv':
            # Импорт доступен только staff
            return [IsAdminUser()]
        if self.action in ['create', 'update', 'partial_update', 'destroy',
                           'add_organizer', 'remove_organizer']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def check_object_permissions(self, request, obj):
        """Проверяем, что пользователь — организатор конвента или staff"""
        super().check_object_permissions(request, obj)
        if request.method in ['PUT', 'PATCH', 'DELETE'] or self.action in ['add_organizer', 'remove_organizer']:
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
        
        if not csv_file.name.lower().endswith('.csv'):
            return Response(
                {'error': 'Файл должен быть в формате CSV'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            decoded = csv_file.read().decode('utf-8-sig')
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
                    new_event = ConventionEvent.objects.create(
                        convention=convention,
                        city=city,
                        date_start=date_start,
                        date_end=date_end
                    )
                    # Наследуем организаторов от конвента
                    new_event.organizers.set(convention.organizers.all())
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
    pagination_class = StandardPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return ConventionEventListSerializer
        return ConventionEventSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'registrations']:
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
            'convention', 'city', 'city__region', 'venue'
        )
        if self.action == 'list':
            return self.filter_list_queryset(queryset)

        # Используем явный Prefetch для надёжной загрузки прогонов и игр
        runs_queryset = Run.objects.select_related('game').defer('game__announcement', 'game__red_flags')
        if self.action == 'schedule':
            # Расписание отдаётся одним запросом к API: всё нужное прогонам загружаем заранее
            runs_queryset = runs_queryset.select_related('city').prefetch_related(
                'masters',
                Prefetch('rooms', queryset=Room.objects.select_related('venue'))
            ).annotate(_registered_count=active_registrations_count())

        return queryset.prefetch_related(
            Prefetch('scheduled_runs', queryset=runs_queryset.order_by('date', 'id')),
            'organizers',
            'convention__organizers',
            'convention__links',
            'venue__rooms',
            'common_events'
        ).order_by('-date_start')

    def filter_list_queryset(self, queryset):
        """Фильтры, счётчики и сортировка для списка проведений"""
        user = self.request.user
        queryset = queryset.annotate(
            _runs_count=count_subquery(Run.objects.all(), 'convention_event'),
            _confirmed_count=count_subquery(
                ConventionEventRegistration.objects.filter(status='confirmed'), 'convention_event'
            ),
            _pending_count=count_subquery(
                ConventionEventRegistration.objects.filter(status='pending'), 'convention_event'
            ),
        )
        if user.is_authenticated:
            # Собственная регистрация пользователя — одним запросом на всю страницу
            queryset = queryset.prefetch_related(Prefetch(
                'event_registrations',
                queryset=ConventionEventRegistration.objects.filter(user=user).select_related('user'),
                to_attr='_my_registrations'
            ))
            if not user.is_staff:
                queryset = queryset.annotate(
                    _user_is_organizer=event_organizer_exists(user, 'pk', 'convention_id')
                )

        # Фильтр по конвенту
        convention_id = int_param(self.request, 'convention')
        if convention_id is not None:
            queryset = queryset.filter(convention_id=convention_id)

        # Фильтр по городу
        city_id = int_param(self.request, 'city')
        if city_id is not None:
            queryset = queryset.filter(city_id=city_id)

        # Фильтр по площадке
        venue_id = int_param(self.request, 'venue')
        if venue_id is not None:
            queryset = queryset.filter(venue_id=venue_id)

        # Проведения, где текущий пользователь организатор или зарегистрирован
        if bool_param(self.request, 'mine'):
            if not user.is_authenticated:
                return queryset.none()
            queryset = queryset.filter(
                Q(pk__in=ConventionEvent.organizers.through.objects.filter(
                    user_id=user.id
                ).values('conventionevent_id')) |
                Q(convention_id__in=Convention.organizers.through.objects.filter(
                    user_id=user.id
                ).values('convention_id')) |
                Q(pk__in=ConventionEventRegistration.objects.filter(user=user).values('convention_event_id'))
            )

        # Фильтр по времени: upcoming (предстоящие), past (прошедшие), all (все, по умолчанию)
        time_filter = choice_param(self.request, 'time', TIME_CHOICES, 'all')
        today = timezone.localdate()
        if time_filter == 'upcoming':
            queryset = queryset.filter(date_end__gte=today)
            return queryset.order_by('date_start', 'id')  # Ближайшие первыми
        elif time_filter == 'past':
            queryset = queryset.filter(date_end__lt=today)

        return queryset.order_by('-date_start', '-id')  # Недавно прошедшие первыми
    
    def perform_create(self, serializer):
        """При создании проведения конвента наследуем организаторов от конвента"""
        self.check_convention_permission(serializer.validated_data['convention'])
        event = serializer.save()
        # Копируем организаторов из конвента
        convention_organizers = event.convention.organizers.all()
        event.organizers.set(convention_organizers)

    def perform_update(self, serializer):
        """При переносе проведения в другой конвент проверяем права на этот конвент"""
        convention = serializer.validated_data.get('convention')
        if convention is not None and convention != serializer.instance.convention:
            self.check_convention_permission(convention)
        serializer.save()

    def check_convention_permission(self, convention):
        """Создавать проведения конвента может только его организатор или staff"""
        user = self.request.user
        if not user.is_staff and user not in convention.organizers.all():
            raise PermissionDenied('Только организатор конвента может создавать его проведения')
    
    @action(detail=False, methods=['get'])
    def cities(self, request):
        """Получить список городов, в которых есть проведения конвентов"""
        cities = City.objects.filter(
            convention_events__isnull=False
        ).distinct().order_by('name').values('id', 'name')
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
        serializer = ScheduleRunSerializer(
            data=request.data, 
            context={
                'request': request,
                'city_timezone': event.city.timezone if event.city else None
            }
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что дата прогона попадает в даты проведения конвента
        error = date_outside_event_error(serializer.validated_data['date'], event, 'прогона')
        if error:
            return Response({'date': [error]}, status=status.HTTP_400_BAD_REQUEST)
        
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
        serializer = ScheduleRunSerializer(
            run, 
            data=update_data, 
            partial=True, 
            context={
                'request': request,
                'city_timezone': run.city.timezone if run.city else None
            }
        )
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
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_organizer(self, request, pk=None):
        """Добавить организатора к проведению конвента"""
        event = self.get_object()
        
        # Проверяем права
        if not request.user.is_staff:
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Только организатор может добавлять других организаторов'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        username = request.data.get('username')
        if not username:
            return Response({'error': 'Укажите имя пользователя'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        if user in event.organizers.all():
            return Response({'error': 'Пользователь уже является организатором'}, status=status.HTTP_400_BAD_REQUEST)
        
        event.organizers.add(user)
        return Response(ConventionEventSerializer(event, context={'request': request}).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def remove_organizer(self, request, pk=None):
        """Удалить организатора из проведения конвента"""
        event = self.get_object()
        
        # Проверяем права
        if not request.user.is_staff:
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Только организатор может удалять других организаторов'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({'error': 'Укажите ID пользователя'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
        
        if user not in event.organizers.all():
            return Response({'error': 'Пользователь не является организатором'}, status=status.HTTP_400_BAD_REQUEST)
        
        event.organizers.remove(user)
        return Response(ConventionEventSerializer(event, context={'request': request}).data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_common_event(self, request, pk=None):
        """Добавить общее событие в расписание конвента"""
        event = self.get_object()
        
        # Проверяем права
        if not request.user.is_staff:
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Только организатор может добавлять события в расписание'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Создаём общее событие
        serializer = CommonEventSerializer(
            data=request.data, 
            context={
                'request': request,
                'city_timezone': event.city.timezone if event.city else None
            }
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что дата события попадает в даты проведения конвента
        error = date_outside_event_error(serializer.validated_data['date'], event, 'события')
        if error:
            return Response({'date': [error]}, status=status.HTTP_400_BAD_REQUEST)
        
        common_event = serializer.save(convention_event=event)
        
        return Response(
            CommonEventSerializer(common_event, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def update_common_event(self, request, pk=None):
        """Обновить общее событие в расписании конвента"""
        event = self.get_object()
        common_event_id = request.data.get('common_event_id')
        
        if not common_event_id:
            return Response({'error': 'common_event_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            common_event = CommonEvent.objects.get(id=common_event_id, convention_event=event)
        except CommonEvent.DoesNotExist:
            return Response({'error': 'Событие не найдено'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем права
        if not request.user.is_staff:
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Нет прав для редактирования этого события'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Обновляем событие
        update_data = {k: v for k, v in request.data.items() if k != 'common_event_id'}
        serializer = CommonEventSerializer(
            common_event, 
            data=update_data, 
            partial=True, 
            context={
                'request': request,
                'city_timezone': event.city.timezone if event.city else None
            }
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def remove_common_event(self, request, pk=None):
        """Удалить общее событие из расписания конвента"""
        event = self.get_object()
        common_event_id = request.query_params.get('common_event_id')
        
        if not common_event_id:
            return Response({'error': 'common_event_id обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            common_event = CommonEvent.objects.get(id=common_event_id, convention_event=event)
        except CommonEvent.DoesNotExist:
            return Response({'error': 'Событие не найдено'}, status=status.HTTP_404_NOT_FOUND)
        
        # Проверяем права
        if not request.user.is_staff:
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Нет прав для удаления этого события'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        common_event.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    # === Регистрация участников на конвент ===
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request, pk=None):
        """Зарегистрироваться на конвент"""
        event = self.get_object()

        # На завершившийся конвент зарегистрироваться нельзя (сегодня — по времени города проведения)
        if event_local_date(timezone.now(), event) > event.date_end:
            return Response(
                {'error': 'Конвент уже завершился', 'code': 'event_past'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, открыта ли регистрация
        if not event.registration_open:
            return Response(
                {'error': 'Регистрация на этот конвент закрыта', 'code': 'registration_closed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, не зарегистрирован ли уже
        if ConventionEventRegistration.objects.filter(
            convention_event=event, 
            user=request.user
        ).exists():
            return Response(
                {'error': 'Вы уже зарегистрированы на этот конвент', 'code': 'already_registered'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем, не заполнен ли конвент
        if event.is_full():
            return Response(
                {'error': 'Все места на конвент заняты', 'code': 'event_full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем комментарий
        comment = request.data.get('comment', '')
        
        # Создаём регистрацию со статусом pending (ожидает подтверждения)
        registration = ConventionEventRegistration.objects.create(
            convention_event=event,
            user=request.user,
            status='pending',
            comment=comment
        )
        
        return Response({
            'registration': ConventionEventRegistrationSerializer(
                registration, context={'request': request}
            ).data,
            'message': 'Заявка отправлена и ожидает подтверждения организатором'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def unregister(self, request, pk=None):
        """Отменить регистрацию на конвент"""
        event = self.get_object()
        
        try:
            registration = ConventionEventRegistration.objects.get(
                convention_event=event, 
                user=request.user
            )
        except ConventionEventRegistration.DoesNotExist:
            return Response(
                {'error': 'Вы не зарегистрированы на этот конвент'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Удаляем регистрацию
        registration.delete()

        # Вместе с ней снимаем заявки на предстоящие прогоны этого проведения:
        # без регистрации на конвент участвовать в них нельзя
        run_registrations = Registration.objects.filter(
            user=request.user,
            run__convention_event=event,
            run__date__gte=timezone.now()
        ).select_related('run')
        runs_unregistered = 0
        for run_registration in run_registrations:
            delete_run_registration(run_registration)
            runs_unregistered += 1

        return Response({
            'message': 'Регистрация отменена',
            'runs_unregistered': runs_unregistered
        })
    
    @action(detail=True, methods=['get'])
    def registrations(self, request, pk=None):
        """Получить список регистраций на конвент (только для организаторов)"""
        event = self.get_object()

        if not can_manage_event(request.user, event):
            return Response(
                {'error': 'Только организатор может просматривать регистрации'},
                status=status.HTTP_403_FORBIDDEN
            )

        registrations = event.event_registrations.select_related('user').all()
        return Response(
            ConventionEventRegistrationSerializer(
                registrations, many=True, context={'request': request}
            ).data
        )
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def update_registration(self, request, pk=None):
        """Обновить статус регистрации (только для организаторов)"""
        event = self.get_object()
        
        # Проверяем права
        if not request.user.is_staff:
            is_event_organizer = request.user in event.organizers.all()
            is_convention_organizer = request.user in event.convention.organizers.all()
            if not is_event_organizer and not is_convention_organizer:
                return Response(
                    {'error': 'Только организатор может изменять регистрации'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        registration_id = request.data.get('registration_id')
        new_status = request.data.get('status')
        admin_comment = request.data.get('admin_comment')
        
        if not registration_id:
            return Response(
                {'error': 'Укажите registration_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_status and new_status not in ['pending', 'confirmed', 'rejected', 'cancelled']:
            return Response(
                {'error': 'Недопустимый статус'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            registration = ConventionEventRegistration.objects.get(
                id=registration_id, 
                convention_event=event
            )
        except ConventionEventRegistration.DoesNotExist:
            return Response(
                {'error': 'Регистрация не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Обновляем статус если передан
        if new_status:
            registration.status = new_status
        
        # Обновляем комментарий организатора если передан
        if admin_comment is not None:
            registration.admin_comment = admin_comment
        
        registration.save()
        
        return Response({
            'registration': ConventionEventRegistrationSerializer(
                registration, context={'request': request}
            ).data
        })


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
