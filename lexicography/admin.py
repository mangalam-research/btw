from django.contrib import admin
from lexicography.models import Entry, Chunk, ChangeRecord

admin.site.register(Entry)
admin.site.register(Chunk)
admin.site.register(ChangeRecord)
