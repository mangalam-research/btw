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
from django.views.decorators.http import require_POST
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
import lxml.etree
import datetime
import semver
import json
import urllib
import logging
import itertools
import re

logger = logging.getLogger("lexicography")

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")
xsl_dirname = os.path.join(dirname, "../utils/xsl/")

from .models import Entry, ChangeRecord, Chunk, UserAuthority

class HandleManager(object):
    """This classes manages the mapping between entry ids and handles
used for saving data. The handles provided by this class are passed to
the editor instance embedded in pages that edit lexicographic
entries. These handles are then used when saving the data back onto
the server to refer to specific entries.

The main advantage of using system is that it is possible to have
unassociated handles representing new articles that have not yet been
saved. The alternative would be to create a fake article whenever a
user asks to create a new article. If the user then aborted the
edition by reloading, or turning off the browser or some similar
non-excplicit action, these preemptively created articles would then
be left over on the system. The handle->id mapping allows the system
to give a handle that is not associated **yet** with an article. Upon
first save the server can then associate an id with it.

One object of this class must be created per session. The handles
provided by this class are guaranteed to be unique within a session.

:param session_key: The session key of the session associated with this object.
:type session_key: str

.. warning:: This class is not designed to provide security.
"""
    def __init__(self, session_key):
        self.session_key = session_key
        self.handle_to_entry_id = {}
        self.entry_id_to_handle = {}
        self.__count = itertools.count()

    @property
    def _next_name(self):
        return self.session_key + "." + str(self.__count.next())

    def make_associated(self, entry_id):
        """
Create a new handle if there is no handle associated with the id. Otherwise, return the handle already associated with it.

:param entry_id: The id to associate.
:type entry_id: int
:returns: The handle.
:rtype: str
"""
        handle = self.entry_id_to_handle.get(entry_id, None)
        if handle is not None:
            return handle

        handle = self._next_name
        while handle in self.handle_to_entry_id:
            handle = self._next_name

        self.entry_id_to_handle[entry_id] = handle
        self.handle_to_entry_id[handle] = entry_id
        return handle

    def make_unassociated(self):
        """
Create an unassociated handle.

:returns: The handle.
:rtype: str
"""
        handle = self._next_name
        while handle in self.handle_to_entry_id:
            handle = self._next_name

        self.handle_to_entry_id[handle] = None
        return handle

    def associate(self, handle, entry_id):
        """
Associate an unassociated handle with an id.

:param handle: The handle.
:type handle: str
:param entry_id: The id.
:type entry_id: int
"""
        if self.handle_to_entry_id[handle] is not None:
            raise ValueError("handle {0} already associated".format(handle))

        if self.entry_id_to_handle.get(entry_id, None) is not None:
            raise ValueError("id {0} already associated".format(entry_id))

        self.handle_to_entry_id[handle] = entry_id
        self.entry_id_to_handle[entry_id] = handle

    def id(self, handle):
        """
Return the id associated with a handle.

:param handle: The handle.
:type handle: str
:returns: The id.
:rtype: int or None
"""
        return self.handle_to_entry_id[handle]

hms = {}
def get_handle_manager(session):
    """
If the session already has a HandleManager, return it. Otherwise,
create one, associate it with the session and return it.

:param session: The session.
:type session: :py:class:`django.contrib.sessions.backends.base.SessionBase`
:returns: The handle manager.
:rtype: :py:class:`HandleManager`
"""
    # Check whether we have a HandleManager or need to create one
    hm = hms.get(session.session_key, None)
    if hm is None:
        hm = HandleManager(session.session_key)
        hms[session.session_key] = hm
    return hm



def main(request):
    return render(request, 'lexicography/main.html', {'form': SearchForm()})

class SearchForm(forms.Form):
    q = forms.CharField(max_length=100, label="Search")

def search(request):
    found_entries = None
    query_string = request.GET.get('q', None)
    if query_string is not None and query_string.strip():
        entry_query = util.get_query(query_string, ['headword'])

        active_entries = Entry.objects.exclude(ctype='D')

        found_entries = active_entries.filter(entry_query)

        chunk_query = util.get_query(query_string, ['data'])
        chunks = Chunk.objects.filter(chunk_query)

        found_entries |= active_entries.filter(c_hash=chunks)

    return render_to_response('lexicography/main.html',
                              { 'form': SearchForm(request.GET),
                                'query_string': query_string,
                                'found_entries': found_entries },
                              context_instance=RequestContext(request))

def details(request, entry_id):
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

def storage_to_editable(data):
    return util.run_saxon(os.path.join(xsl_dirname, "out/xml-to-html.xsl"),
                          data)

def editable_to_storage(data):
    return util.run_saxon(os.path.join(xsl_dirname, "out/html-to-xml.xsl"),
                          data)

class XMLTree(object):
    def __init__(self, data):
        """
The XML tree represetation of the data. Allows performing operations
on this tree or querying it.

:param data: The data to parse.
:type data: str
"""
        self.parsing_error = None
        self.tree = None
        try:
            self.tree = lxml.etree.fromstring(data)
        except lxml.etree.XMLSyntaxError as ex:
            self.parsing_error = "Parsing error: " + str(ex)

    def is_data_unclean(self):
        """
Ensure that the tree parses as XML and that it contains only div
elements in the ``http://www.w3.org/1999/xhtml`` namespace, no
processing instructions, no attributes in any namespace and no
attribute other than ``class`` or ``data-wed-*``.

:returns: Evaluates to False if the tree is clean, True if not. When unclean the value returned is a diagnosis message.

.. warning:: This method is security-critical. In theory it would be
    possible for one user of the system to include JavaScript in the
    data they send to BTW. This JavaScript could then be loaded in
    someone else's browser and executed there.
    """
        if self.parsing_error:
            return self.parsing_error

        for node in self.tree.iter():
            # pylint: disable-msg=W0212
            if isinstance(node, lxml.etree._ProcessingInstruction):
                return "Processing instruction found."
            elif isinstance(node, lxml.etree._Element):
                if node.tag != "{http://www.w3.org/1999/xhtml}div":
                    return "Element outside the xhtml namespace: " + node.tag
                for attr in node.attrib.keys():
                    if attr == "xmlns":
                        if node.attrib[attr] != "http://www.w3.org/1999/xhtml":
                            return ("Attribute xmlns with invalid value: " +
                                    node.attrib[attr] + ".")
                    elif attr != "class" and not attr.startswith("data-wed-"):
                        return "Invalid attribute: " + attr + "."

        return False

    def extract_headword(self):
        """
Extracts the headword from the XML tree. This is the contents of the
btw:lemma element.

:returns: The headword.
:rtype: str
"""
        class_sought = 'btw:lemma'
        lemma = self.tree.xpath(
            "xhtml:div[contains(@class, '" + class_sought + "')]",
            namespaces={
                'xhtml':
                'http://www.w3.org/1999/xhtml'})

        # Check that it is really what we want. Unfortunately writing the
        # XPath 1.0 (what lxml supports) required to do a good job at
        # tokenizing @class would be hairier than just doing it in python.
        if len(lemma):
            classes = lemma[0].get("class").strip().split()
            if not any(x == class_sought for x in classes):
                lemma = [] # Not what we wanted after all

        if not len(lemma):
            raise ValueError("can't find a headword in the data passed")

        return lemma[0].text

    def extract_authority(self):
        """
Extracts the authority from the XML tree. This is the contents of the
authority attribute on the top element.

:returns: The authority
:rtype: str
"""
        authority = self.tree.get('data-wed-authority')

        if authority is None:
            raise ValueError("can't find the authority in the data passed")

        return authority.strip()

auth_re = re.compile(r'authority\s*=\s*(["\']).*?\1')
new_auth_re = re.compile(r"^[A-Za-z0-9/]*$")
def set_authority(data, new_authority):
    # We don't use lxml for this because we don't want to introduce
    # another serialization in the pipe which may change things in
    # unexpected ways.
    if not new_auth_re.match(new_authority):
        raise ValueError("the new authority contains invalid data")
    return auth_re.sub('authority="{0}"'.format(new_authority), data, count=1)

def xhtml_to_xml(data):
    return data.replace(u"&nbsp;", u'\u00a0')

def update_entry(request, entry, chunk, xmltree, subtype):
    cr = ChangeRecord()
    cr.entry = entry
    entry.copy_to(cr)
    entry.headword = xmltree.extract_headword()
    entry.user = request.user
    entry.datetime = datetime.datetime.utcnow().replace(tzinfo=utc)
    entry.session = request.session.session_key
    entry.ctype = Entry.UPDATE
    entry.csubtype = subtype
    entry.c_hash = chunk
    cr.save()
    entry.save()

def try_updating_entry(request, entry, chunk, xmltree, subtype):
    # A garbage collection occurring between now and the time
    # we are done could result in a failure for us.
    tries = 3
    while tries:
        try:
            chunk.save()
            if entry.id is None:
                entry.headword = xmltree.extract_headword()
                entry.user = request.user
                entry.datetime = datetime.datetime.utcnow().replace(tzinfo=utc)
                entry.session = request.session.session_key
                entry.ctype = Entry.CREATION
                entry.csubtype = subtype
                entry.c_hash = chunk
                entry.save()
            else:
                update_entry(request, entry, chunk, xmltree, subtype)

            transaction.commit()
            tries = 0
        # Yes we're casting a wide net here with this
        # except. However, it is not clear exactly how a failure
        # at the DB level would manifest itself.
        except Exception as ex: # pylint: disable-msg=W0703
            transaction.rollback()
            tries -= 1
            if not tries:
                raise ex



class _RawSaveForm(forms.ModelForm):
    class Meta(object):
        model = Chunk
        exclude = ('c_hash', 'is_normal')

@login_required
@transaction.commit_manually
def raw_update(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    if request.method == 'POST':
        form = _RawSaveForm(request.POST)
        if form.is_valid():
            chunk = form.save(commit=False)
            chunk.data = storage_to_editable(chunk.data)
            xmltree = XMLTree(chunk.data)
            try_updating_entry(request, entry, chunk, xmltree, Entry.MANUAL)
    else:
        instance = entry.c_hash
        tmp = Chunk()
        tmp.data = editable_to_storage(instance.data)
        form = _RawSaveForm(instance=tmp)

    ret = render(request, 'lexicography/new.html', {
        'form': form,
    })
    transaction.commit()
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
def new(request):
    if request.method == 'POST':
        # We don't actually save anything here because saves are done
        # through AJAX.
        return HttpResponseRedirect(reverse("main"))
    else:
        hm = get_handle_manager(request.session)
        chunk = Chunk()
        chunk.data = storage_to_editable(
            open(os.path.join(dirname, "skeleton.xml"), 'r').read())
        chunk.save()
        form = SaveForm(instance=chunk,
                        initial = {"saveurl":
                                   reverse('save',
                                           args=(hm.make_unassociated(),))
                                   })

    return render(request, 'lexicography/new.html', {
        'form': form,
    })

@login_required
def update(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    if request.method == 'POST':
        # We don't actually save anything here because saves are done
        # through AJAX.
        return HttpResponseRedirect(reverse("main"))
    else:
        hm = get_handle_manager(request.session)
        form = SaveForm(instance=entry.c_hash,
                        initial = {"saveurl":
                                   reverse('save',
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
def save(request, handle):
    if not request.is_ajax():
        return HttpResponseBadRequest()

    command = request.POST.get("command")
    messages = []
    if command:
        messages += version_check(request.POST.get("version"))
        if command == "check":
            transaction.commit()
        elif command == "save" or command == "recover":
            hm = get_handle_manager(request.session)
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
                    entry = Entry.objects.get(id=entry_id)
                else:
                    entry = Entry()

                if xmltree.extract_headword() is None:
                    messages.append({'type': 'save_validation_error',
                                     'msg': 'Please specify a lemma.'})
                    transaction.rollback()
                else:
                    subtype = Entry.MANUAL if command == "save" \
                        else Entry.RECOVERY
                    try_updating_entry(request, entry, chunk, xmltree,
                                       subtype)
                    if entry_id is None:
                        hm.associate(handle, entry.id)
                    messages.append({'type': 'save_successful'})
            else:
                chunk = Chunk(data=data, is_normal=False)
                chunk.save()
                logger.error("Unclean chunk: %s, %s" % (chunk.c_hash, unclean))
                transaction.commit()
                messages.append({'type': 'save_corrupted'})
        else:
            return HttpResponseBadRequest("unrecognized command")
    resp = json.dumps({'messages': messages}, ensure_ascii=False)
    return HttpResponse(resp, content_type="application/json")

@login_required
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
@permission_required('lexicography.garbage_collect')
def collect(request):
    # Find all chunks which are no longer referenced
    chunks = Chunk.objects.filter(entry__isnull=True, changerecord__isnull=True)
    resp = "<br>".join(str(c) for c in chunks)
    chunks.delete()
    return HttpResponse(resp + "<br>collected.")

#  LocalWords:  html btwtmp utf saxon xsl btw tei teitohtml xml xhtml
#  LocalWords:  profiledir lxml xmlns
