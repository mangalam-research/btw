# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lexicography', '0003_auto_20150609_1331'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='otherauthority',
            name='authority_ptr',
        ),
        migrations.DeleteModel(
            name='OtherAuthority',
        ),
        migrations.RemoveField(
            model_name='userauthority',
            name='user',
        ),
        migrations.RemoveField(
            model_name='userauthority',
            name='authority_ptr',
        ),
        migrations.DeleteModel(
            name='UserAuthority',
        ),
        migrations.DeleteModel(
            name='Authority',
        ),
    ]
