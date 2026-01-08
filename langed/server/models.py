from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Region(models.Model):
    """Модель региона"""
    
    name = models.CharField(max_length=255, verbose_name='Название')
    
    class Meta:
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'
        ordering = ['name']

    def __str__(self):
        return self.name


class City(models.Model):
    """Модель города"""
    
    TIMEZONE_CHOICES = [
        ('Europe/Kaliningrad', 'Калининград (UTC+2)'),
        ('Europe/Moscow', 'Москва (UTC+3)'),
        ('Europe/Samara', 'Самара (UTC+4)'),
        ('Asia/Yekaterinburg', 'Екатеринбург (UTC+5)'),
        ('Asia/Omsk', 'Омск (UTC+6)'),
        ('Asia/Krasnoyarsk', 'Красноярск (UTC+7)'),
        ('Asia/Irkutsk', 'Иркутск (UTC+8)'),
        ('Asia/Yakutsk', 'Якутск (UTC+9)'),
        ('Asia/Vladivostok', 'Владивосток (UTC+10)'),
        ('Asia/Magadan', 'Магадан (UTC+11)'),
        ('Asia/Kamchatka', 'Камчатка (UTC+12)'),
    ]
    
    name = models.CharField(max_length=255, verbose_name='Название')
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name='cities',
        verbose_name='Регион',
        null=True,
        blank=True
    )
    timezone = models.CharField(
        max_length=50,
        choices=TIMEZONE_CHOICES,
        default='Europe/Moscow',
        verbose_name='Часовой пояс'
    )
    
    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['name']

    def __str__(self):
        if self.region:
            return f'{self.name} ({self.region.name})'
        return self.name


class Game(models.Model):
    """Модель игры"""
    
    name = models.CharField(max_length=255, verbose_name='Название')
    creators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='games',
        verbose_name='Создатели',
        blank=True
    )
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
    
    technicians = models.PositiveIntegerField(default=0, verbose_name='Игротехники')
    
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
    organizers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='organized_conventions',
        verbose_name='Организаторы',
        blank=True
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Конвент'
        verbose_name_plural = 'Конвенты'
        ordering = ['name']

    def __str__(self):
        return self.name


class ConventionLink(models.Model):
    """Модель внешней ссылки конвента"""
    
    LINK_TYPE_CHOICES = [
        ('vk', 'ВКонтакте'),
        ('telegram', 'Telegram'),
        ('website', 'Сайт'),
        ('discord', 'Discord'),
        ('youtube', 'YouTube'),
        ('other', 'Другое'),
    ]
    
    convention = models.ForeignKey(
        Convention,
        on_delete=models.CASCADE,
        related_name='links',
        verbose_name='Конвент'
    )
    url = models.URLField(max_length=500, verbose_name='URL')
    link_type = models.CharField(
        max_length=20,
        choices=LINK_TYPE_CHOICES,
        default='other',
        verbose_name='Тип ссылки'
    )
    title = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Название',
        help_text='Опциональное название ссылки (если не указано, используется тип)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Ссылка конвента'
        verbose_name_plural = 'Ссылки конвентов'
        ordering = ['link_type', 'title']

    def __str__(self):
        return f'{self.convention.name} — {self.get_link_type_display()}'
    
    def get_display_title(self):
        """Возвращает название для отображения"""
        return self.title if self.title else self.get_link_type_display()


class ConventionEvent(models.Model):
    """Модель проведения конвента"""
    
    convention = models.ForeignKey(
        Convention,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='Конвент'
    )
    organizers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='organized_convention_events',
        verbose_name='Организаторы',
        blank=True
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='convention_events',
        verbose_name='Город'
    )
    date_start = models.DateField(verbose_name='Дата начала')
    date_end = models.DateField(verbose_name='Дата окончания')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Проведение конвента'
        verbose_name_plural = 'Проведения конвентов'
        ordering = ['date_start']

    def __str__(self):
        return f'{self.convention.name} — {self.city.name} ({self.date_start.strftime("%d.%m.%Y")} - {self.date_end.strftime("%d.%m.%Y")})'

    def clean(self):
        if self.date_start > self.date_end:
            raise ValidationError('Дата начала не может быть позже даты окончания')


class Venue(models.Model):
    """Модель площадки (место проведения)"""
    
    name = models.CharField(max_length=255, verbose_name='Название')
    address = models.TextField(blank=True, verbose_name='Адрес')
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='venues',
        verbose_name='Город'
    )
    description = models.TextField(blank=True, verbose_name='Описание')
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Вместимость'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Площадка'
        verbose_name_plural = 'Площадки'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.city.name})'


class Room(models.Model):
    """Модель помещения на площадке"""
    
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name='rooms',
        verbose_name='Площадка'
    )
    name = models.CharField(max_length=255, verbose_name='Название')
    blackbox = models.BooleanField(default=False, verbose_name='Blackbox')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Помещение'
        verbose_name_plural = 'Помещения'
        ordering = ['name']

    def __str__(self):
        blackbox_mark = ' [blackbox]' if self.blackbox else ''
        return f'{self.name}{blackbox_mark} — {self.venue.name}'


class Run(models.Model):
    """Модель прогона (сеанс игры)"""
    
    game = models.ForeignKey(
        Game,
        on_delete=models.CASCADE,
        related_name='runs',
        verbose_name='Игра'
    )
    masters = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='runs',
        verbose_name='Мастера',
        blank=True
    )
    date = models.DateTimeField(verbose_name='Дата и время прогона')
    duration = models.PositiveIntegerField(
        default=180,
        verbose_name='Продолжительность (минут)',
        help_text='Продолжительность прогона в минутах'
    )
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name='runs',
        verbose_name='Город'
    )
    rooms = models.ManyToManyField(
        Room,
        related_name='runs',
        verbose_name='Помещения',
        blank=True
    )
    convention_event = models.ForeignKey(
        ConventionEvent,
        on_delete=models.SET_NULL,
        related_name='scheduled_runs',
        verbose_name='Проведение конвента',
        null=True,
        blank=True
    )
    max_players = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Максимум игроков',
        help_text='Если не указано, берётся из игры'
    )
    registration_open = models.BooleanField(
        default=True,
        verbose_name='Регистрация открыта'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Прогон'
        verbose_name_plural = 'Прогоны'
        ordering = ['date']

    def __str__(self):
        return f'{self.game.name} — {self.city.name} ({self.date.strftime("%d.%m.%Y %H:%M")})'
    
    def get_max_players(self):
        """Возвращает максимальное количество игроков для этого прогона"""
        if self.max_players is not None:
            return self.max_players
        return self.game.players_max
    
    def get_registered_count(self):
        """Возвращает количество зарегистрированных игроков"""
        return self.registrations.filter(
            status__in=['confirmed', 'pending'],
            is_technician=False
        ).count()
    
    def get_available_slots(self):
        """Возвращает количество свободных мест"""
        max_players = self.get_max_players()
        registered = self.get_registered_count()
        return max(0, max_players - registered)
    
    def is_full(self):
        """Проверяет, заполнен ли прогон"""
        return self.get_available_slots() == 0


class Registration(models.Model):
    """Модель регистрации игрока на прогон"""
    
    ROLE_CHOICES = [
        ('any', 'Любая'),
        ('female', 'Женская'),
        ('male', 'Мужская'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждена'),
        ('cancelled', 'Отменена'),
        ('waitlist', 'В листе ожидания'),
    ]
    
    run = models.ForeignKey(
        Run,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name='Прогон'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registrations',
        verbose_name='Пользователь'
    )
    role_preference = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='any',
        verbose_name='Предпочтение по роли'
    )
    is_technician = models.BooleanField(
        default=False,
        verbose_name='Игротехник'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='confirmed',
        verbose_name='Статус'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий',
        help_text='Дополнительная информация от игрока'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Регистрация'
        verbose_name_plural = 'Регистрации'
        ordering = ['created_at']
        unique_together = ['run', 'user']

    def __str__(self):
        role_info = ' (игротехник)' if self.is_technician else ''
        return f'{self.user.username} → {self.run.game.name}{role_info}'
    
    def clean(self):
        # Проверяем, что пользователь не является мастером этого прогона
        if hasattr(self, 'run') and hasattr(self, 'user'):
            if self.run.masters.filter(id=self.user.id).exists():
                raise ValidationError('Мастер не может зарегистрироваться как игрок на свой прогон')
