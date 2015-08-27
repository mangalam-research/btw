from lib import env
if env.testing:
    #
    # We modify the connections so that the code cannot access the
    # database before the databases have been set by the test runner.
    #
    # The problem is that it is hard to track which Django operations
    # will result in a database access. For instance, most ``reverse``
    # calls won't result in a database access but some do, if they
    # involve the sites framework, for instance.
    #
    # We patch the code so that any connection that happens before our
    # runner gets a chance to update the databases fails.
    #
    # This requires the use of core.runner.Runner so that the patch is
    # undone when the tests start.
    #

    def fail(*args, **kwargs):
        raise Exception("database access during testing before the "
                        "databases have been set by the test runner")

    from django.db import connections
    for name in connections:
        conn = connections[name]
        if getattr(conn, "_old_connect", None) is not None:
            raise Exception("Django already defines an _old_connect field"
                            "on connections; can't patch them")
        setattr(conn, "_old_connect", conn.connect)
        conn.connect = fail

from django.contrib import admin
from django.contrib.admin import sites

class FullAdminSite(admin.AdminSite):

    def has_permission(self, request):
        return request.user.is_superuser

mysite = FullAdminSite("full-admin")
admin.site = mysite
sites.site = mysite


default_app_config = "core.apps.DefaultAppConfig"
