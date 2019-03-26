from lib.util import PermissionResolver

def create_perms(apps=None):
    """
    Create the users and groups needed by the lexicography
    app. ``apps`` must be passed if called from a
    migration. Otherwise, it should be ``None``.
    """

    if apps is None:
        from django.contrib.auth.models import Group, Permission, ContentType
    else:
        Group = apps.get_model("auth", "Group")
        Permission = apps.get_model("auth", "Permission")
        ContentType = apps.get_model("contenttypes", "ContentType")

    # Rename the author group if it exists.
    try:
        author_group = Group.objects.get(name="author")
    except Group.DoesNotExist:
        author_group = None

    if author_group:
        author_group.name = "scribe"
        author_group.save()

    if Group.objects.filter(name__in=("scribe", "editor")).exists():
        print("You already have an scribe or editor groups in your database.")
        print("Assuming that we are upgrading from a pre-Django 1.7 "
              "installation, and stopping.")
        print()
        print("If the assumption is incorrect, please edit your database "
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
    scribe.permissions.set(scribe_perms)
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
    editor.permissions.set(editor_perms)
    editor.save()
