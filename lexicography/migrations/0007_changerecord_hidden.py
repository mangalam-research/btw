# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lexicography', '0006_chunkmetadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='changerecord',
            name='hidden',
            field=models.BooleanField(default=False, db_index=True),
        ),
    ]
