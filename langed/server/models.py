from django.db import models
from django.core.exceptions import ValidationError


class City(models.Model):
    """Модель города"""
    
    name = models.CharField(max_length=255, verbose_name='Название')
    region = models.CharField(max_length=255, blank=True, verbose_name='Регион')
    
    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['name']

    def __str__(self):
        if self.region:
            return f'{self.name} ({self.region})'
        return self.name


class Game(models.Model):
    """Модель игры"""
    
    name = models.CharField(max_length=255, verbose_name='Название')
    poster = models.ImageField(
        upload_to='games/posters/',
        blank=True,
        null=True,
        verbose_name='Постер'
    )
    announcement = models.TextField(blank=True, verbose_name='Анонс')
    red_flags = models.TextField(blank=True, verbose_name='Красные флаги')
    
    players_min = models.PositiveIntegerField(default=1, verbose_name='Минимум игроков')
    players_max = models.PositiveIntegerField(default=10, verbose_name='Максимум игроков')
    
    female_roles_min = models.PositiveIntegerField(default=0, verbose_name='Минимум женских ролей')
    female_roles_max = models.PositiveIntegerField(default=0, verbose_name='Максимум женских ролей')
    
    male_roles_min = models.PositiveIntegerField(default=0, verbose_name='Минимум мужских ролей')
    male_roles_max = models.PositiveIntegerField(default=0, verbose_name='Максимум мужских ролей')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Игра'
        verbose_name_plural = 'Игры'
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def clean(self):
        if self.players_min > self.players_max:
            raise ValidationError('Минимум игроков не может быть больше максимума')
        if self.female_roles_min > self.female_roles_max:
            raise ValidationError('Минимум женских ролей не может быть больше максимума')
        if self.male_roles_min > self.male_roles_max:
            raise ValidationError('Минимум мужских ролей не может быть больше максимума')


class Convention(models.Model):
    """Модель конвента"""
    
    name = models.CharField(max_length=255, verbose_name='Название')
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='conventions',
        verbose_name='Город'
    )
    date_start = models.DateField(verbose_name='Дата начала')
    date_end = models.DateField(verbose_name='Дата окончания')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Конвент'
        verbose_name_plural = 'Конвенты'
        ordering = ['date_start']

    def __str__(self):
        return f'{self.name} — {self.city.name} ({self.date_start.strftime("%d.%m.%Y")} - {self.date_end.strftime("%d.%m.%Y")})'

    def clean(self):
        if self.date_start > self.date_end:
            raise ValidationError('Дата начала не может быть позже даты окончания')


class Run(models.Model):
    """Модель прогона (сеанс игры)"""
    
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='runs',
        verbose_name='Игра'
    )
    date = models.DateTimeField(verbose_name='Дата и время прогона')
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='runs',
        verbose_name='Город'
    )
    convention = models.ForeignKey(
        Convention,
        on_delete=models.SET_NULL,
        related_name='runs',
        verbose_name='Конвент',
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Прогон'
        verbose_name_plural = 'Прогоны'
        ordering = ['date']

    def __str__(self):
        return f'{self.game.name} — {self.city.name} ({self.date.strftime("%d.%m.%Y %H:%M")})'
