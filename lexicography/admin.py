from django.conf import settings
from django.utils.html import escape, mark_safe
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods, require_POST
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.contrib.admin.templatetags.admin_modify import register, submit_row
from django.utils.translation import ugettext as _
from django.utils.encoding import force_text
from django.http import HttpResponseRedirect, HttpResponse
from django.core.exceptions import PermissionDenied


from .locking import release_entry_lock, entry_lock_required
from .forms import RawSaveForm
from .models import Entry, Chunk, ChangeRecord, EntryLock, Handle, \
    PublicationChange, DeletionChange
from .xml import XMLTree, can_revert_to
from . import usermod

def make_link(url, text):
    return mark_safe(u'<a href="{0}">{1}</a>'.format(url, escape(text)))

def make_link_method(field_name, display_name=None):
    if display_name is None:
        display_name = field_name

    def method(self, obj):
        field = getattr(obj, field_name)
        # pylint: disable-msg=W0212
        model_name = field._meta.model_name
        return make_link(reverse("full-admin:lexicography_" +
                                 model_name + "_change", args=(field, )),
                         escape(str(field)))
    method.allow_tags = True
    method.short_description = display_name
    return method


class ChangeRecordMixin(object):

    def revert(self, obj):
        if obj.id is None:
            return ""

        if not can_revert_to(obj.c_hash.schema_version):
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
    fields = ('lemma', 'user', 'datetime', 'session', 'ctype',
              'csubtype', 'c_hash', 'revert')
    readonly_fields = fields
    ordering = ('-datetime', )

    def has_add_permission(self, _request):
        return False

    def has_delete_permission(self, _request, _obj=None):
        return False


def changerecord_to_str(cr):
    return make_link(reverse('full-admin:lexicography_changerecord_change',
                             args=(cr.id, )),
                     cr.user.username + " " + str(cr.datetime)) \
        if cr is not None else None


class EntryAdmin(admin.ModelAdmin):
    list_display = ('lemma', 'view', 'nice_deleted', 'nice_latest',
                    'nice_latest_published', 'edit_raw')
    readonly_fields = ('delete_undelete', )
    exclude = ('deleted', )

    inlines = (ChangeRecordInline, )

    def nice_deleted(self, obj):
        return "Yes" if obj.deleted else "No"
    nice_deleted.short_description = "Deleted"

    def nice_latest(self, obj):
        return changerecord_to_str(obj.latest)
    nice_latest.short_description = "Latest"

    def nice_latest_published(self, obj):
        return changerecord_to_str(obj.latest_published)
    nice_latest_published.short_description = "Latest published"

    def edit_raw(self, obj):
        return make_link(reverse('full-admin:lexicography_entry_rawupdate',
                                 args=(obj.id, )), "Edit raw XML")

    def view(self, obj):
        return make_link(reverse('lexicography_entry_details',
                                 args=(obj.id, )), "View")

    def delete_undelete(self, obj):
        return mark_safe(
            '<a class="{2}" href="{0}">{1}</a>'
            .format(reverse('full-admin:lexicography_entry_undelete'
                            if obj.deleted
                            else 'full-admin:lexicography_entry_mark_deleted',
                            args=(obj.id, )),
                    "Undelete" if obj.deleted else "Delete",
                    "lexicography-undelete" if obj.deleted
                    else "lexicography-delete"))
    delete_undelete.allow_tags = True
    delete_undelete.short_description = ""

    def get_urls(self):
        return [
            url(r'^add_raw/$', self.raw_new,
                name='lexicography_entry_rawnew'),
            url(r'^(?P<entry_id>\d+)/raw_update$', self.raw_update,
                name="lexicography_entry_rawupdate"),
            url(r'^(?P<entry_id>\d+)/mark_deleted$', self.mark_deleted,
                name="lexicography_entry_mark_deleted"),
            url(r'^(?P<entry_id>\d+)/undelete$', self.undelete,
                name="lexicography_entry_undelete"),
        ] + \
            super(EntryAdmin, self).get_urls()

    @method_decorator(login_required)
    @method_decorator(require_http_methods(["GET", "POST"]))
    def raw_new(self, request):
        if not usermod.can_author(request.user):
            raise PermissionDenied

        if request.method == 'POST':
            form = RawSaveForm(request.POST)
            if form.is_valid():
                chunk = form.save(commit=False)
                xmltree = form._xmltree
                lemma = xmltree.extract_lemma()

                if Entry.objects.filter(lemma=lemma).count() > 0:
                    # From Django 1.7 onwards this should use:
                    # form.add_error('data', ...)
                    errors = form.errors.setdefault(
                        'data', form.error_class())
                    errors.append(
                        'Lemma already present in database: ' + lemma)
                else:
                    entry = Entry()
                    entry.try_updating(request, chunk, xmltree,
                                       ChangeRecord.CREATE,
                                       ChangeRecord.MANUAL)
                    release_entry_lock(entry, request.user)
                    return HttpResponseRedirect(
                        reverse('full-admin:lexicography_entry_changelist',
                                current_app=self.admin_site.name))
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
        if not usermod.can_author(request.user):
            raise PermissionDenied

        entry = Entry.objects.get(id=entry_id)
        if request.method == 'POST':
            form = RawSaveForm(request.POST)
            if form.is_valid():
                chunk = form.save(commit=False)

                xmltree = XMLTree(chunk.data.encode("utf-8"))
                entry.try_updating(
                    request, chunk, xmltree, ChangeRecord.UPDATE,
                    ChangeRecord.MANUAL)
                release_entry_lock(entry, request.user)
                return HttpResponseRedirect(
                    reverse('full-admin:lexicography_entry_changelist',
                            current_app=self.admin_site.name))

        else:
            form = RawSaveForm(instance=entry.latest.c_hash)

        opts = self.model._meta
        return self.render_raw_form(
            request, form, _('Change %s') % force_text(opts.verbose_name),
            entry)

    @method_decorator(login_required)
    @method_decorator(require_POST)
    @method_decorator(entry_lock_required)
    def mark_deleted(self, request, entry_id):
        if not usermod.can_author(request.user):
            raise PermissionDenied
        Entry.objects.get(id=entry_id).mark_deleted(request.user)
        return HttpResponse("Deleted.")

    @method_decorator(login_required)
    @method_decorator(require_POST)
    @method_decorator(entry_lock_required)
    def undelete(self, request, entry_id):
        if not usermod.can_author(request.user):
            raise PermissionDenied
        Entry.objects.get(id=entry_id).undelete(request.user)
        return HttpResponse("Undeleted.")

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
        }, current_app=self.admin_site.name)


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

    list_display = ('entry', 'lemma', 'user', 'datetime', 'session',
                    'ctype', 'csubtype', 'published', 'revert', 'chunk_link')

    list_filter = ('entry', 'lemma', 'published',
                   'user', 'session', 'ctype', 'csubtype')

    chunk_link = make_link_method('c_hash', "Chunk")


class ChunkAdmin(admin.ModelAdmin):
    list_display = ('c_hash', 'is_normal', 'schema_version', '_valid')
    list_filter = ('is_normal', 'schema_version', '_valid')


class EntryLockAdmin(admin.ModelAdmin):
    list_display = ('entry', 'owner', 'expirable', 'datetime')
    list_filter = ('owner', )


class HandleAdmin(admin.ModelAdmin):
    list_display = ('handle', 'entry', 'session')

admin.site.register(Entry, EntryAdmin)
admin.site.register(Chunk, ChunkAdmin)
admin.site.register(ChangeRecord, ChangeRecordAdmin)
admin.site.register(PublicationChange)
admin.site.register(DeletionChange)
admin.site.register(EntryLock, EntryLockAdmin)
admin.site.register(Handle, HandleAdmin)
