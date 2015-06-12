# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from lib.util import PermissionResolver

def permissions(apps, schema_editor):
    from django.contrib.contenttypes.management import update_contenttypes
    from django.apps import apps as configured_apps
    for app in configured_apps.get_app_configs():
        update_contenttypes(app, interactive=True, verbosity=0)

    from django.contrib.auth.management import create_permissions
    for app in configured_apps.get_app_configs():
        create_permissions(app, verbosity=0)

    Group = apps.get_model("auth", "Group")

    # Rename the author group if it exists.
    try:
        author_group = Group.objects.get(name="author")
    except Group.DoesNotExist:
        author_group = None

    if author_group:
        author_group.name = "scribe"
        author_group.save()

    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    if Group.objects.filter(name__in=("scribe", "editor")).exists():
        print "You already have an scribe or editor groups in your database."
        print ("Assuming that we are upgrading from a pre-Django 1.7 "
               "installation, and stopping.")
        print
        print ("If the assumption is incorrect, please edit your database "
               "manually.")
        return

    resolver = PermissionResolver(Permission, ContentType)

    scribe_perms = [resolver.resolve(x) for x in [
        ["add_changerecord", "lexicography", "changerecord"],
        ["add_chunk", "lexicography", "chunk"],
        ["add_entry", "lexicography", "entry"],
        ["change_entry", "lexicography", "entry"],
        ["add_entrylock", "lexicography", "entrylock"],
        ["change_entrylock", "lexicography", "entrylock"],
        ["delete_entrylock", "lexicography", "entrylock"],
    ]]
    scribe = Group.objects.create(name="scribe")
    scribe.permissions = scribe_perms
    scribe.save()

    editor_perms = [resolver.resolve(x) for x in [
        ["add_changerecord", "lexicography", "changerecord"],
        ["add_chunk", "lexicography", "chunk"],
        ["add_entry", "lexicography", "entry"],
        ["change_entry", "lexicography", "entry"],
        ["delete_entry", "lexicography", "entry"],
        ["add_entrylock", "lexicography", "entrylock"],
        ["change_entrylock", "lexicography", "entrylock"],
        ["delete_entrylock", "lexicography", "entrylock"],
    ]]
    editor = Group.objects.create(name="editor")
    editor.permissions = editor_perms
    editor.save()

class Migration(migrations.Migration):

    dependencies = [
        ('lexicography', '0001_initial'),
        ('auth', '0001_initial'),
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(permissions),
    ]
