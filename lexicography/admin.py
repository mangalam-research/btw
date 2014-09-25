from django.conf import settings
from django.utils.html import escape, mark_safe
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.admin.templatetags.admin_modify import register, submit_row
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text
from django.http import HttpResponseRedirect
from django import forms

from .locking import release_entry_lock, entry_lock_required
from .forms import RawSaveForm
from .models import Entry, Chunk, ChangeRecord, UserAuthority, \
    OtherAuthority, Authority, EntryLock, Handle
from .xml import XMLTree
from .views import try_updating_entry


def make_link_method(field_name, display_name=None):
    if display_name is None:
        display_name = field_name

    def method(self, obj):
        field = getattr(obj, field_name)
        # pylint: disable-msg=W0212
        model_name = field._meta.model_name
        return mark_safe(u'<a href="%s">%s</a>' %
                         (reverse("admin:lexicography_" +
                                  model_name + "_change",
                                  args=(field, )),
                          escape(str(field))))
    method.allow_tags = True
    method.short_description = display_name
    return method


class ChangeRecordMixin(object):

    def revert(self, obj):
        if obj.id is None:
            return ""

        return mark_safe(('<a class="lexicography-revert" href="%s">'
                          'Revert entry to this version</a>') %
                         (reverse('lexicography_change_revert',
                                  args=(obj.id, ))))


class ChangeRecordInline(admin.TabularInline, ChangeRecordMixin):

    class Media(object):
        js = (settings.BTW_REQUIREJS_PATH,
              settings.BTW_REQUIREJS_CONFIG_PATH,
              '/'.join([settings.STATIC_URL, 'js/lexicography/admin.js']))

        css = {
            'all': (settings.BTW_JQUERY_GROWL_CSS_PATH, )
        }

    model = ChangeRecord
    fields = ('headword', 'user', 'datetime', 'session', 'ctype', 'csubtype',
              'c_hash', 'revert')
    readonly_fields = ('revert', )
    ordering = ('-datetime', )

    def has_add_permission(self, _request):
        return False


class EntryAdmin(admin.ModelAdmin):
    list_display = ('headword', 'user', 'datetime', 'session', 'ctype',
                    'csubtype', 'edit_raw', 'view', 'chunk_link')

    chunk_link = make_link_method('c_hash', "Chunk")

    inlines = (ChangeRecordInline, )

    def edit_raw(self, obj):
        return mark_safe('<a href="%s">Edit raw XML</a>' %
                         (reverse('admin:lexicography_entry_rawupdate',
                                  args=(obj.id, ))))

    def view(self, obj):
        return mark_safe('<a href="%s">View</a>' %
                         (reverse('lexicography_entry_details',
                                  args=(obj.id, ))))

    def get_urls(self):
        return [
            url(r'^add_raw/$', self.raw_new,
                name='lexicography_entry_rawnew'),
            url(r'^(?P<entry_id>\d+)/raw_update$', self.raw_update,
                name="lexicography_entry_rawupdate")
        ] + \
            super(EntryAdmin, self).get_urls()

    @method_decorator(login_required)
    @method_decorator(require_http_methods(["GET", "POST"]))
    def raw_new(self, request):
        if request.method == 'POST':
            form = RawSaveForm(request.POST)
            if form.is_valid():
                chunk = form.save(commit=False)

                xmltree = XMLTree(chunk.data)

                entry = Entry()
                try_updating_entry(request, entry, chunk, xmltree,
                                   Entry.CREATE, Entry.MANUAL)
                release_entry_lock(entry, request.user)
                return HttpResponseRedirect(
                    reverse('admin:lexicography_entry_changelist'))
        else:
            form = RawSaveForm()

            opts = self.model._meta
            return self.render_raw_form(
                request, form,
                _('Add %s') % force_text(opts.verbose_name))

    @method_decorator(login_required)
    @method_decorator(require_http_methods(["GET", "POST"]))
    @method_decorator(entry_lock_required)
    def raw_update(self, request, entry_id):
        entry = Entry.objects.get(id=entry_id)
        if request.method == 'POST':
            form = RawSaveForm(request.POST)
            if form.is_valid():
                chunk = form.save(commit=False)

                xmltree = XMLTree(chunk.data.encode("utf-8"))
                try_updating_entry(
                    request, entry, chunk, xmltree, Entry.UPDATE,
                    Entry.MANUAL)
                release_entry_lock(entry, request.user)
                return HttpResponseRedirect(
                    reverse('admin:lexicography_entry_changelist'))

        else:
            form = RawSaveForm(instance=entry.c_hash)

            opts = self.model._meta
            return self.render_raw_form(
                request, form, _('Change %s') % force_text(opts.verbose_name),
                entry)

    def render_raw_form(self, request, form, title, entry=None):
        opts = self.model._meta
        return render(request, 'admin/lexicography/entry/raw.html', {
            'title': title,
            'form': form,
            'opts': opts,
            'app_label': opts.app_label,
            'change': True,
            'is_popup': False,
            'save_as': False,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission':
            self.has_change_permission(request, entry) if entry else False,
            'has_delete_permission':
            self.has_delete_permission(request, entry) if entry else False,
            'add': False,
            'show_save_and_add_another': False,
            'show_save_and_continue': False,
            'show_delete': False
        })


#
# What this rigmarole does is allow us to turn off the two save
# buttons by setting a context when using ``render``. Without this,
# the context given to ``render`` has no effect at all.
#

@register.inclusion_tag('admin/submit_line.html', takes_context=True)
def my_submit_row(context):
    ctx = submit_row(context)  # Get a new context from the original.

    # Override on the basis of what the passed context contains...
    for name in ('show_save_and_add_another', 'show_save_and_continue'):
        ctx[name] = context.get(name, ctx[name])

    return ctx


class ChangeRecordAdmin(admin.ModelAdmin, ChangeRecordMixin):

    class Media(object):
        js = (settings.BTW_REQUIREJS_PATH,
              settings.BTW_REQUIREJS_CONFIG_PATH,
              '/'.join([settings.STATIC_URL, 'js/lexicography/admin.js']))

    list_display = ('entry', 'headword', 'user', 'datetime', 'session',
                    'ctype', 'csubtype', 'revert', 'chunk_link')

    list_filter = ('entry', 'headword', 'user', 'session', 'ctype', 'csubtype')

    chunk_link = make_link_method('c_hash', "Chunk")


class EntryLockAdmin(admin.ModelAdmin):
    list_display = ('entry', 'owner', 'expirable', 'datetime')
    list_filter = ('owner', )


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
