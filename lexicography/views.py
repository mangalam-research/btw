# -*- coding: utf-8 -*-
"""Views for the lexicography app.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
from functools import wraps
import os
import datetime
import json
import urllib
import logging

import semver
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect, render_to_response
from django.http import HttpResponse, HttpResponseNotFound, \
    HttpResponseRedirect, HttpResponseBadRequest, Http404, QueryDict
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST, require_GET, \
    require_http_methods, etag
from django.middleware.csrf import get_token
from django.template import RequestContext
from django.db import IntegrityError
from django.db.models import ProtectedError, F
from django.conf import settings
from django.db import transaction
from django.utils.http import quote_etag
from django.utils.html import mark_safe
from django.contrib.auth import get_user_model
from django.views.decorators.cache import never_cache
from django.core.cache import caches
from django_datatables_view.base_datatable_view import BaseDatatableView
from django_datatables_view.mixins import LazyEncoder
from eulexistdb.db import ExistDB
import lxml.etree

import lib.util as util
from . import handles, usermod, article, models
from .models import Entry, ChangeRecord, Chunk, EntryLock
from .locking import release_entry_lock, drop_entry_lock, \
    entry_lock_required
from .xml import XMLTree, xhtml_to_xml, clean_xml, \
    get_supported_schema_versions, default_namespace_mapping
from .forms import SaveForm
from lib.existdb import query_iterator, is_lucene_query_clean, \
    get_collection_path
from lib import xquery

article_display_cache = caches['article_display']

logger = logging.getLogger("lexicography")

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")

JSON_TYPE = "application/json; charset=utf-8"

@require_GET
def main(request):
    return render(request, 'lexicography/main.html',
                  {'page_title': "Lexicography",
                   'can_author': usermod.can_author(request.user)})


class SearchTable(BaseDatatableView):
    model = ChangeRecord
    # django-datatables-view takes a dot-notation to refer to fields
    # in related models rather than Django's native ``__`` system.
    columns = ['lemma', 'c_hash.schema_version', 'published', 'entry.deleted',
               'datetime', 'user', 'hit']
    order_columns = ['lemma', 'c_hash.schema_version', 'published',
                     'entry.deleted', 'datetime', 'user', '']

    def get(self, *args, **kwargs):
        self.chunk_to_hits = {}
        search_value = self.request.GET.get('search[value]', None)

        if search_value is not None:
            search_value = search_value.encode("utf-8")

        if search_value is not None and len(search_value):
            # Provide an early failure if the Lucene query is not
            # syntactically correct.
            db = ExistDB()
            if not is_lucene_query_clean(db, search_value):
                if self.pre_camel_case_notation:
                    ret = {'sEcho': int(self._querydict.get('sEcho', 0)),
                           'badLucene': True}
                else:
                    ret = {'draw': int(self._querydict.get('draw', 0)),
                           'badLucene': True}
                    ret["result"] = "ok"
                return self.render_to_response(
                    json.dumps(ret, cls=LazyEncoder))

        return super(SearchTable, self).get(*args, **kwargs)

    # pylint: disable=too-many-return-statements
    def render_column(self, row, column):
        if column == "published":
            if row.published:
                if not usermod.can_author(self.request.user):
                    return "Yes"

                return "Yes " + mark_safe(
                    ('<a class="btw-unpublish-btn btn btn-xs btn-default" '
                     'href="%s">Unpublish</a> ') %
                    reverse("lexicography_changerecord_unpublish",
                            args=(row.id, )))

            if not usermod.can_author(self.request.user):
                return "No"

            return "No " + mark_safe(
                ('<a class="btw-publish-btn btn btn-xs btn-default" '
                 'href="%s">Publish</a> ') %
                reverse("lexicography_changerecord_publish",
                        args=(row.id, )))

        if column == "datetime":
            return row.datetime

        if column == "user":
            return row.user.username

        if column == "entry.deleted":
            return "Yes" if row.entry.deleted else "No"

        if column == "c_hash.schema_version":
            warn = ""
            # We do not want to generate the warning for change
            # records that we cannot edit. The only thing we can edit
            # is the latest version of an entry.
            if row.entry.latest == row \
               and row.schema_version != \
                    get_supported_schema_versions().keys()[-1]:
                warn = (
                    ' <span class="label label-warning" title='
                    '"Editing this entry will automatically upgrade the '
                    'schema version and may require additional editing to '
                    'satisfy the new schema.">!</span>'
                )
            return row.schema_version + warn

        if column == "hit":
            hit = self.chunk_to_hits.get(row.c_hash.c_hash, None)

            if hit is not None and len(hit):
                return lxml.etree.tostring(hit,
                                           xml_declaration=True,
                                           encoding='utf-8').decode("utf-8")
            return ""

        ret = super(SearchTable, self).render_column(row, column)
        #
        # We check the permission because for people who cannot edit
        # entries, we do not want to show anything. (They are not
        # affected by locking.)
        #
        # Also we don't put edit buttons for change records that are
        # not the latest.
        #
        if column == 'lemma' and \
           self.request.user.has_perm("lexicography.change_entry") and \
           row.entry.latest == row:
            if row.entry.is_editable_by(self.request.user):
                ret = mark_safe(
                    ('<a class="btn btn-xs btn-default" href="%s">Edit</a> ') %
                    reverse("lexicography_entry_update",
                            args=(row.entry.id, ))) + \
                    ret
            elif row.entry.is_locked():
                ret = mark_safe('Locked by ' +
                                util.nice_name(row.entry.is_locked()) + '. ') \
                    + ret

        return ret

    def get_initial_queryset(self):
        # Random users search only what is published and cannot
        # search history. If we set their initial queryset to all
        # ChangeRecord then they'll see a count ("filtered down
        # from...)" which does not make sense from their point of
        # view. So for them, the initial queryset must be restricted
        # rather than let filtering do the job.

        qs = ChangeRecord.objects.select_related()
        if not usermod.can_author(self.request.user):
            qs = qs.filter(entry__in=Entry.objects.active_entries()) \
                   .filter(entry__latest_published=F('pk'))

        return qs

    def filter_queryset(self, qs):  # pylint: disable=too-many-branches
        search_value = self.request.GET.get('search[value]', None)

        if search_value is not None:
            search_value = search_value.encode("utf-8")

        lemmata_only = self.request.GET.get('lemmata_only', "false") == \
            "true"

        if usermod.can_author(self.request.user):
            publication_status = self.request.GET.get('publication_status',
                                                      "published")
            search_all = self.request.GET.get('search_all', "false") == "true"
            if not search_all:
                # Remove deleted entries from the set.
                active = qs.filter(entry__in=Entry.objects.active_entries())
                if publication_status == "published":
                    active = active.filter(entry__latest_published=F('pk'))
                elif publication_status == "unpublished":
                    active = active.filter(entry__latest=F('pk')) \
                                   .exclude(entry__latest_published=F('pk'))
                elif publication_status == "both":
                    active = active.filter(entry__latest=F('pk'))
                else:
                    raise ValueError("unknown value for publication_status: " +
                                     publication_status)
            else:
                if publication_status == "published":
                    active = qs.filter(published=True)
                elif publication_status == "unpublished":
                    active = qs.filter(published=False)
                elif publication_status == "both":
                    active = qs
                else:
                    raise ValueError("unknown value for publication_status: " +
                                     publication_status)
        else:
            # If the user cannot author, then our queryset is already
            # reduced to what the user can see: the latest version of
            # published articles.
            active = qs

        if search_value:
            db = ExistDB()
            chunks = []
            if lemmata_only:
                scope = "//btw:lemma"
                # When we do a lemma search, hits are not useful.
                hit = ""
            else:
                scope = "//btw:entry"
                hit = "{kwic:summarize($m, <config width='80'/>)}"

            for query_chunk in query_iterator(db, xquery.format(
                    """\
import module namespace kwic="http://exist-db.org/xquery/kwic";
for $m in collection({db}){scope}[ft:query(., {search_text})]
order by ft:score($m) descending
return <result><doc>{doc}</doc><hit>{hit}</hit></result>""",
                    db=get_collection_path("display"),
                    scope=xquery.Verbatim(scope),
                    doc=xquery.Verbatim("{util:document-name($m)}"),
                    hit=xquery.Verbatim(hit),
                    search_text=search_value)):

                for result in query_chunk.results:
                    chunk = result[0].text  # Content of <doc>.
                    self.chunk_to_hits[chunk] = result[1]
                    chunks.append(chunk)

            # We need to get the changerecords that pertain to these chunks.
            qs = active.filter(c_hash__in=set(chunks))
        else:
            qs = active

        return qs


@require_GET
@never_cache
def entry_details(request, entry_id, changerecord_id=None):
    """
    When no ChangeRecord id is provided, showing the Entry will show
    the latest published version of the entry.

    If a ChangeRecord id is provided, we show this ChangeRecord,
    provided that it belongs to the Entry specified.
    """
    entry = Entry.objects.get(id=entry_id)
    can_author = usermod.can_author(request.user)

    if changerecord_id is None:

        # The entry does not have a latest published record...
        if not entry.latest_published:
            return HttpResponseNotFound(
                "You are trying to view the latest published "
                "version of an article that has never been published.")
        return _show_changerecord(request, entry.latest_published)

    # We have a changerecord_id
    try:
        cr = ChangeRecord.objects.get(id=changerecord_id)
    except ChangeRecord.DoesNotExist:
        return HttpResponseNotFound("You are trying to view a version "
                                    "that does not exist.")
    if cr.entry != entry:
        return HttpResponseNotFound("""
<h1>Non-existent Version</h1>
<p>The article exists but you are looking for a version does not exist. \
The version you are seeking may never have existed in the first place. Or \
perhaps the version you are seeking has been removed from the system due \
to a serious issue (legal, ethical, etc.) with its contents.</p>
<p>The latest version of the article accessible to you is \
<a href="{0}">here</a>.</p>
        """.format(mark_safe(entry.get_absolute_url())))

    # Random users cannot view records that have not been published.
    if not can_author and not cr.published:
        raise PermissionDenied

    return _show_changerecord(request, cr)

@require_GET
@never_cache
def mods(request, entry_id, changerecord_id=None):
    access_date = request.GET.get('access-date', None)
    version_specific = request.GET.get('version-specific', None)

    if access_date is None:
        return HttpResponseBadRequest(
            "access-date is a required parameter")

    entry = Entry.objects.get(id=entry_id)
    if changerecord_id is not None:
        cr = ChangeRecord.objects.get(id=changerecord_id)
    else:
        cr = entry.latest_published
        if cr is None:
            return HttpResponseBadRequest("this entry has never been "
                                          "published: you must request a "
                                          "specific change record")

    data = cr.c_hash.data

    xml = XMLTree(data)

    def names_to_objects(names):
        objs = []
        for name in names:
            forename = ''.join(
                name.xpath("./tei:forename",
                           namespaces=default_namespace_mapping)[0].itertext())
            surname = ''.join(
                name.xpath("./tei:surname",
                           namespaces=default_namespace_mapping)[0].itertext())
            # pylint: disable=invalid-name
            genName = ''.join(
                name.xpath("./tei:genName",
                           namespaces=default_namespace_mapping)[0].itertext())
            objs.append({
                'forename': forename,
                'surname': surname,
                'genName': genName
            })
        return objs

    authors = names_to_objects(
        xml.tree.xpath("//btw:credit//tei:persName",
                       namespaces=default_namespace_mapping))

    editors = names_to_objects(
        xml.tree.xpath("//tei:editor/tei:persName",
                       namespaces=default_namespace_mapping))

    url = cr.get_absolute_url() if version_specific \
        else entry.get_absolute_url()

    return render(request,
                  "lexicography/mods.xml",
                  {
                      'title': cr.lemma,
                      'version': util.version(),
                      'year': datetime.date.today().year,
                      'authors': authors,
                      'editors': editors,
                      'url': request.build_absolute_uri(url),
                      'access_date': access_date
                  },
                  content_type="application/xml+mods")

@require_GET
@never_cache
def changerecord_details(request, changerecord_id):
    cr = ChangeRecord.objects.get(pk=changerecord_id)

    if request.is_ajax():
        published = not usermod.can_author(request.user)
        prepared = cr.c_hash.get_display_data()
        if not prepared:
            raise Http404

        prepared["xml"] = \
            article.hyperlink_prepared_data(prepared, published)

        return HttpResponse(json.dumps(prepared),
                            content_type=JSON_TYPE)

    # We no longer access ChangeRecord objects directly.
    return redirect(cr, permanent=True)

@require_POST
def changerecord_publish(request, changerecord_id):
    cr = ChangeRecord.objects.get(id=changerecord_id)

    if not cr.publish(request.user):
        if not cr.can_be_published():
            return HttpResponse("This change record cannot be published.",
                                status=409)
        return HttpResponse("This change record was already published.")

    return HttpResponse("This change record was published.")


@require_POST
def changerecord_unpublish(request, changerecord_id):
    cr = ChangeRecord.objects.get(id=changerecord_id)

    if not cr.unpublish(request.user):
        return HttpResponse("This change record was already unpublished.")

    return HttpResponse("This change record was unpublished.")

def _show_changerecord(request, cr):
    get_token(request)

    can_author = usermod.can_author(request.user)

    show_published = not can_author

    prepared = cr.c_hash.get_display_data()

    if prepared is None:
        data = None
        bibl_data = '{}'
    else:
        data = article.hyperlink_prepared_data(prepared, show_published)
        bibl_data = json.dumps(prepared["bibl_data"])

    # We want an edit option only if this record is the latest and if
    # the user can edit it.
    edit_url = (reverse("lexicography_entry_update", args=(cr.entry.id, ))
                if (cr.entry.latest == cr and
                    cr.entry.is_editable_by(request.user)) else '')
    fetch_url = '' if data is not None else \
                reverse('lexicography_changerecord_details',
                        args=(cr.pk, ))

    # We want to warn the user of any version that has been published
    # and is not this version. We pass cr.entry so that we can get the
    # non-version specific URL of to view the entry.
    latest_published = cr.entry \
        if (cr.entry.latest_published is not None and
            cr != cr.entry.latest_published) else None

    # If the user is able to see unpublished articles, then we want to
    # warn the user if there exist a later version which is
    # unpublished.
    latest_unpublished = cr.entry.latest if can_author and \
        (cr != cr.entry.latest) and \
        (cr.entry.latest != cr.entry.latest_published) else None

    # Provide a history for the article
    history = []
    for version in cr.entry.changerecord_set.filter(published=True) \
            .order_by("-datetime"):
        history.append({
            'url': version.get_absolute_url(),
            'date': version.datetime
        })

    return render_to_response(
        'lexicography/details.html',
        {
            'bibliographical_data': {
                'version': util.version()
            },
            'page_title': cr.lemma,
            'fetch_url': fetch_url,
            'semantic_field_fetch_url':
            reverse("semantic_fields_semanticfield-list"),
            'data': data,
            'bibl_data': bibl_data,
            'edit_url': edit_url,
            'is_published': cr.published,
            'latest_unpublished': latest_unpublished,
            'latest_published': latest_published,
            'permalink': cr.entry.get_absolute_url(),
            'version_permalink': cr.get_absolute_url(),
            'can_author': can_author,
            'history': history
        },
        context_instance=RequestContext(request))


# entry_new and entry_update do not call the handle_update directly
# but send back a redirection response. Why? This is so that from the
# user's point of view the urls that edit articles are consistently
# pointing to the same place.

@never_cache
@login_required
@require_GET
def entry_new(request):
    hm = handles.get_handle_manager(request.session)
    # What we are doing here is indicating to the next view that it is
    # being invoked for a *new* article.
    request.session['BTW_HANDLE_UPDATE_NEW'] = True
    return HttpResponseRedirect(
        reverse('lexicography_handle_update',
                args=("h:" + str(hm.make_unassociated()),)))


@never_cache
@login_required
@require_GET
@entry_lock_required
def entry_update(request, entry_id):
    return HttpResponseRedirect(reverse('lexicography_handle_update',
                                        args=(entry_id,)))


@never_cache
@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def handle_update(request, handle_or_entry_id):
    # We determine through the session whether this is for a new
    # article.
    new_entry = request.session.get('BTW_HANDLE_UPDATE_NEW', False)
    # This is a once only setting.
    try:
        del request.session['BTW_HANDLE_UPDATE_NEW']
    except KeyError:
        pass

    if handle_or_entry_id.startswith("h:"):
        hm = handles.get_handle_manager(request.session)
        handle = handle_or_entry_id[2:]
        entry_id = hm.id(handle)
    else:
        entry_id = handle_or_entry_id

    entry = None
    if entry_id is not None:
        entry = Entry.objects.get(id=entry_id)

    if request.method == 'POST':
        # We don't actually save anything here because saves are done
        # through AJAX. We get here if the user decided to quit editing.
        if entry is not None:
            # The lock could have expired or been removed while we
            # were not doing anything. Or it could even have been
            # acquired by another user: so we **drop** it rather than
            # **release** it.
            drop_entry_lock(entry, request.user)
        return HttpResponseRedirect(reverse("lexicography_main"))

    if entry is not None:
        latest = entry.use_latest_schema_version(request)
        # This means that the entry is locked. This could happen if
        # the entry was unlocked when the user searched for it but was
        # locked between the time the user searched and the time the
        # user clicked the button.
        if latest is None:
            lock = EntryLock.objects.get(entry=entry_id)
            return TemplateResponse(
                request, 'lexicography/locked.html',
                {'page_title': "Lexicography",
                 'lock': lock})
        chunk = latest.c_hash
    else:
        chunk = Chunk(data=clean_xml(
            open(os.path.join(dirname, "skeleton.xml"), 'r').read()))
        chunk.schema_version = XMLTree(
            chunk.data.encode("utf-8")).extract_version()
        chunk.save()

    form = SaveForm(instance=chunk,
                    initial={"saveurl":
                             reverse('lexicography_handle_save',
                                     args=(handle_or_entry_id,)),
                             "initial_etag":
                             entry.latest.etag if entry else None})

    return render(request, 'lexicography/new.html', {
        'page_title': "Lexicography | Edit",
        'form': form,
        'new_entry': new_entry
    })

# This is purposely not set through the settings. Why? Because this is
# not something which someone installing BTW should have the
# opportunity to change. The Django **code** depends on wed being at a
# certain version. Changing this in the settings file would be a
# recipe for disaster.
REQUIRED_WED_VERSION = "0.27.0"


def version_check(version):
    if not semver.match(version, ">=" + REQUIRED_WED_VERSION):
        return [{'type': "version_too_old_error"}]
    return []


def uses_handle_or_entry_id(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        handle_or_entry_id = kwargs.pop('handle_or_entry_id')
        handle = None
        entry_id = None
        if handle_or_entry_id.startswith("h:"):
            hm = handles.get_handle_manager(request.session)
            handle = handle_or_entry_id[2:]
            try:
                entry_id = hm.id(handle)
            except ValueError:
                logger.error(
                    "user %s tried accessing handle %s which did not exist"
                    " in the handle manager associated with sesssion %s",
                    request.user.username, handle,
                    request.session.session_key)
                resp = json.dumps(
                    {'messages': [{'type': 'save_fatal_error'}]},
                    ensure_ascii=False)
                return HttpResponse(resp, content_type=JSON_TYPE)
        else:
            entry_id = handle_or_entry_id

        return view(request, entry_id=entry_id, handle=handle, *args, **kwargs)
    return wrapper


def get_etag(request, entry_id, handle):
    if entry_id is None:
        return None

    ret = Entry.objects.get(id=entry_id).latest.etag
    return ret


def save_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view(request, *args, **kwargs)

        messages = [{'type': 'save_transient_error',
                     'msg': 'Save failed because you are not logged in. '
                            'Perhaps you logged out from BTW in another tab?'}]

        resp = json.dumps({'messages': messages}, ensure_ascii=False)
        return HttpResponse(resp, content_type=JSON_TYPE)

    return wrapper


@save_login_required
@require_POST
@uses_handle_or_entry_id
@etag(get_etag)
def handle_save(request, entry_id, handle):
    if not request.is_ajax():
        return HttpResponseBadRequest()

    command = request.POST.get("command")
    messages = []
    entry = None
    if command:
        messages += version_check(request.POST.get("version"))
        if command == "check":
            pass
        elif command in ("save", "autosave", "recover"):
            entry = _save_command(request, entry_id, handle, command, messages)
        else:
            return HttpResponseBadRequest("unrecognized command")
    resp = json.dumps({'messages': messages}, ensure_ascii=False)
    response = HttpResponse(resp, content_type=JSON_TYPE)

    # We want to set ETag ourselves to the correct value because the
    # etag decorator will actually set it to the value it had before the
    # request was processed!
    if entry:
        response['ETag'] = quote_etag(entry.latest.etag)

    return response


_COMMAND_TO_ENTRY_TYPE = {
    "save": ChangeRecord.MANUAL,
    "recover": ChangeRecord.RECOVERY,
    "autosave": ChangeRecord.AUTOMATIC
}


@transaction.atomic
def _save_command(request, entry_id, handle, command, messages):
    data = xhtml_to_xml(
        urllib.unquote(request.POST.get("data")))
    xmltree = XMLTree(data.encode("utf-8"))

    unclean = xmltree.is_data_unclean()
    if unclean:
        chunk = Chunk(data=data,
                      is_normal=False,
                      # Unclean data, no version ...
                      schema_version="")
        chunk.save()
        logger.error("Unclean chunk: %s, %s", chunk.c_hash, unclean)
        # Yes, we want to commit...
        messages.append({'type': 'save_fatal_error'})
        return None

    if xmltree.extract_lemma() is None:
        messages.append(
            {'type': 'save_transient_error',
             'msg': 'Please specify a lemma for your entry.'})
        return None

    schema_version = xmltree.extract_version()
    chunk = Chunk(data=data, schema_version=schema_version)
    chunk.save()

    if entry_id is not None:
        entry = Entry.objects.select_for_update().get(id=entry_id)
    else:
        entry = Entry()

    subtype = _COMMAND_TO_ENTRY_TYPE[command]

    try:
        with transaction.atomic():
            if not entry.try_updating(request, chunk, xmltree,
                                      ChangeRecord.UPDATE, subtype):
                # Update failed due to locking
                lock = EntryLock.objects.get(entry=entry)
                messages.append(
                    {'type': 'save_transient_error',
                     'msg': 'The entry is locked by user %s.'
                            % lock.owner.username})

                # Clean up the chunk.
                try:
                    chunk.delete()
                except ProtectedError:
                    # This means that the chunk is shared with another
                    # entry.
                    pass

                return None
    except IntegrityError:
        # Clean up the chunk.
        try:
            chunk.delete()
        except ProtectedError:
            # This means that the chunk is shared with another
            # entry.
            pass
        # Try to determine what the problem is. If there is an
        # IntegrityError it is possible that it is *not* due to a
        # duplicate lemma.
        others = Entry.objects.filter(lemma=entry.lemma)
        if len(others) > 1 or (others and others[0].id != entry.id):
            # Duplicate lemma
            messages.append(
                {'type': 'save_transient_error',
                 'msg': u'There is another entry with the lemma "{0}".'
                        .format(entry.lemma)})
            return None

        # Can't figure it out.
        logger.error("undetermined integrity error")
        raise

    if entry_id is None:
        hm = handles.get_handle_manager(request.session)
        hm.associate(handle, entry.id)
    messages.append({'type': 'save_successful'})
    return entry


# This is a debug view only so we don't cache.
@never_cache
@login_required
@require_GET
def editing_data(request):
    # This view exists only when debugging.
    if not settings.DEBUG:
        raise Http404

    found_entries = None
    query_string = request.GET.get('q', None)
    if query_string is not None and query_string.strip():
        entry_query = util.get_query(query_string, ['data'])

        found_entries = Entry.objects.filter(entry_query)

    if found_entries is None or len(found_entries) == 0:
        raise Http404

    # We return only data for the first hit.
    return HttpResponse(found_entries[0].data, content_type="text/plain")

_cached_BTW_WED_LOGGING_PATH = None


def _get_and_check_logging_path():
    # We can't just cache the logging path in by executing code at the
    # top level of our module due to Django limitations. (It might
    # cause unforeseen problems. So the first time this is called, it
    # will do the sanity checks on BTW_WED_LOGGING_PATH and cache the
    # value. On future calls, it won't do the checks again.

    # pylint: disable=W0603
    global _cached_BTW_WED_LOGGING_PATH

    if _cached_BTW_WED_LOGGING_PATH is not None:
        return _cached_BTW_WED_LOGGING_PATH

    if settings.BTW_WED_LOGGING_PATH is None:
        raise ImproperlyConfigured("BTW_WED_LOGGING_PATH must be set to where "
                                   "you want wed's logs to be stored.")

    if not os.path.exists(settings.BTW_WED_LOGGING_PATH):
        os.mkdir(settings.BTW_WED_LOGGING_PATH)

    _cached_BTW_WED_LOGGING_PATH = settings.BTW_WED_LOGGING_PATH
    return _cached_BTW_WED_LOGGING_PATH


@login_required
@require_POST
def log(request):
    data = request.POST.get('data')
    username = request.user.username
    session_key = request.session.session_key
    logging_path = _get_and_check_logging_path()
    logfile = open(os.path.join(logging_path,
                                username + "_" + session_key + ".log"), 'a+')
    logfile.write(data)
    return HttpResponse()


@login_required
@require_POST
def change_revert(request, change_id):
    change = ChangeRecord.objects.get(id=change_id)
    chunk = change.c_hash
    xmltree = XMLTree(chunk.data.encode("utf-8"))
    if not change.entry.try_updating(request, chunk, xmltree,
                                     ChangeRecord.REVERT,
                                     ChangeRecord.MANUAL):
        return HttpResponse("Entry locked!", status=409)
    return HttpResponse("Reverted.")


@login_required
@require_POST
@permission_required('lexicography.garbage_collect')
def collect(request):
    chunks = Chunk.objects.collect()
    resp = "<br>".join(str(c) for c in chunks)
    return HttpResponse(resp + "<br>collected.")

# Yes, we use GET instead of POST for this view. Yes, we are breaking
# the rules. This is used only by the test suite.
@never_cache
@login_required
@require_GET
@uses_handle_or_entry_id
def handle_background_mod(request, entry_id, handle):
    if not settings.BTW_TESTING:
        raise Exception("BTW_TESTING not on!")

    entry = None
    if entry_id is None:
        raise Exception("this requires an existing entry")

    entry = Entry.objects.get(id=entry_id)

    locks = EntryLock.objects.filter(entry=entry)
    if locks.count():
        lock = locks[0]
        # Cause the lock to expire.
        lock.datetime = lock.datetime - models.LEXICOGRAPHY_LOCK_EXPIRY - \
            datetime.timedelta(seconds=1)
        lock.save()

    # We set the user of the modification to "admin".
    request.user = get_user_model().objects.get(username="admin")
    messages = []
    from .tests import util as test_util
    tree = test_util.set_lemma(entry.latest.c_hash.data, "Glerbl")
    old_post = request.POST
    request.POST = QueryDict('', mutable=True)
    request.POST.update(old_post)
    request.POST["data"] = test_util.stringify_etree(tree)

    logger.debug(entry.latest.etag)
    _save_command(request, entry_id, handle, "save", messages)
    entry = Entry.objects.get(id=entry_id)
    logger.debug(entry.latest.etag)

    if len(messages) != 1:
        raise Exception("there should be only one message")

    if messages[0]['type'] != "save_successful":
        raise Exception("the save was not successful")

    release_entry_lock(entry, request.user)

    return HttpResponse()


# Yes, we use GET instead of POST for this view. Yes, we are breaking
# the rules. This is used only by the test suite.
@never_cache
@login_required
@require_GET
def entry_testing_mark_valid(request, lemma):
    """
    This is a view that exists only in testing. It marks the latest
    version of an entry as valid, unconditionally.
    """
    if not settings.BTW_TESTING:
        raise Exception("BTW_TESTING not on!")

    try:
        entry = Entry.objects.get(lemma=lemma)
    except Entry.DoesNotExist:
        entry = None

    if entry is None:
        original = Entry.objects.get(lemma="foo")
        entry = Entry()
        data = original.latest.c_hash.data
        xmltree = XMLTree(data.encode("utf-8"))
        xmltree.alter_lemma(lemma)
        data = xmltree.serialize()
        entry.try_updating(request, original.latest.c_hash, xmltree,
                           ChangeRecord.CREATE,
                           ChangeRecord.MANUAL)
        release_entry_lock(entry, request.user)

    entry.latest.c_hash._valid = True  # pylint: disable=protected-access
    entry.latest.c_hash.save()

    return HttpResponse()

#  LocalWords:  html btwtmp utf saxon xsl btw tei teitohtml xml xhtml
#  LocalWords:  profiledir lxml xmlns
