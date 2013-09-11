from django.utils.html import escape, mark_safe
from django.core import urlresolvers
from django.contrib import admin
from .models import Entry, Chunk, ChangeRecord, UserAuthority, \
    OtherAuthority, Authority, EntryLock

from btw import settings


def make_link_method(field_name, display_name=None):
    if display_name is None:
        display_name = field_name

    def method(self, obj):
        field = getattr(obj, field_name)
        # pylint: disable-msg=W0212
        model_name = field._meta.module_name
        return mark_safe(u'<a href="%s">%s</a>' %
                         (urlresolvers.reverse("admin:lexicography_" +
                                               model_name + "_change",
                                               args=(field, )),
                          escape(str(field))))
    method.allow_tags = True
    method.short_description = display_name
    return method


class EntryAdmin(admin.ModelAdmin):
    list_display = ('headword', 'user', 'datetime', 'session', 'ctype',
                    'csubtype', 'raw_edit', 'chunk_link')

    chunk_link = make_link_method('c_hash', "Chunk")

    def raw_edit(self, obj):
        return mark_safe('<a href="%s">Edit raw XML</a>' %
                         (urlresolvers.reverse('lexicography_entry_rawupdate',
                                               args=(obj.id, ))))


class ChangeRecordAdmin(admin.ModelAdmin):
    class Media(object):
        js = (settings.BTW_REQUIREJS_PATH,
              settings.BTW_REQUIREJS_CONFIG_PATH,
              '/'.join([settings.STATIC_URL, 'js/lexicography/admin.js']))

    list_display = ('entry', 'headword', 'user', 'datetime', 'session',
                    'ctype', 'csubtype', 'revert', 'chunk_link')

    chunk_link = make_link_method('c_hash', "Chunk")

    def revert(self, obj):
        return mark_safe(('<a class="lexicography-revert" href="%s">'
                          'Revert entry to this version</a>') %
                         (urlresolvers.reverse('lexicography_change_revert',
                                               args=(obj.id, ))))


class EntryLockAdmin(admin.ModelAdmin):
    list_display = ('entry', 'owner', 'datetime')

admin.site.register(Entry, EntryAdmin)
admin.site.register(Chunk)
admin.site.register(ChangeRecord, ChangeRecordAdmin)
admin.site.register(UserAuthority)
admin.site.register(OtherAuthority)
admin.site.register(Authority)
admin.site.register(EntryLock, EntryLockAdmin)
