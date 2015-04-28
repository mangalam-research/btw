# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

class PermissionResolver(object):

    def __init__(self, Permission, ContentType):
        self.Permission = Permission
        self.ContentType = ContentType
        self.ct_cache = {}
        self.p_cache = {}

    def resolve(self, p):
        perm, app, model = p
        p_key = tuple(p)
        p = self.p_cache.get(p_key)
        if p is not None:
            return p

        ct = self.resolve_ct(app, model)
        p = self.Permission.objects.get(codename=perm, content_type=ct)
        self.p_cache[p_key] = p
        return p

    def resolve_ct(self, app, model):
        ct_key = (app, model)
        ct = self.ct_cache.get(ct_key)
        if ct is not None:
            return ct

        ct = self.ContentType.objects.get(app_label=app, model=model)
        self.ct_cache[ct_key] = ct
        return ct

def permissions(apps, schema_editor):
    from django.contrib.contenttypes.management import update_all_contenttypes
    update_all_contenttypes(interactive=True, verbosity=0)

    from django.contrib.auth.management import create_permissions
    from django.apps import apps
    for app in apps.get_app_configs():
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
