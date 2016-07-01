# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('semantic_fields', '0003_auto_20160407_1509'),
        ('lexicography', '0005_auto_20150828_1530'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChunkMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('xml_hash', models.CharField(help_text=b'This is the hash of the last XML we processed for this chunk.', max_length=40)),
                ('chunk', models.OneToOneField(to='lexicography.Chunk')),
                ('semantic_fields', models.ManyToManyField(to='semantic_fields.SemanticField')),
            ],
        ),
    ]
