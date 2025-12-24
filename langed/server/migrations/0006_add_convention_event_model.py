# Generated manually for adding ConventionEvent model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0005_add_city_model_and_update_relations'),
    ]

    operations = [
        # 1. Создаём модель ConventionEvent
        migrations.CreateModel(
            name='ConventionEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_start', models.DateField(verbose_name='Дата начала')),
                ('date_end', models.DateField(verbose_name='Дата окончания')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('convention', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='events',
                    to='server.convention',
                    verbose_name='Конвент'
                )),
                ('city', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='convention_events',
                    to='server.city',
                    verbose_name='Город'
                )),
                ('games', models.ManyToManyField(
                    blank=True,
                    related_name='convention_events',
                    to='server.game',
                    verbose_name='Игры'
                )),
            ],
            options={
                'verbose_name': 'Проведение конвента',
                'verbose_name_plural': 'Проведения конвентов',
                'ordering': ['date_start'],
            },
        ),
        
        # 2. Удаляем поле convention из Run
        migrations.RemoveField(
            model_name='run',
            name='convention',
        ),
        
        # 3. Добавляем поле convention_event в Run
        migrations.AddField(
            model_name='run',
            name='convention_event',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='runs',
                to='server.conventionevent',
                verbose_name='Проведение конвента'
            ),
        ),
        
        # 4. Удаляем поля из Convention
        migrations.RemoveField(
            model_name='convention',
            name='city',
        ),
        migrations.RemoveField(
            model_name='convention',
            name='date_start',
        ),
        migrations.RemoveField(
            model_name='convention',
            name='date_end',
        ),
        
        # 5. Изменяем ordering для Convention
        migrations.AlterModelOptions(
            name='convention',
            options={
                'ordering': ['name'],
                'verbose_name': 'Конвент',
                'verbose_name_plural': 'Конвенты'
            },
        ),
    ]

