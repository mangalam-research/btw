from django.contrib import admin
from django.contrib.auth.models import User
import django.contrib.auth.admin

from models import ZoteroUser

class ZoteroUserInline(admin.StackedInline):
    model = ZoteroUser
    can_delete = False
    verbose_name_plural = 'zotero users'
    max_num = 1

class UserAdmin(django.contrib.auth.admin.UserAdmin):
    inlines = django.contrib.auth.admin.UserAdmin.inlines + [ZoteroUserInline]

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
