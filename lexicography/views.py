# -*- coding: utf-8 -*-
"""Views for the lexicography app.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseBadRequest, Http404, QueryDict
from django.views.decorators.http import require_POST, require_GET, \
    require_http_methods, etag
from django.template import RequestContext
from django.db import IntegrityError
from django.db.models import ProtectedError
from django.conf import settings
from django.db import transaction
from django.utils.http import quote_etag
from django.utils.html import mark_safe
from django.contrib.auth import get_user_model
from django_datatables_view.base_datatable_view import BaseDatatableView

from functools import wraps
import os
import datetime
import semver
import json
import urllib
import logging

import lib.util as util
from . import handles
from .models import Entry, ChangeRecord, Chunk, UserAuthority, EntryLock
from . import models
from .locking import release_entry_lock, entry_lock_required, \
    try_acquiring_lock
from .xml import XMLTree, set_authority, xhtml_to_xml, clean_xml
from .forms import SearchForm, SaveForm

logger = logging.getLogger("lexicography")

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")


@require_GET
def main(request):
    return render(request, 'lexicography/main.html',
                  {'page_title': settings.BTW_SITE_NAME + " | Lexicography",
                   'form': SearchForm()})


class SearchTable(BaseDatatableView):
    model = Entry
    columns = ['headword']
    order_columns = ['headword']

    def render_column(self, row, column):
        ret = super(SearchTable, self).render_column(row, column)
        if column == 'headword':
            if row.is_editable_by(self.request.user):
                ret = mark_safe(
                    ('<a class="btn btn-xs btn-default" href="%s">Edit</a> ') %
                    reverse("lexicography_entry_update", args=(row.id, ))) + \
                    ret
            elif row.is_locked():
                ret = mark_safe('Locked by ' +
                                util.nice_name(row.is_locked()) + '. ') + ret
        return ret

    def filter_queryset(self, qs):
        sSearch = self.request.GET.get('sSearch', None)
        bHeadwordsOnly = self.request.GET.get('bHeadwordsOnly', "false") == \
            "true"
        # Remove deleted entries from the set.
        active = qs.exclude(ctype=Entry.DELETE)
        if sSearch:
            qs = active.filter(util.get_query(sSearch, ['headword']))
            if not bHeadwordsOnly:
                chunks = Chunk.objects.filter(
                    util.get_query(sSearch, ['data']))
                qs |= active.filter(c_hash=chunks)

        return qs


@require_GET
def search(request):
    """
    This is a view meant only for testing. It allows bypassing
    ``SearchTable`` to talk directly to the backend rather than having
    to emulate the AJAX talk between a ``DataTable`` instance in the
    client and the ``SearchTable`` view.
    """
    found_entries = None
    query_string = request.GET.get('q', None)
    headwords_only = request.GET.get('headwords_only', None)
    if query_string is not None and query_string.strip():
        entry_query = util.get_query(query_string, ['headword'])

        active_entries = Entry.objects.exclude(ctype=Entry.DELETE)

        found_entries = active_entries.filter(entry_query)
        if not headwords_only:
            chunk_query = util.get_query(query_string, ['data'])
            chunks = Chunk.objects.filter(chunk_query)

            found_entries |= active_entries.filter(c_hash=chunks)

    data = {}
    for entry in found_entries:
        data[entry.headword] = {
            "headword": entry.headword,
            "id": entry.id,
            "edit_url":
            reverse("lexicography_entry_update", args=(entry.id, ))
            if entry.is_editable_by(request.user) else None,
            "view_url": reverse("lexicography_entry_details",
                                args=(entry.id, ))
        }
    resp = json.dumps(data, ensure_ascii=False)
    return HttpResponse(resp, content_type="application/json")


@require_GET
def entry_details(request, entry_id):
    return render_to_response('lexicography/details.html',
                              context_instance=RequestContext(request))
    # data = Entry.objects.get(id=entry_id).data

    # (tmpdata_file, tmpdata_path) = tempfile.mkstemp(prefix='btwtmp')
    # with os.fdopen(tmpdata_file, 'w') as f:
    #     f.write(data.encode("utf-8"))

    # (tmptei_file, tmptei_path) = tempfile.mkstemp(prefix='btwtmp')
    # os.close(tmptei_file)

    # subprocess.check_call(["saxon", "-s:" + tmpdata_path, "-xsl:" +
    #                        os.path.join(schemas_dirname,
    #                                     "btw-storage-to-tei.xsl"), "-o:" +
    #                        tmptei_path])

    # (tmphtml_file, tmphtml_path) = tempfile.mkstemp(prefix="btwtmp")
    # os.close(tmphtml_file)

    # subprocess.check_call(["teitohtml", "--profiledir=" +
    #                        os.path.join(dirname, "btw-profiles"),
    #                        "--profile=html-render", tmptei_path,
    #                        tmphtml_path])

    # data = open(tmphtml_path).read()

    # return render_to_response('lexicography/details.html',
    #                           {'data': data},
    #                           context_instance=RequestContext(request))


def update_entry(request, entry, chunk, xmltree, ctype, subtype):
    cr = ChangeRecord()
    cr.entry = entry
    entry.copy_to(cr)
    entry.headword = xmltree.extract_headword()
    entry.user = request.user
    entry.datetime = util.utcnow()
    entry.session = request.session.session_key
    entry.ctype = ctype
    entry.csubtype = subtype
    entry.c_hash = chunk
    # entry.save() first. So that if we have an integrity error, there is no
    # stale ChangeRecord to remove.
    entry.save()
    cr.save()


def try_updating_entry(request, entry, chunk, xmltree, ctype, subtype):
    chunk.save()
    if entry.id is None:
        entry.headword = xmltree.extract_headword()
        entry.user = request.user
        entry.datetime = util.utcnow()
        entry.session = request.session.session_key
        entry.ctype = Entry.CREATE
        entry.csubtype = subtype
        entry.c_hash = chunk
        entry.save()
        if try_acquiring_lock(entry, request.user) is None:
            raise Exception("unable to acquire the lock of an entry "
                            "that was just created but not committed!")
    else:
        if try_acquiring_lock(entry, request.user) is None:
            return False
        update_entry(request, entry, chunk, xmltree, ctype, subtype)
    return True


@login_required
@require_GET
def entry_new(request):
    hm = handles.get_handle_manager(request.session)
    return HttpResponseRedirect(
        reverse('lexicography_handle_update',
                args=("h:" + str(hm.make_unassociated()),)))


@login_required
@require_GET
@entry_lock_required
def entry_update(request, entry_id):
    return HttpResponseRedirect(reverse('lexicography_handle_update',
                                        args=(entry_id,)))


@login_required
@require_http_methods(["GET", "POST"])
def handle_update(request, handle_or_entry_id):
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
            release_entry_lock(entry, request.user)
        return HttpResponseRedirect(reverse("lexicography_main"))

    if entry is not None:
        chunk = entry.c_hash
    else:
        chunk = Chunk()
        chunk.data = clean_xml(
            open(os.path.join(dirname, "skeleton.xml"), 'r').read())
        chunk.save()

    form = SaveForm(instance=chunk,
                    initial={"saveurl":
                             reverse('lexicography_handle_save',
                                     args=(handle_or_entry_id,)),
                             "initial_etag": entry.c_hash if entry else None})

    return render(request, 'lexicography/new.html', {
        'page_title': settings.BTW_SITE_NAME + " | Lexicography | Edit",
        'form': form,
    })

# This is purposely not set through the settings. Why? Because this is
# not something which someone installing BTW should have the
# opportunity to change. The Django **code** depends on wed being at a
# certain version. Changing this is a recipe for disaster.
REQUIRED_WED_VERSION = "0.17.1"


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
                    ("user {0} tried accessing handle {1} which did not exist"
                     " in the handle manager associated with sesssion {2}")
                    .format(request.user.username, handle,
                            request.session.session_key))
                resp = json.dumps(
                    {'messages': [{'type': 'save_fatal_error'}]},
                    ensure_ascii=False)
                return HttpResponse(resp, content_type="application/json")
        else:
            entry_id = handle_or_entry_id

        return view(request, entry_id=entry_id, handle=handle, *args, **kwargs)
    return wrapper


def get_etag(request, entry_id, handle):
    if entry_id is None:
        return None

    return Entry.objects.get(id=entry_id).etag


def save_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated():
            return view(request, *args, **kwargs)

        messages = [{'type': 'save_transient_error',
                     'msg': 'Save failed because you are not logged in. '
                     'Perhaps you logged out from BTW in another tab?'}]

        resp = json.dumps({'messages': messages}, ensure_ascii=False)
        return HttpResponse(resp, content_type="application/json")

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
    response = HttpResponse(resp, content_type="application/json")

    # We want to set ETag ourselves to the correct value because the
    # etag decorator will actually set it to the value it had before the
    # request was processed!
    if entry:
        response['ETag'] = quote_etag(entry.etag)

    return response


_COMMAND_TO_ENTRY_TYPE = {
    "save": Entry.MANUAL,
    "recover": Entry.RECOVERY,
    "autosave": Entry.AUTOMATIC
}


@transaction.atomic
def _save_command(request, entry_id, handle, command, messages):
    data = xhtml_to_xml(
        urllib.unquote(request.POST.get("data")))
    xmltree = XMLTree(data.encode("utf-8"))

    unclean = xmltree.is_data_unclean()
    if unclean:
        chunk = Chunk(data=data, is_normal=False)
        chunk.save()
        logger.error("Unclean chunk: %s, %s" % (chunk.c_hash, unclean))
        # Yes, we want to commit...
        messages.append({'type': 'save_fatal_error'})
        return None

    if xmltree.extract_headword() is None:
        messages.append(
            {'type': 'save_transient_error',
             'msg': 'Please specify a lemma for your entry.'})
        return None

    authority = xmltree.extract_authority()
    if authority == "/":
        # We must replace the temp value with something real
        try:
            authority = UserAuthority.objects.get(user=request.user)
        except UserAuthority.DoesNotExist:
            authority = UserAuthority()
            authority.user = request.user
            authority.save()
        data = set_authority(data, "/authority/" + str(authority.id))

    chunk = Chunk(data=data)
    chunk.save()

    if entry_id is not None:
        entry = Entry.objects.select_for_update().get(id=entry_id)
    else:
        entry = Entry()

    subtype = _COMMAND_TO_ENTRY_TYPE[command]

    try:
        with transaction.atomic():
            if not try_updating_entry(request, entry, chunk, xmltree,
                                      Entry.UPDATE, subtype):
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
        # duplicate headword.
        others = Entry.objects.filter(headword=entry.headword)
        if len(others) > 1 or (others and others[0].id != entry.id):
            # Duplicate headword
            messages.append(
                {'type': 'save_transient_error',
                 'msg': 'There is another entry with the lemma "{0}".'
                 .format(entry.headword)})
            return None

        # Can't figure it out.
        logger.error("undetermined integrity error")
        raise

    if entry_id is None:
        hm = handles.get_handle_manager(request.session)
        hm.associate(handle, entry.id)
    messages.append({'type': 'save_successful'})
    return entry


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
    if not try_updating_entry(request, change.entry, chunk, xmltree,
                              Entry.REVERT, Entry.MANUAL):
        return HttpResponse("<br>entry locked!")
    return HttpResponse("<br>reverted.")


@login_required
@require_POST
@permission_required('lexicography.garbage_collect')
def collect(request):
    chunks = Chunk.objects.collect()
    resp = "<br>".join(str(c) for c in chunks)
    return HttpResponse(resp + "<br>collected.")

#  LocalWords:  html btwtmp utf saxon xsl btw tei teitohtml xml xhtml
#  LocalWords:  profiledir lxml xmlns


# Yes, we use GET instead of POST for this view. Yes, we are breaking
# the rules. This is used only by the test suite.
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
    tree = test_util.set_lemma(entry.c_hash.data, "Glerbl")
    old_post = request.POST
    request.POST = QueryDict('', mutable=True)
    request.POST.update(old_post)
    request.POST["data"] = test_util.stringify_etree(tree)

    logger.debug(entry.etag)
    _save_command(request, entry_id, handle, "save", messages)
    entry = Entry.objects.get(id=entry_id)
    logger.debug(entry.etag)

    if len(messages) != 1:
        raise Exception("there should be only one message")

    if messages[0]['type'] != "save_successful":
        raise Exception("the save was not successful")

    release_entry_lock(entry, request.user)

    return HttpResponse()
