from django.contrib import admin
from django.contrib.admin import sites

class FullAdminSite(admin.AdminSite):

    def has_permission(self, request):
        return request.user.is_superuser

mysite = FullAdminSite("full-admin")
admin.site = mysite
sites.site = mysite


default_app_config = "core.apps.DefaultAppConfig"
