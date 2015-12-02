# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('semantic_fields', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Category',
            new_name='SemanticField'
        ),
        migrations.AlterField(
            model_name='SemanticField',
            name='parent',
            field=models.ForeignKey(to='semantic_fields.SemanticField',
                                    related_name="children",
                                    null=True, blank=True),
            preserve_default=True
        ),
        migrations.AlterField(
            model_name='lexeme',
            name='category',
            field=models.ForeignKey(to='semantic_fields.SemanticField'),
            preserve_default=True,
        ),
        migrations.RenameField(
            model_name='lexeme',
            old_name='category',
            new_name='semantic_field'
        ),
        migrations.AlterUniqueTogether(
            name='lexeme',
            unique_together=set([('semantic_field', 'catorder')]),
        ),
    ]
