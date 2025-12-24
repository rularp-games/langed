from django.contrib import admin
from .models import Game, Run


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'players_min', 'players_max', 'female_roles_min', 'female_roles_max', 
                    'male_roles_min', 'male_roles_max', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'announcement', 'red_flags')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'announcement', 'red_flags')
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


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('game', 'city', 'date', 'created_at')
    list_filter = ('city', 'date', 'game')
    search_fields = ('game__name', 'city')
    date_hierarchy = 'date'
    autocomplete_fields = ['game']
    fieldsets = (
        ('Информация о прогоне', {
            'fields': ('game', 'city', 'date')
        }),
    )
