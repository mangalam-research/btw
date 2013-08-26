from django.contrib import admin
import django.contrib.auth.admin
from django.contrib.auth import get_user_model

from bibsearch.models import ZoteroUser

class ZoteroUserInline(admin.StackedInline):
    model = ZoteroUser
    can_delete = False
    verbose_name_plural = 'zotero users'
    max_num = 1

class UserAdmin(django.contrib.auth.admin.UserAdmin):
    inlines = django.contrib.auth.admin.UserAdmin.inlines + [ZoteroUserInline]

# Re-register UserAdmin
admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), UserAdmin)
