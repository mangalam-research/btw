# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('catid', models.IntegerField(max_length=7, unique=True, null=True)),
                ('path', models.TextField(unique=True, db_column=b'path')),
                ('heading', models.TextField()),
                ('parent', models.ForeignKey(related_name='children', blank=True, to='semantic_fields.Category', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Lexeme',
            fields=[
                ('htid', models.IntegerField(max_length=7, serialize=False, primary_key=True)),
                ('word', models.CharField(max_length=60)),
                ('fulldate', models.CharField(max_length=90)),
                ('catorder', models.IntegerField(max_length=3)),
                ('category', models.ForeignKey(to='semantic_fields.Category')),
            ],
            options={
                'ordering': ['catorder'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SearchWord',
            fields=[
                ('sid', models.IntegerField(max_length=7, serialize=False, primary_key=True)),
                ('searchword', models.CharField(max_length=60, db_index=True)),
                ('type', models.CharField(max_length=3)),
                ('htid', models.ForeignKey(to='semantic_fields.Lexeme')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='lexeme',
            unique_together=set([('category', 'catorder')]),
        ),
    ]
