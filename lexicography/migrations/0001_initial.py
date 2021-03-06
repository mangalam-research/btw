# -*- coding: utf-8 -*-


from django.db import models, migrations
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Authority',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
                'verbose_name_plural': 'Authorities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ChangeRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('lemma', models.CharField(max_length=1024)),
                ('datetime', models.DateTimeField()),
                ('session', models.CharField(max_length=100, null=True)),
                ('ctype', models.CharField(max_length=1, choices=[
                 ('C', 'Create'), ('U', 'Update'), ('R', 'Revert')])),
                ('csubtype', models.CharField(max_length=1, choices=[
                 ('A', 'Automatic'), ('M', 'Manual'), ('R', 'Recovery')])),
                ('published', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Chunk',
            fields=[
                ('c_hash', models.CharField(help_text='This is the primary key for chunks. It is a hash of the <code>data</code> field.',
                                            max_length=40, serialize=False, primary_key=True)),
                ('is_normal', models.BooleanField(default=True,
                                                  help_text="A 'normal' chunk is one that is well-formed XML")),
                ('schema_version', models.CharField(
                    help_text='This is the version of the btw-storage schema that ought to be used to validate this chunk.', max_length=10)),
                ('_valid', models.NullBooleanField(help_text='Whether this chunk is valid when validated against the schema version specified in the <code>schema_version</code> field. You do not normally access this field through <code>valid</code>.', db_column='valid')),
                ('data', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DeletionChange',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('ctype', models.CharField(max_length=1, choices=[
                 ('D', 'Delete'), ('U', 'Undelete')])),
                ('datetime', models.DateTimeField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Entry',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('lemma', models.CharField(max_length=1024)),
                ('deleted', models.BooleanField(default=False)),
                ('latest', models.ForeignKey(related_name='+',
                                             to='lexicography.ChangeRecord', null=True, on_delete=models.CASCADE)),
                ('latest_published', models.ForeignKey(
                    related_name='+', to='lexicography.ChangeRecord', null=True, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name_plural': 'Entries',
                'permissions': (('garbage_collect', 'Perform a garbage collection.'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntryLock',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('datetime', models.DateTimeField()),
                ('entry', models.ForeignKey(
                    to='lexicography.Entry', on_delete=models.CASCADE)),
                ('owner', models.ForeignKey(
                    to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'Entry lock',
                'verbose_name_plural': 'Entry locks',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Handle',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('session', models.CharField(max_length=100)),
                ('handle', models.IntegerField()),
                ('entry', models.ForeignKey(to='lexicography.Entry',
                                            null=True, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OtherAuthority',
            fields=[
                ('authority_ptr', models.OneToOneField(parent_link=True, auto_created=True,
                                                       primary_key=True, serialize=False, to='lexicography.Authority',
                                                       on_delete=models.CASCADE)),
                ('name', models.CharField(max_length=1024)),
            ],
            options={
                'verbose_name_plural': 'OtherAuthorities',
            },
            bases=('lexicography.authority',),
        ),
        migrations.CreateModel(
            name='PublicationChange',
            fields=[
                ('id', models.AutoField(verbose_name='ID',
                                        serialize=False, auto_created=True, primary_key=True)),
                ('ctype', models.CharField(max_length=1, choices=[
                 ('P', 'Publish'), ('U', 'Unpublish')])),
                ('datetime', models.DateTimeField()),
                ('changerecord', models.ForeignKey(
                    to='lexicography.ChangeRecord', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL,
                                           on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserAuthority',
            fields=[
                ('authority_ptr', models.OneToOneField(parent_link=True, auto_created=True,
                                                       primary_key=True, serialize=False, to='lexicography.Authority',
                                                       on_delete=models.CASCADE)),
                ('user', models.ForeignKey(
                    to=settings.AUTH_USER_MODEL, on_delete=models.PROTECT)),
            ],
            options={
                'verbose_name_plural': 'UserAuthorities',
            },
            bases=('lexicography.authority',),
        ),
        migrations.AlterUniqueTogether(
            name='handle',
            unique_together=set([('session', 'entry'), ('session', 'handle')]),
        ),
        migrations.AlterUniqueTogether(
            name='entrylock',
            unique_together=set([('entry',)]),
        ),
        migrations.AlterUniqueTogether(
            name='entry',
            unique_together=set([('lemma',)]),
        ),
        migrations.AddField(
            model_name='deletionchange',
            name='entry',
            field=models.ForeignKey(
                to='lexicography.Entry', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='deletionchange',
            name='user',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='changerecord',
            name='c_hash',
            field=models.ForeignKey(
                to='lexicography.Chunk', on_delete=django.db.models.deletion.PROTECT),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='changerecord',
            name='entry',
            field=models.ForeignKey(
                to='lexicography.Entry', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='changerecord',
            name='user',
            field=models.ForeignKey(
                to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.PROTECT),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='changerecord',
            unique_together=set([('entry', 'datetime', 'ctype')]),
        ),
    ]
