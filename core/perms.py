from lib.util import PermissionResolver

def create_perms(apps=None):
    from django.conf import settings

    if apps is None:
        from django.contrib.auth.models import Permission, ContentType
        from django.contrib.auth import get_user_model
        from cms.models.permissionmodels import PageUserGroup, \
            GlobalPagePermission

        User = get_user_model()
    else:
        user_model_name = settings.AUTH_USER_MODEL
        user_app, user_model = user_model_name.rsplit(".", 1)
        User = apps.get_model(user_app, user_model)

        Permission = apps.get_model("auth", "Permission")
        ContentType = apps.get_model("contenttypes", "ContentType")
        PageUserGroup = apps.get_model("cms", "PageUserGroup")
        GlobalPagePermission = apps.get_model("cms", "GlobalPagePermission")

    username = "cms-migration-user"

    try:
        fake = User.objects.get(username=username)
    except User.DoesNotExist:
        fake = User.objects.create()
        fake.username = username
        fake.is_active = False
        fake.save()

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
