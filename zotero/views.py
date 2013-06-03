# Create your views here.

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from django.core.cache import get_cache
from django import forms
import urlparse
import os
import lxml.etree
import zotero
import logging
import btw.settings as settings

logger = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

class Cache(zotero.Cache):
    def __init__(self):
        zotero.Cache.__init__(self)
        # This cache must be defined in the settings.py file
        self.cache = get_cache("zotero")

    def resolve(self, url, data = None, headers = None):
        # We cache only gets not posts
        if data is None:
            url_str = str(url)
            ret = self.cache.get(url_str, None)
            if ret is not None:
                logger.debug("Zotero Cache: hit on " + url.safe_str())
            else:
                logger.debug("Zotero Cache: miss on " + url.safe_str())
                ret = self.server.resolve(url, data, headers).read()
                self.cache.set(url_str, ret)
        else:
            # POST, just pass through
            ret = self.server.resolve(url, data, headers)

        return ret

# Our Zotero query resolver, using our ad hoc cache.
z = zotero.Zotero(cache=Cache())

# TransactionParameters for the BTW library
uid = settings.ZOTERO_SETTINGS["uid"]
assert uid.startswith("u:") or uid.startswith("g:")
btw_tp = zotero.TransactionParameters(
    uid = uid[2:] if uid.startswith("u:") else None,
    gid = uid[2:] if uid.startswith("g:") else None,
    key = settings.ZOTERO_SETTINGS["api_key"]
)


atom_to_html = lxml.etree.XSLT(lxml.etree.parse(os.path.join(dirname, "atom-to-html.xsl")))
namespaces = {
    "atom" :"http://www.w3.org/2005/Atom",
    "xhtml": "http://www.w3.org/1999/xhtml",
    "zapi": "http://zotero.org/ns/api"
    }

class SearchForm(forms.Form):
    q = forms.CharField(max_length=100, label="Search")

@login_required
def main(request):
    return render(request, 'zotero/main.html', {'form': SearchForm()})

def get_zotero_transaction_parameters(request):
    zp = request.session.get("zotero_parameters")
    if zp is None:
        user = request.user.zoterouser

        # This should be checkd at input so we just do a cursory check here.
        assert user.uid.startswith("u:") or user.uid.startswith("g:")
        
        zp = zotero.TransactionParameters(
            uid = user.uid[2:] if user.uid.startswith("u:") else None, 
            gid = user.uid[2:] if user.uid.startswith("g:") else None,
            key = user.api_key)
        request.session["zotero_parameters"] = zp
    return zp

@login_required
def search(request):
    found_entries = None
    query_string = request.GET.get('q', '').strip()
    if len(query_string):
        tp = get_zotero_transaction_parameters(request)

        # Compute possible additional parameters for the Zotero query
        start_param = request.GET.get('start', '').strip()
        # Sanitize
        if not len(start_param) or start_param == "0":
            start_param = None

        # The minus sign at the beginning of the query negates
        # all types, so this will exclude attachments and web pages.
        resp = z.search(query_string, tp, content=html,
                        start = start_param, itemType= "-attachment || webpage")
        atom_tree = lxml.etree.XML(resp)

        # Find where the listing will start if the user goes forward...
        next_items = atom_tree.xpath("/atom:feed/atom:link[@rel='next']/@href",
                                     namespaces=namespaces)
        assert len(next_items) <= 1, "unexpected Zotero API result: query result contains more than one <link rel=\"next\"...>"
        next_start = None
        if len(next_items):
            next_start = urlparse.parse_qs(urlparse.urlparse(next_items[0]).query, True, True)
            assert next_start.has_key("start")
            assert len(next_start["start"]) == 1
            next_start = next_start["start"][0]

        # Find where the listing will start if the user goes backwards...
        # There does not seem to be a corresponding <link> element.
        prev_start = None
        if start_param:
            prev_start = int(start_param) - 50

        html_tree = atom_to_html(atom_tree, 
                                 **{"first-index": start_param if start_param else "1"})

    return render_to_response('zotero/main.html',
                              { 'form': SearchForm(request.GET), 
                                'query_string': query_string, 
                                'next_items': next_start,
                                'prev_items': prev_start,
                                'response': str(html_tree) },
                              context_instance=RequestContext(request))


@login_required
def associate(request):
    item_key = request.GET.get('item_key', '').strip()
    assert len(item_key), "item_key missing"
    tp = get_zotero_transaction_parameters(request)

    if request.GET.get('submit') is not None:
        resp = z.get_item(item_key, tp, content="json")
        atom_tree = lxml.etree.XML(resp)
        item_json = atom_tree.xpath("/atom:entry/atom:content/")
        assert len(item_json) > 0, "missing json content."
        assert len(item_json) == 1, "more than one json content."
        item_json = item_json[0]
        
        # Save it in our own library
        z.create_item(btw_tp, item_json, request.GET.get("zotero_write_token", None))
        # XXX incomplete
    else:
        resp = z.get_item(item_key, tp, content="html")
        atom_tree = lxml.etree.XML(resp)
        html_tree = atom_to_html(atom_tree)  

        proposed = \
            atom_tree.xpath("/atom:entry/zapi:creatorSummary/text()",
                            namespaces=namespaces)[0] + \
                            " " + \
                            atom_tree.xpath("/atom:entry/zapi:year/text()",
                                            namespaces=namespaces)[0]

        return render_to_response('zotero/associate.html',
                                  { 'item': str(html_tree),
                                    'item_key': item_key,
                                    'abbrev': proposed,
                                    'zotero_write_token': z.get_write_token()},
                                  context_instance=RequestContext(request))
    
    
