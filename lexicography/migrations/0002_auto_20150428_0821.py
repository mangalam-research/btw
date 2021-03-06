# -*- coding: utf-8 -*-


from django.db import migrations
from ..perms import create_perms

def permissions(apps, schema_editor):
    try:
        # Django <= 1.10
        from django.contrib.contenttypes.management import update_contenttypes
    except ImportError:
        # Django 1.11 and over
        from django.contrib.contenttypes.management import \
            create_contenttypes as update_contenttypes

    from django.apps import apps as configured_apps
    for app in configured_apps.get_app_configs():
        update_contenttypes(app, interactive=True, verbosity=0)

    from django.contrib.auth.management import create_permissions
    for app in configured_apps.get_app_configs():
        create_permissions(app, verbosity=0)

    create_perms(apps)

class Migration(migrations.Migration):

    dependencies = [
        ('lexicography', '0001_initial'),
        ('auth', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(permissions),
    ]
