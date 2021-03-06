# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings
import bibliography.models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('uid', bibliography.models.ZoteroUIDField(max_length=22)),
                ('item_key', models.CharField(max_length=16)),
                ('date', models.TextField(null=True)),
                ('title', models.TextField(null=True)),
                ('creators', models.TextField(null=True)),
                ('item', models.TextField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PrimarySource',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('reference_title', models.TextField(default=None, unique=True, validators=[
                 django.core.validators.RegexValidator('[^\\s]', 'This field cannot contain only spaces.')])),
                ('genre', models.CharField(default=None, max_length=2, choices=[('SU', 'Sūtra'), (
                    'SH', 'Śāstra'), ('AV', 'Avadāna'), ('LI', 'Literary Text'), ('PA', 'Pāli')])),
                ('item', models.ForeignKey(related_name='primary_sources',
                                           to='bibliography.Item', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name_plural': 'Primary sources',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ZoteroUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('uid', bibliography.models.ZoteroUIDField(max_length=22)),
                ('api_key', bibliography.models.ZoteroAPIKeyField(max_length=48)),
                ('btw_user', models.OneToOneField(
                    to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
