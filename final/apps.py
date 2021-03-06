from django.apps import AppConfig, apps as django_apps

from lib import env

class DefaultAppConfig(AppConfig):
    name = 'final'

    def ready(self):
        from lib.admin import limited_admin_site as site
        # If we are run from the command line, there is no point in
        # performing any work here. It would actually be harmful to
        # run this code as it would trigger an invalidation of Django
        # CMS' cache and cause an access to Redis, but Redis may not
        # be started.
        #
        # When we are testing though, we do need this app.
        #
        if env.from_command_line and not env.testing:
            return

        #
        # This list needs to replicate what Django CMS does by default.
        # Search the instances of site.register with:
        #
        # ``grep site.register cms/admin/*``
        #

        from cms.admin.permissionadmin import GlobalPagePermissionAdmin
        site.register(django_apps.get_model("cms", "GlobalPagePermission"),
                      GlobalPagePermissionAdmin)

        from cms.admin.useradmin import PageUserAdmin, PageUserGroupAdmin
        site.register(django_apps.get_model("cms", "PageUser"),
                      PageUserAdmin)
        site.register(django_apps.get_model("cms", "PageUserGroup"),
                      PageUserGroupAdmin)

        from cms.admin.pageadmin import PageAdmin
        site.register(django_apps.get_model("cms", "Page"),
                      PageAdmin)

        from cms.admin.pageadmin import PageTypeAdmin
        site.register(django_apps.get_model("cms", "PageType"),
                      PageTypeAdmin)

        from cms.admin.settingsadmin import SettingsAdmin
        site.register(django_apps.get_model("cms", "UserSettings"),
                      SettingsAdmin)

        from cms.admin.static_placeholder import StaticPlaceholderAdmin
        site.register(django_apps.get_model("cms", "StaticPlaceholder"),
                      StaticPlaceholderAdmin)

        # This is required so that the CMS toolbar does not crash when
        # a superuser (or anyone who can edit users) is logged
        # in. This won't **actually** give users the capability to
        # edit User models.
        from django.contrib.auth.admin import UserAdmin
        from django.contrib.auth import get_user_model
        site.register(get_user_model(), UserAdmin)
