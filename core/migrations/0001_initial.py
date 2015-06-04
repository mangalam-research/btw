# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from lib.util import PermissionResolver

def cms_editor(apps, schema_editor):
    from django.contrib.contenttypes.management import update_contenttypes
    from django.apps import apps as configured_apps
    for app in configured_apps.get_app_configs():
        update_contenttypes(app, interactive=True, verbosity=0)

    from django.contrib.auth.management import create_permissions
    for app in configured_apps.get_app_configs():
        create_permissions(app, verbosity=0)

    from django.conf import settings

    user_model_name = settings.AUTH_USER_MODEL
    user_app, user_model = user_model_name.rsplit(".", 1)
    User = apps.get_model(user_app, user_model)
    username = "cms-migration-user"

    try:
        fake = User.objects.get(username=username)
    except User.DoesNotExist:
        fake = User.objects.create()
        fake.username = username
        fake.is_active = False
        fake.save()

    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    PageUserGroup = apps.get_model("cms", "PageUserGroup")
    GlobalPagePermission = apps.get_model("cms", "GlobalPagePermission")

    resolver = PermissionResolver(Permission, ContentType)

    perms = [resolver.resolve((x, "cms", "page")) for x in (
        "add_page",
        "change_page",
        "delete_page",
        "edit_static_placeholder",
        "view_page",
        "publish_page",
    )]

    perms.append(resolver.resolve(("use_structure", "cms", "placeholder")))

    pg = PageUserGroup.objects.create(name="CMS scribe", created_by=fake)
    pg.permissions = perms
    pg.save()

    # We create a GlobalPagePermission for our new group with default
    # values.
    global_pp = GlobalPagePermission()
    global_pp.group = pg
    global_pp.save()


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('cms', '0011_auto_20150419_1006')
    ]

    operations = [
        migrations.RunPython(cms_editor),
    ]
