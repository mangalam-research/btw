# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse_lazy
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, render_to_response
from django.http import HttpResponse, Http404
from django.views.decorators.http import require_POST
from django.template import RequestContext
from django import forms
from django.views.generic.edit import UpdateView
from wed import WedWidget
import util
import os
import subprocess
import tempfile
import btw.settings as settings
from lib.generic import LoginRequiredUpdateView

dirname = os.path.dirname(__file__)
schemas_dirname = os.path.join(dirname, "../utils/schemas")
xsl_dirname = os.path.join(dirname, "../utils/xsl/")

from models import Entry, Chunk

class SearchForm(forms.Form):
    q = forms.CharField(max_length=100, label="Search")

class SaveForm(forms.ModelForm):
    class Media:
        js = (settings.BTW_REQUIREJS_PATH, ) \
            if not settings.BTW_WED_USE_REQUIREJS else ()

    class Meta:
        model = Chunk
        exclude = ('c_hash', )

    logurl = forms.CharField(widget=forms.HiddenInput(),
                             initial=reverse_lazy('lexicography-log'));
    data = forms.CharField(label="",
                           widget=WedWidget(source=settings.BTW_WED_PATH,
                                            css=settings.BTW_WED_CSS))

class RawSaveForm(forms.ModelForm):
    class Meta:
        model = Chunk

def storage_to_editable(data):
    (tmpinput_file, tmpinput_path) = tempfile.mkstemp(prefix='btwtmp')
    with os.fdopen(tmpinput_file, 'w') as f:
        f.write(data.encode("utf-8"))

    (tmpoutput_file, tmpoutput_path) = tempfile.mkstemp(prefix='btwtmp')

    subprocess.check_call(["saxon", "-s:" + tmpinput_path, "-xsl:" + os.path.join(xsl_dirname, "out/xml-to-html.xsl"), "-o:" + tmpoutput_path])

    return os.fdopen(tmpoutput_file, 'r').read().decode('utf-8')

class UpdateEntryView(LoginRequiredUpdateView):
    def get_form_kwargs(self):
        ret = UpdateView.get_form_kwargs(self)
        instance = ret["instance"]

        instance.data = storage_to_editable(instance.data)

        return ret

@login_required
def update(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    return UpdateEntryView.as_view(
        model=Chunk,
        form_class=SaveForm,
        template_name='lexicography/new.html')(request, pk=entry.c_hash)

@login_required
def raw_update(request, entry_id):
    entry = Entry.objects.get(id=entry_id)
    return LoginRequiredUpdateView.as_view(
        model=Entry,
        form_class=RawSaveForm,
        template_name='lexicography/new.html')(request, pk=entry.c_hash)

def main(request):
    return render(request, 'lexicography/main.html', {'form': SearchForm()})

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

if not hasattr(settings, "BTW_WED_LOGGING_PATH"):
    raise ImproperlyConfigured("BTW_WED_LOGGING_PATH must be set to where "
                               "you want wed's logs to be stored.")
else:
    if not os.path.exists(settings.BTW_WED_LOGGING_PATH):
        os.mkdir(settings.BTW_WED_LOGGING_PATH)

@login_required
@require_POST
def log(request):
    data = request.POST.get('data')
    username = request.user.username;
    session_key = request.session.session_key
    logfile = open(os.path.join(settings.BTW_WED_LOGGING_PATH,
                                username + "_" + session_key + ".log"), 'a+')
    logfile.write(data);
    return HttpResponse()

@login_required
@permission_required('lexicography.garbage_collect')
def collect(request):
    # Find all chunks which are no longer referenced
    chunks = Chunk.objects.filter(entry__isnull=True, changerecord__isnull=True)
    resp = "<br>".join(str(c) for c in chunks)
    chunks.delete()
    return HttpResponse(resp + "<br>collected.")
