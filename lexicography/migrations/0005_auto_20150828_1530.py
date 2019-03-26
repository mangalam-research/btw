# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lexicography', '0004_auto_20150611_1147'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='deleted',
            field=models.BooleanField(default=False, db_index=True),
            preserve_default=True,
        ),
    ]
