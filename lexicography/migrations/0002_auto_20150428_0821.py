# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
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
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    if Group.objects.filter(name__in=("author", "editor")).exists():
        print "You already have an author or editor group in your database."
        print ("Assuming that we are upgrading from a pre-Django 1.7 "
               "installation, and aborting.")
        print
        print ("If the assumption is incorrect, please edit your database "
               "manually.")
        return

    resolver = PermissionResolver(Permission, ContentType)

    author_perms = [resolver.resolve(x) for x in [
        ["add_authority", "lexicography", "authority"],
        ["add_changerecord", "lexicography", "changerecord"],
        ["add_chunk", "lexicography", "chunk"],
        ["add_entry", "lexicography", "entry"],
        ["change_entry", "lexicography", "entry"],
        ["add_entrylock", "lexicography", "entrylock"],
        ["change_entrylock", "lexicography", "entrylock"],
        ["delete_entrylock", "lexicography", "entrylock"],
        ["add_otherauthority", "lexicography", "otherauthority"],
        ["add_userauthority", "lexicography", "userauthority"]
    ]]
    author = Group.objects.create(name="author")
    author.permissions = author_perms
    author.save()

    editor_perms = [resolver.resolve(x) for x in [
        ["add_authority", "lexicography", "authority"],
        ["add_changerecord", "lexicography", "changerecord"],
        ["add_chunk", "lexicography", "chunk"],
        ["add_entry", "lexicography", "entry"],
        ["change_entry", "lexicography", "entry"],
        ["delete_entry", "lexicography", "entry"],
        ["add_entrylock", "lexicography", "entrylock"],
        ["change_entrylock", "lexicography", "entrylock"],
        ["delete_entrylock", "lexicography", "entrylock"],
        ["add_otherauthority", "lexicography", "otherauthority"],
        ["add_userauthority", "lexicography", "userauthority"]
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
