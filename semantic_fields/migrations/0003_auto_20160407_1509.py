# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('semantic_fields', '0002_auto_20151201_1611'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lexeme',
            name='catorder',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='lexeme',
            name='htid',
            field=models.IntegerField(serialize=False, primary_key=True),
        ),
        migrations.AlterField(
            model_name='searchword',
            name='sid',
            field=models.IntegerField(serialize=False, primary_key=True),
        ),
        migrations.AlterField(
            model_name='semanticfield',
            name='catid',
            field=models.IntegerField(unique=True, null=True),
        ),
    ]
