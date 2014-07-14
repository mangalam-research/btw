from django.conf import settings
from django.utils.html import escape, mark_safe
from django.core import urlresolvers
from django.contrib import admin
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.utils.decorators import method_decorator

from .locking import release_entry_lock, entry_lock_required
from .forms import RawSaveForm
from .models import Entry, Chunk, ChangeRecord, UserAuthority, \
    OtherAuthority, Authority, EntryLock, Handle
from .xml import storage_to_editable, XMLTree
from .views import try_updating_entry


def make_link_method(field_name, display_name=None):
    if display_name is None:
        display_name = field_name

    def method(self, obj):
        field = getattr(obj, field_name)
        # pylint: disable-msg=W0212
        model_name = field._meta.model_name
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

    def get_urls(self):
        return [
            url(r'^add_raw/$', self.entry_raw_new,
                name='admin_lexicography_entry_rawnew'),
        ] + \
            super(EntryAdmin, self).get_urls()

    @method_decorator(login_required)
    @method_decorator(require_http_methods(["GET", "POST"]))
    def entry_raw_new(self, request):
        if request.method == 'POST':
            form = RawSaveForm(request.POST)
            if form.is_valid():
                chunk = form.save(commit=False)

                # If it was not already entered in the editable format, then we
                # need to convert it.
                if not form.cleaned_data['editable_format']:
                    chunk.data = storage_to_editable(chunk.data)
                xmltree = XMLTree(chunk.data)

                entry = Entry()
                try_updating_entry(request, entry, chunk, xmltree,
                                   Entry.CREATE, Entry.MANUAL)
                release_entry_lock(entry, request.user)
        else:
            form = RawSaveForm()

        ret = render(request, 'lexicography/raw.html', {
            'page_title': settings.BTW_SITE_NAME + " | Lexicography | New ",
            'form': form,
        })
        return ret


class ChangeRecordAdmin(admin.ModelAdmin):

    class Media(object):
        js = (settings.BTW_REQUIREJS_PATH,
              settings.BTW_REQUIREJS_CONFIG_PATH,
              '/'.join([settings.STATIC_URL, 'js/lexicography/admin.js']))

    list_display = ('entry', 'headword', 'user', 'datetime', 'session',
                    'ctype', 'csubtype', 'revert', 'chunk_link')

    list_filter = ('entry', 'headword', 'user', 'session', 'ctype', 'csubtype')

    chunk_link = make_link_method('c_hash', "Chunk")

    def revert(self, obj):
        return mark_safe(('<a class="lexicography-revert" href="%s">'
                          'Revert entry to this version</a>') %
                         (urlresolvers.reverse('lexicography_change_revert',
                                               args=(obj.id, ))))


class EntryLockAdmin(admin.ModelAdmin):
    list_display = ('entry', 'owner', 'datetime')


class HandleAdmin(admin.ModelAdmin):
    list_display = ('handle', 'entry', 'session')

admin.site.register(Entry, EntryAdmin)
admin.site.register(Chunk)
admin.site.register(ChangeRecord, ChangeRecordAdmin)
admin.site.register(UserAuthority)
admin.site.register(OtherAuthority)
admin.site.register(Authority)
admin.site.register(EntryLock, EntryLockAdmin)
admin.site.register(Handle, HandleAdmin)
