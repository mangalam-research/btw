# -*- coding: utf-8 -*-
"""Views for the lexicography app.

.. moduleauthor:: Louis-Dominique Dubeau <ldd@lddubeau.com>

"""
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseBadRequest, Http404
from django.views.decorators.http import require_POST, require_GET, \
    require_http_methods
from django.template import RequestContext
from django.utils.timezone import utc
from django.db import transaction
from django import forms
from wed import WedWidget
import util
import os
import subprocess
import tempfile
import btw.settings as settings
import datetime
import semver
import json
import urllib
import logging

from . import handles
from .models import Entry, ChangeRecord, Chunk, UserAuthority, EntryLock
from .locking import release_entry_lock, entry_lock_required, \
    try_acquiring_lock
from .xml import storage_to_editable, editable_to_storage, XMLTree, \
    set_authority, xhtml_to_xml

logger = logging.getLogger("lexicography")

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")

@require_GET
def main(request):
    return render(request, 'lexicography/main.html', {'form': SearchForm()})

class SearchForm(forms.Form):
    q = forms.CharField(max_length=100, label="Search")

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

    return render_to_response('lexicography/main.html',
                              { 'form': SearchForm(request.GET),
                                'query_string': query_string,
                                'found_entries': found_entries },
                              context_instance=RequestContext(request))

@require_GET
def entry_details(request, entry_id):
    data = Entry.objects.get(id=entry_id).data

    (tmpdata_file, tmpdata_path) = tempfile.mkstemp(prefix='btwtmp')
    with os.fdopen(tmpdata_file, 'w') as f:
        f.write(data.encode("utf-8"))

    (tmptei_file, tmptei_path) = tempfile.mkstemp(prefix='btwtmp')
    os.close(tmptei_file)

    subprocess.check_call(["saxon", "-s:" + tmpdata_path, "-xsl:" + os.path.join(schemas_dirname, "btw-storage-to-tei.xsl"), "-o:" + tmptei_path])

    (tmphtml_file, tmphtml_path) = tempfile.mkstemp(prefix="btwtmp")
    os.close(tmphtml_file)

    subprocess.check_call(["teitohtml", "--profiledir=" + os.path.join(dirname, "btw-profiles"), "--profile=html-render", tmptei_path, tmphtml_path])

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
    entry.datetime = datetime.datetime.utcnow().replace(tzinfo=utc)
    entry.session = request.session.session_key
    entry.ctype = ctype
    entry.csubtype = subtype
    entry.c_hash = chunk
    cr.save()
    entry.save()

def try_updating_entry(request, entry, chunk, xmltree, ctype, subtype):
    if not transaction.is_managed():
        raise Exception("try_updating_entry requires transactions to be "
                        "managed")
    chunk.save()
    if entry.id is None:
        entry.headword = xmltree.extract_headword()
        entry.user = request.user
        entry.datetime = datetime.datetime.utcnow().replace(tzinfo=utc)
        entry.session = request.session.session_key
        entry.ctype = Entry.CREATE
        entry.csubtype = subtype
        entry.c_hash = chunk
        entry.save()
        if try_acquiring_lock(entry, entry.user) is None:
            raise Exception("unable to acquire the lock of an entry "
                            "that was just created but not committed!")
    else:
        if try_acquiring_lock(entry, entry.user) is None:
            return False
        update_entry(request, entry, chunk, xmltree, ctype, subtype)
    return True

class _RawSaveForm(forms.ModelForm):
    class Meta(object):
        model = Chunk
        exclude = ('c_hash', 'is_normal')

@login_required
@require_http_methods(["GET", "POST"])
@entry_lock_required
def entry_raw_update(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    if request.method == 'POST':
        form = _RawSaveForm(request.POST)
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
        form = _RawSaveForm(instance=tmp)

    ret = render(request, 'lexicography/new.html', {
        'form': form,
    })
    return ret

class SaveForm(forms.ModelForm):
    class Media(object):
        js = (settings.BTW_REQUIREJS_PATH, ) \
            if not settings.BTW_WED_USE_REQUIREJS else ()

    class Meta(object):
        model = Chunk
        exclude = ('c_hash', 'is_normal')

    logurl = forms.CharField(widget=forms.HiddenInput(),
                             initial=reverse_lazy('log'))
    saveurl = forms.CharField(widget=forms.HiddenInput())
    data = forms.CharField(label="",
                           widget=WedWidget(source=settings.BTW_WED_PATH,
                                            css=settings.BTW_WED_CSS))

@login_required
@require_http_methods(["GET", "POST"])
def entry_new(request):
    if request.method == 'POST':
        # We don't actually save anything here because saves are done
        # through AJAX.
        return HttpResponseRedirect(reverse("main"))
    else:
        hm = handles.get_handle_manager(request.session)
        chunk = Chunk()
        chunk.data = storage_to_editable(
            open(os.path.join(dirname, "skeleton.xml"), 'r').read())
        chunk.save()
        form = SaveForm(instance=chunk,
                        initial = {"saveurl":
                                   reverse('handle_save',
                                           args=(hm.make_unassociated(),))
                                   })

    return render(request, 'lexicography/new.html', {
        'form': form,
    })

@login_required
@require_http_methods(["GET", "POST"])
@entry_lock_required
def entry_update(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    if request.method == 'POST':
        # We don't actually save anything here because saves are done
        # through AJAX. We get here if the user decided to quit editing.
        release_entry_lock(entry, request.user)
        return HttpResponseRedirect(reverse("main"))

    hm = handles.get_handle_manager(request.session)
    form = SaveForm(instance=entry.c_hash,
                    initial = {"saveurl":
                                   reverse('handle_save',
                                           args=(hm.make_associated(entry_id),))
                               })

    return render(request, 'lexicography/new.html', {
        'form': form,
    })

def version_check(version):
    if not semver.match(version, ">=0.6.0"):
        return [{'type': "version_failure" }]
    return []

@login_required
@require_POST
@transaction.commit_manually
def handle_save(request, handle):
    if not request.is_ajax():
        transaction.rollback()
        return HttpResponseBadRequest()

    command = request.POST.get("command")
    messages = []
    if command:
        messages += version_check(request.POST.get("version"))
        if command == "check":
            transaction.commit()
        elif command == "save" or command == "recover":
            hm = handles.get_handle_manager(request.session)
            data = xhtml_to_xml(urllib.unquote(request.POST.get("data")))
            xmltree = XMLTree(data)
            unclean = xmltree.is_data_unclean()
            if not unclean:
                authority =  xmltree.extract_authority()
                if authority == "/":
                    # We must replace the temp value with something real
                    try:
                        authority = UserAuthority.objects.get(user=request.user)
                    except UserAuthority.DoesNotExist:
                        authority = UserAuthority()
                        authority.user = request.user
                        authority.save()
                    data = set_authority(data,
                                         "/authority/" + str(authority.id))
                chunk = Chunk(data=data)
                chunk.save()
                entry_id = hm.id(handle)
                if entry_id is not None:
                    entry = Entry.objects.select_for_update().get(id=entry_id)
                else:
                    entry = Entry()

                if xmltree.extract_headword() is None:
                    messages.append({'type': 'save_validation_error',
                                     'msg': 'Please specify a lemma.'})
                    transaction.rollback()
                else:
                    subtype = Entry.MANUAL if command == "save" \
                        else Entry.RECOVERY
                    if not try_updating_entry(request, entry, chunk, xmltree,
                                              Entry.UPDATE, subtype):
                        # Update failed due to locking
                        lock = EntryLock.objects.get(entry=entry.id)
                        messages.append(
                            {'type': 'locked',
                             'msg': 'The entry is locked by user %s'
                             % str(lock.owner)})
                        transaction.rollback()
                    else:
                        if entry_id is None:
                            hm.associate(handle, entry.id)
                        messages.append({'type': 'save_successful'})
                        transaction.commit()
            else:
                chunk = Chunk(data=data, is_normal=False)
                chunk.save()
                logger.error("Unclean chunk: %s, %s" % (chunk.c_hash, unclean))
                transaction.commit()
                messages.append({'type': 'save_corrupted'})
        else:
            transaction.rollback()
            return HttpResponseBadRequest("unrecognized command")
    resp = json.dumps({'messages': messages}, ensure_ascii=False)
    return HttpResponse(resp, content_type="application/json")

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

if settings.BTW_WED_LOGGING_PATH is None:
    raise ImproperlyConfigured("BTW_WED_LOGGING_PATH must be set to where "
                               "you want wed's logs to be stored.")
else:
    if not os.path.exists(settings.BTW_WED_LOGGING_PATH):
        os.mkdir(settings.BTW_WED_LOGGING_PATH)

@login_required
@require_POST
def log(request):
    data = request.POST.get('data')
    username = request.user.username
    session_key = request.session.session_key
    logfile = open(os.path.join(settings.BTW_WED_LOGGING_PATH,
                                username + "_" + session_key + ".log"), 'a+')
    logfile.write(data)
    return HttpResponse()

@login_required
@entry_lock_required
@require_POST
def change_revert(request, change_id):
    change = ChangeRecord.objects.get(id=change_id)
    chunk = change.c_hash
    xmltree = XMLTree(chunk.data)
    try_updating_entry(request, change.entry, chunk, xmltree, Entry.REVERT,
                       Entry.MANUAL)
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
