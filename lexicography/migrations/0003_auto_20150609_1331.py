# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('lexicography', '0002_auto_20150428_0821'),
    ]

    operations = [
        migrations.AddField(
            model_name='changerecord',
            name='note',
            field=models.CharField(max_length=1024, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='changerecord',
            name='ctype',
            field=models.CharField(max_length=1, choices=[
                ('C', 'Create'),
                ('U', 'Update'), ('R', 'Revert'),
                ('V', 'Version update')]),
            preserve_default=True,
        ),
    ]
