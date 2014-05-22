# -*- coding: utf-8 -*-
"""Views for the lexicography app.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseBadRequest, Http404
from django.views.decorators.http import require_POST, require_GET, \
    require_http_methods
from django.template import RequestContext
from django.db import IntegrityError
from django.conf import settings
import os
import subprocess
import tempfile
import semver
import json
import urllib
import logging

import lib.util as util
from . import handles
from .models import Entry, ChangeRecord, Chunk, UserAuthority, EntryLock
from .locking import release_entry_lock, entry_lock_required, \
    try_acquiring_lock
from .xml import storage_to_editable, editable_to_storage, XMLTree, \
    set_authority, xhtml_to_xml
from .forms import SearchForm, RawSaveForm, SaveForm

logger = logging.getLogger("lexicography")

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")


@require_GET
def main(request):
    return render(request, 'lexicography/main.html',
                  {'page_title': settings.BTW_SITE_NAME + " | Lexicography",
                   'form': SearchForm()})


@require_GET
def search(request):
    found_entries = None
    query_string = request.GET.get('q', None)
    if query_string is not None and query_string.strip():
        entry_query = util.get_query(query_string, ['headword'])

        active_entries = Entry.objects.exclude(ctype=Entry.DELETE)

        found_entries = active_entries.filter(entry_query)

        chunk_query = util.get_query(query_string, ['data'])
        chunks = Chunk.objects.filter(chunk_query)

        found_entries |= active_entries.filter(c_hash=chunks)

    return render_to_response(
        'lexicography/main.html',
        {'page_title': settings.BTW_SITE_NAME + " | Lexicography",
         'form': SearchForm(request.GET),
         'query_string': query_string,
         'user': request.user,
         'found_entries': found_entries},
        context_instance=RequestContext(request))


@require_GET
def entry_details(request, entry_id):
    data = Entry.objects.get(id=entry_id).data

    (tmpdata_file, tmpdata_path) = tempfile.mkstemp(prefix='btwtmp')
    with os.fdopen(tmpdata_file, 'w') as f:
        f.write(data.encode("utf-8"))

    (tmptei_file, tmptei_path) = tempfile.mkstemp(prefix='btwtmp')
    os.close(tmptei_file)

    subprocess.check_call(["saxon", "-s:" + tmpdata_path, "-xsl:" +
                           os.path.join(schemas_dirname,
                                        "btw-storage-to-tei.xsl"), "-o:" +
                           tmptei_path])

    (tmphtml_file, tmphtml_path) = tempfile.mkstemp(prefix="btwtmp")
    os.close(tmphtml_file)

    subprocess.check_call(["teitohtml", "--profiledir=" +
                           os.path.join(dirname, "btw-profiles"),
                           "--profile=html-render", tmptei_path, tmphtml_path])

    data = open(tmphtml_path).read()

    return render_to_response('lexicography/details.html',
                              {'data': data},
                              context_instance=RequestContext(request))


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
@require_http_methods(["GET", "POST"])
@entry_lock_required
def entry_raw_update(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    if request.method == 'POST':
        form = RawSaveForm(request.POST)
        if form.is_valid():
            chunk = form.save(commit=False)
            chunk.data = storage_to_editable(chunk.data)
            xmltree = XMLTree(chunk.data)
            try_updating_entry(request, entry, chunk, xmltree, Entry.UPDATE,
                               Entry.MANUAL)
            release_entry_lock(entry, request.user)
    else:
        instance = entry.c_hash
        tmp = Chunk()
        tmp.data = editable_to_storage(instance.data)
        form = RawSaveForm(instance=tmp)

    ret = render(request, 'lexicography/new.html', {
        'page_title': settings.BTW_SITE_NAME + " | Lexicography | Edit",
        'form': form,
    })
    return ret


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
        chunk.data = storage_to_editable(
            open(os.path.join(dirname, "skeleton.xml"), 'r').read())
        chunk.save()

    form = SaveForm(instance=chunk,
                    initial={"saveurl":
                             reverse('lexicography_handle_save',
                                     args=(handle_or_entry_id,))})

    return render(request, 'lexicography/new.html', {
        'page_title': settings.BTW_SITE_NAME + " | Lexicography | Edit",
        'form': form,
    })

# This is purposely not set through the settings. Why? Because this is
# not something which someone installing BTW should have the
# opportunity to change. The Django **code** depends on wed being at a
# certain version. Changing this is a recipe for disaster.
REQUIRED_WED_VERSION = "0.15.0"


def version_check(version):
    if not semver.match(version, ">=" + REQUIRED_WED_VERSION):
        return [{'type': "version_too_old_error"}]
    return []


@login_required
@require_POST
def handle_save(request, handle_or_entry_id):
    if not request.is_ajax():
        return HttpResponseBadRequest()

    command = request.POST.get("command")
    messages = []
    if command:
        messages += version_check(request.POST.get("version"))
        if command == "check":
            pass
        elif command in ("save", "recover"):
            _save_command(request, handle_or_entry_id, command, messages)
        else:
            return HttpResponseBadRequest("unrecognized command")
    resp = json.dumps({'messages': messages}, ensure_ascii=False)
    return HttpResponse(resp, content_type="application/json")


def _save_command(request, handle_or_entry_id, command, messages):
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
            messages.append({'type': 'save_fatal_error'})
            return
    else:
        entry_id = handle_or_entry_id

    data = xhtml_to_xml(urllib.unquote(request.POST.get("data")))
    xmltree = XMLTree(data)

    unclean = xmltree.is_data_unclean()
    if unclean:
        chunk = Chunk(data=data, is_normal=False)
        chunk.save()
        logger.error("Unclean chunk: %s, %s" % (chunk.c_hash, unclean))
        # Yes, we want to commit...
        messages.append({'type': 'save_fatal_error'})
        return

    if xmltree.extract_headword() is None:
        messages.append(
            {'type': 'save_transient_error',
             'msg': 'Please specify a lemma for your entry.'})
        return

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

    subtype = Entry.MANUAL if command == "save" else Entry.RECOVERY

    try:
        if not try_updating_entry(request, entry, chunk, xmltree,
                                  Entry.UPDATE, subtype):
            # Update failed due to locking
            lock = EntryLock.objects.get(entry=entry)
            messages.append(
                {'type': 'save_transient_error',
                 'msg': 'The entry is locked by user %s.'
                 % lock.owner.username})
            # Clean up the chunk.
            chunk.delete()
            return
    except IntegrityError:
        # Clean up the chunk.
        chunk.delete()
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
            return

        # Can't figure it out.
        logger.error("undetermined integrity error")
        raise

    if entry_id is None:
        hm.associate(handle, entry.id)
    messages.append({'type': 'save_successful'})


@login_required
@require_GET
def editing_data(request):
    found_entries = None
    query_string = request.GET.get('q', None)
    if query_string is not None and query_string.strip():
        entry_query = util.get_query(query_string, ['data'])

        found_entries = Entry.objects.filter(entry_query)

    if found_entries is None or len(found_entries) == 0:
        raise Http404

    # We return only data for the first hit.
    return HttpResponse(storage_to_editable(found_entries[0].data),
                        content_type="text/plain")

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
    xmltree = XMLTree(chunk.data)
    if not try_updating_entry(request, change.entry, chunk, xmltree,
                              Entry.REVERT, Entry.MANUAL):
        return HttpResponse("<br>entry locked!")
    return HttpResponse("<br>reverted.")


@login_required
@require_POST
@permission_required('lexicography.garbage_collect')
def collect(request):
    # Find all chunks which are no longer referenced
    chunks = Chunk.objects.select_for_update().filter(
        entry__isnull=True, changerecord__isnull=True)
    chunks.delete()
    resp = "<br>".join(str(c) for c in chunks)
    return HttpResponse(resp + "<br>collected.")

#  LocalWords:  html btwtmp utf saxon xsl btw tei teitohtml xml xhtml
#  LocalWords:  profiledir lxml xmlns
