from django.contrib import admin
from .models import Game, Run, Convention


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'has_poster', 'players_min', 'players_max', 'female_roles_min', 'female_roles_max', 
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
    
    def has_poster(self, obj):
        return bool(obj.poster)
    has_poster.boolean = True
    has_poster.short_description = 'Постер'


@admin.register(Convention)
class ConventionAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'date_start', 'date_end', 'runs_count', 'created_at')
    list_filter = ('city', 'date_start', 'date_end')
    search_fields = ('name', 'city', 'description')
    date_hierarchy = 'date_start'
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'city', 'description')
        }),
        ('Даты проведения', {
            'fields': (('date_start', 'date_end'),)
        }),
    )
    
    def runs_count(self, obj):
        return obj.runs.count()
    runs_count.short_description = 'Прогонов'


@admin.register(Run)
class RunAdmin(admin.ModelAdmin):
    list_display = ('game', 'city', 'date', 'convention', 'created_at')
    list_filter = ('city', 'date', 'game', 'convention')
    search_fields = ('game__name', 'city', 'convention__name')
    date_hierarchy = 'date'
    autocomplete_fields = ['game', 'convention']
    fieldsets = (
        ('Информация о прогоне', {
            'fields': ('game', 'city', 'date', 'convention')
        }),
    )
