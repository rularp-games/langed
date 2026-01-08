from django.contrib import admin
from django import forms
from django.contrib import messages
from django.utils import timezone
from datetime import time
from .models import Game, City, Region, Convention, ConventionEvent, Run, ConventionLink, Venue


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
        return ', '.join([str(c) for c in obj.creators.all()])
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
        return ', '.join([str(o) for o in obj.organizers.all()])
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


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'address', 'capacity', 'runs_count', 'created_at')
    list_filter = ('city', 'city__region')
    search_fields = ('name', 'address', 'city__name', 'description')
    ordering = ('name',)
    autocomplete_fields = ('city',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'city', 'address')
        }),
        ('Дополнительно', {
            'fields': ('description', 'capacity')
        }),
    )
    
    def runs_count(self, obj):
        return obj.runs.count()
    runs_count.short_description = 'Прогонов'


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('game', 'get_masters', 'city', 'venue', 'date', 'convention_event', 'created_at')
    list_filter = ('city', 'venue', 'convention_event', 'date')
    search_fields = ('game__name', 'city__name', 'venue__name', 'convention_event__convention__name', 'masters__username', 'masters__first_name', 'masters__last_name')
    date_hierarchy = 'date'
    autocomplete_fields = ('game', 'city', 'venue', 'convention_event')
    filter_horizontal = ('masters',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('game', 'masters', 'city', 'venue', 'convention_event')
        }),
        ('Дата', {
            'fields': ('date',)
        }),
    )
    
    def get_masters(self, obj):
        return ', '.join([str(m) for m in obj.masters.all()])
    get_masters.short_description = 'Мастера'
