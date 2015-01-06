# django imports
from django.contrib import admin

# module imports
from .models import ZoteroUser, PrimarySource, Item

# register the zotero profile to admin,
# there is no other way to enter local zotero profile details.
# this is as per the current project scope.
admin.site.register(ZoteroUser)

admin.site.register(PrimarySource)

admin.site.register(Item)
