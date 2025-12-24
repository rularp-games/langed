from django.contrib import admin
from .models import Game, City, Convention, Run


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'region')
    list_filter = ('region',)
    search_fields = ('name', 'region')
    ordering = ('name',)


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'players_min', 'players_max', 'female_roles_min', 'female_roles_max', 
                    'male_roles_min', 'male_roles_max', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'announcement', 'red_flags')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'poster', 'announcement', 'red_flags')
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
    )


@admin.register(Convention)
class ConventionAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'date_start', 'date_end', 'created_at')
    list_filter = ('city', 'date_start')
    search_fields = ('name', 'description', 'city__name')
    ordering = ('date_start',)
    date_hierarchy = 'date_start'
    autocomplete_fields = ('city',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'city', 'description')
        }),
        ('Даты', {
            'fields': (('date_start', 'date_end'),)
        }),
    )


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('game', 'city', 'date', 'convention', 'created_at')
    list_filter = ('city', 'convention', 'date')
    search_fields = ('game__name', 'city__name', 'convention__name')
    date_hierarchy = 'date'
    autocomplete_fields = ('game', 'city', 'convention')
    fieldsets = (
        ('Основная информация', {
            'fields': ('game', 'city', 'convention')
        }),
        ('Дата', {
            'fields': ('date',)
        }),
    )
