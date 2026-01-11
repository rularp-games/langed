from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django import forms
from django.contrib import messages
from django.utils import timezone
from datetime import time
from .models import Game, City, Region, Convention, ConventionEvent, Run, ConventionLink, Venue, Room, Registration

User = get_user_model()


def get_user_display_name(user):
    """Возвращает отображаемое имя пользователя: first_name + last_name или username"""
    full_name = f'{user.first_name} {user.last_name}'.strip()
    return full_name if full_name else user.username


# Перерегистрируем UserAdmin с поддержкой autocomplete
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'get_display_name', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    
    def get_display_name(self, obj):
        return get_user_display_name(obj)
    get_display_name.short_description = 'Имя'


class ConventionEventForm(forms.ModelForm):
    selected_games = forms.ModelMultipleChoiceField(
        queryset=Game.objects.all().order_by('name'),
        widget=forms.SelectMultiple(attrs={'size': 10}),
        required=False,
        label='Выбрать игры для создания прогонов',
        help_text='При сохранении будут созданы прогоны выбранных игр на дату начала конвента'
    )

    class Meta:
        model = ConventionEvent
        fields = ['convention', 'city', 'date_start', 'date_end']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'cities_count')
    search_fields = ('name',)
    ordering = ('name',)
    
    def cities_count(self, obj):
        return obj.cities.count()
    cities_count.short_description = 'Городов'


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'timezone')
    list_filter = ('region', 'timezone')
    search_fields = ('name', 'region__name')
    ordering = ('name',)
    autocomplete_fields = ('region',)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_creators', 'players_min', 'players_max', 'female_roles_min', 'female_roles_max', 
                    'male_roles_min', 'male_roles_max', 'technicians', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'announcement', 'red_flags', 'creators__username', 'creators__first_name', 'creators__last_name')
    filter_horizontal = ('creators',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'creators', 'poster', 'announcement', 'red_flags')
        }),
        ('Количество игроков', {
            'fields': (('players_min', 'players_max'),)
        }),
        ('Женские роли', {
            'fields': (('female_roles_min', 'female_roles_max'),)
        }),
        ('Мужские роли', {
            'fields': (('male_roles_min', 'male_roles_max'),)
        }),
        ('Игротехники', {
            'fields': ('technicians',)
        }),
    )
    
    def get_creators(self, obj):
        return ', '.join([get_user_display_name(c) for c in obj.creators.all()])
    get_creators.short_description = 'Создатели'


class ConventionLinkInline(admin.TabularInline):
    model = ConventionLink
    extra = 1
    fields = ('link_type', 'url', 'title')


@admin.register(Convention)
class ConventionAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_organizers', 'description', 'links_count', 'created_at')
    list_filter = ()
    search_fields = ('name', 'description', 'organizers__username', 'organizers__first_name', 'organizers__last_name')
    ordering = ('name',)
    filter_horizontal = ('organizers',)
    inlines = [ConventionLinkInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'organizers', 'description')
        }),
    )
    
    def get_organizers(self, obj):
        return ', '.join([get_user_display_name(o) for o in obj.organizers.all()])
    get_organizers.short_description = 'Организаторы'
    
    def links_count(self, obj):
        return obj.links.count()
    links_count.short_description = 'Ссылок'


@admin.register(ConventionLink)
class ConventionLinkAdmin(admin.ModelAdmin):
    list_display = ('convention', 'link_type', 'url', 'title', 'created_at')
    list_filter = ('link_type', 'convention')
    search_fields = ('convention__name', 'url', 'title')
    ordering = ('convention__name', 'link_type')


@admin.register(ConventionEvent)
class ConventionEventAdmin(admin.ModelAdmin):
    form = ConventionEventForm
    list_display = ('convention', 'city', 'date_start', 'date_end', 'runs_count', 'created_at')
    list_filter = ('convention', 'city', 'date_start')
    search_fields = ('convention__name', 'city__name')
    ordering = ('date_start',)
    date_hierarchy = 'date_start'
    autocomplete_fields = ('convention', 'city')

    def get_fieldsets(self, request, obj=None):
        fieldsets = (
            ('Основная информация', {
                'fields': ('convention', 'city')
            }),
            ('Даты', {
                'fields': (('date_start', 'date_end'),)
            }),
            ('Создание прогонов', {
                'fields': ('selected_games',),
                'description': 'Выберите игры для автоматического создания прогонов на дату начала конвента'
            }),
        )

        return fieldsets

    def save_model(self, request, obj, form, change):
        # Save the object first so it has a pk before creating related runs
        super().save_model(request, obj, form, change)

        # Создаем прогоны для выбранных игр
        if 'selected_games' in form.cleaned_data:
            selected_games = form.cleaned_data.get('selected_games')
            if selected_games:
                created_runs = []
                for game in selected_games:
                    # Создаем прогон на дату начала конвента в 10:00
                    run_date = timezone.make_aware(timezone.datetime.combine(obj.date_start, time(10, 0)))
                    run, created = Run.objects.get_or_create(
                        game=game,
                        date=run_date,
                        city=obj.city,
                        convention_event=obj,
                        defaults={
                            'game': game,
                            'date': run_date,
                            'city': obj.city,
                            'convention_event': obj
                        }
                    )
                    if created:
                        created_runs.append(run)

                if created_runs:
                    messages.success(
                        request,
                        f'Создано {len(created_runs)} прогонов для выбранных игр на {run_date.strftime("%d.%m.%Y %H:%M")}.'
                    )
                else:
                    messages.info(
                        request,
                        'Все выбранные игры уже имеют прогоны на эту дату.'
                    )

    def runs_count(self, obj):
        return obj.scheduled_runs.count()
    runs_count.short_description = 'Количество прогонов'


class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    fields = ('name', 'blackbox')


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'address', 'capacity', 'rooms_count', 'created_at')
    list_filter = ('city', 'city__region')
    search_fields = ('name', 'address', 'city__name', 'description')
    ordering = ('name',)
    autocomplete_fields = ('city',)
    inlines = [RoomInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'city', 'address')
        }),
        ('Дополнительно', {
            'fields': ('description', 'capacity')
        }),
    )
    
    def rooms_count(self, obj):
        return obj.rooms.count()
    rooms_count.short_description = 'Помещений'


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'venue', 'blackbox', 'created_at')
    list_filter = ('blackbox', 'venue', 'venue__city')
    search_fields = ('name', 'venue__name', 'venue__city__name')
    ordering = ('venue__name', 'name')
    autocomplete_fields = ('venue',)


class RegistrationInline(admin.TabularInline):
    model = Registration
    extra = 1
    fields = ('user', 'is_technician', 'role_preference', 'status', 'comment')
    autocomplete_fields = ('user',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('game', 'get_masters', 'city', 'get_rooms', 'date', 'convention_event', 'get_players_count', 'get_technicians_count', 'created_at')
    list_filter = ('city', 'rooms__venue', 'convention_event', 'date')
    search_fields = ('game__name', 'city__name', 'rooms__name', 'rooms__venue__name', 'convention_event__convention__name', 'masters__username', 'masters__first_name', 'masters__last_name')
    date_hierarchy = 'date'
    autocomplete_fields = ('game', 'city', 'convention_event')
    filter_horizontal = ('masters', 'rooms')
    inlines = [RegistrationInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('game', 'masters', 'city', 'rooms', 'convention_event')
        }),
        ('Дата и настройки', {
            'fields': ('date', 'duration', 'max_players', 'registration_open')
        }),
    )
    
    def get_masters(self, obj):
        return ', '.join([get_user_display_name(m) for m in obj.masters.all()])
    get_masters.short_description = 'Мастера'
    
    def get_rooms(self, obj):
        return ', '.join([r.name for r in obj.rooms.all()])
    get_rooms.short_description = 'Помещения'
    
    def get_players_count(self, obj):
        return obj.registrations.filter(is_technician=False, status__in=['confirmed', 'pending']).count()
    get_players_count.short_description = 'Игроков'
    
    def get_technicians_count(self, obj):
        return obj.registrations.filter(is_technician=True, status__in=['confirmed', 'pending']).count()
    get_technicians_count.short_description = 'Игротехников'


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'run', 'is_technician', 'role_preference', 'status', 'created_at')
    list_filter = ('is_technician', 'status', 'role_preference', 'run__city', 'run__convention_event')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'run__game__name', 'comment')
    ordering = ('-created_at',)
    autocomplete_fields = ('user', 'run')
    date_hierarchy = 'created_at'
    fieldsets = (
        ('Основная информация', {
            'fields': ('run', 'user', 'is_technician')
        }),
        ('Настройки роли', {
            'fields': ('role_preference', 'status')
        }),
        ('Дополнительно', {
            'fields': ('comment',)
        }),
    )
