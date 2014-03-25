import urllib
import logging
from functools import wraps

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect, \
    HttpResponseServerError, HttpResponseBadRequest
from django.template import Context, loader, RequestContext
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required, permission_required
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.db import IntegrityError

from .zotero import Zotero, zotero_settings
from .models import ZoteroUser, Item
from .forms import SearchForm

logger = logging.getLogger(__name__)

btw_zotero = Zotero(zotero_settings(), 'BTW Library')


def ajax_login_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated():
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


@require_GET
def search(request):
    return _ajax_search(request) if request.is_ajax() else \
        title(request, submenu="btw-bibliography-general-sub")


@ajax_login_required
@require_GET
def _ajax_search(request):
    # present a unbound form.
    form = SearchForm()
    template = loader.get_template('bibliography/search_form.html')
    context = RequestContext(request, {'form': form})
    return HttpResponse(template.render(context))


def _cache_all():
    search_results, _extra_vars = btw_zotero.get_all()
    for result in search_results:
        key = result["itemKey"]
        if not Item.objects.filter(item_key=key).exists():
            t = Item(item_key=key, uid=btw_zotero.full_uid)
            t.save()

    # Items are never deleted from this cache.


@login_required
@require_GET
def title(request, editable=False, submenu="btw-bibliography-title-sub"):
    _cache_all()
    form = SearchForm()
    template = loader.get_template('bibliography/title.html')
    context = RequestContext(
        request,
        {
            'form': form,
            'can_edit': (editable and
                         request.user.has_perm('bibliography.change_item')),
            'submenu': submenu

        })
    return HttpResponse(template.render(context))


@ajax_login_required
@require_POST
def exec_(request):
    if not request.is_ajax():
        return HttpResponseBadRequest()

    # 1. from POST dictionary prepare:
    # a. the zotero library to search info from.
    # b. the keyword to search zotero for.

    # 2. perform search
    # a. see if the search got modified for the field
    # b. if not fetch from cache.
    # c. if modified fetch from zotero, reset key in cache
    # d. if result doesnot exist in cache forcefully fetch.

    query_dict = request.POST

    if 'keyword' not in query_dict:
        return HttpResponseServerError("cannot interpret form data.")

    results_list = []
    extra_data = {}
    try:
        search_results, extra_vars = btw_zotero.search(query_dict['keyword'])

        # update data
        results_list.extend(search_results)
        extra_data.update(extra_vars)

    except ValueError:
        return HttpResponseServerError("Malformed form data.")

    # append the results_list to the user's session
    # as the keyword changes, the result changes
    # when user's session is invalidated, the data too is cleaned.
    request.session['results_list'] = results_list
    request.session['extra_data'] = extra_data
    logger.debug("ajax update fired")

    # redirect to pagination url for returning the results first time.
    return HttpResponseRedirect('/bibliography/results/')


@ajax_login_required
@require_GET
def results(request):
    """ pagination logic for the search results """

    results_list = request.session.get('results_list')
    extra_data = request.session.get('extra_data')

    if type(results_list) is list:
        logger.debug("start paginating the results")
        paginator = Paginator(results_list,
                              settings.BIBLIOGRAPHY_PAGINATION_SIZE)
        page = request.GET.get('page')
        try:
            results = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            results = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 999), deliver last page of results.
            results = paginator.page(paginator.num_pages)

        template = loader.get_template('bibliography/results.html')
        context = Context({
            'results': results,
            'extras': extra_data,
        })
        return HttpResponse(template.render(context))

    return HttpResponseServerError('Search error.')


@ajax_login_required
@require_GET
def abbrev(request, itemKey):
    item = btw_zotero.get_item(itemKey)
    ret = None

    creators = item.get("creators", None)
    if creators is not None:
        first = creators[0]
        ret = first.get("lastName", first.get("firstName", first.get("name",
                                                                     None)))

    if ret is None:
        ret = "***ITEM HAS NO AUTHORS***"
    return HttpResponse(ret)


@ajax_login_required
@require_GET
def info(request, itemKey):
    item = btw_zotero.get_item(itemKey)
    ret = ""

    creators = item.get("creators", None)
    if creators is not None:
        names = [creator.get("lastName", creator.get("firstName",
                                                     creator.get("name",
                                                                 "")))
                 for creator in creators]
        ret = ", ".join(names)

    title = item.get("title", None)
    if title:
        ret += ", " + title

    year = item.get("date", None)
    if year:
        ret += ", " + year

    return HttpResponse(ret)


@ajax_login_required
@require_POST
def sync(request):
    """ Sync the given json string to BTW project.

    Sync has two steps :
    1) search (Item type, title ) if not with BTW project
    2) sync(write) if new item otherwise,
    3) mark it duplicate."""

    results_list = request.session.get('results_list')
    enc_string = request.POST.get('enc')

    if type(enc_string) is unicode and type(results_list) is list:
        data_dict = None
        for result in results_list:
            if 'itemKey' in result and result['itemKey'] == enc_string:
                data_dict = result
                break

        else:
            if len(enc_string) == 0:
                return HttpResponseServerError(
                    "ERROR: malformed data cannot be copied.")
            return HttpResponse(
                "ERROR: Item not in result database.")

        title = data_dict.get('title')
        item_type = data_dict.get('itemType')

        # Search for duplicates.
        search_results, extras = btw_zotero.duplicate_search(
            urllib.quote(title.lower()), item_type)

        dup_results = btw_zotero.duplicate_drill_down(search_results,
                                                      data_dict)

        if len(dup_results) == 0:
            local_profile_object = ZoteroUser.objects.get(
                btw_user=request.user)
            if item_type == u'attachment':
                # call set_attachment
                res = btw_zotero.set_attachment(data_dict,
                                                local_profile_object)

            else:
                # call set_item
                res = btw_zotero.set_item(data_dict)

            # do additional steps to manipulate bibliography_sync_status to 0
            if res == "OK":
                extra_dict = request.session.pop('extra_data')
                if enc_string in extra_dict:
                    extra_dict[enc_string]['sync_status'] = 0
                # restore the extra dictionary
                request.session['extra_data'] = extra_dict

            return HttpResponse(res)

        else:
            extra_dict = request.session.pop('extra_data')
            if enc_string in extra_dict:
                extra_dict[enc_string]['sync_status'] = 1
            # restore the extra dictionary
            request.session['extra_data'] = extra_dict

            return HttpResponse("DUP")

    return HttpResponseServerError(
        "ERROR: session data or query parameters incorrect.")


class ItemList(BaseDatatableView):
    model = Item

    # define the columns that will be returned
    columns = ['reference_title_url', 'reference_title', 'creators', 'title',
               'date']
    order_columns = ['', 'reference_title', 'creators', 'title', 'date']

    max_display_length = 500

    @classmethod
    def as_view(cls, *args, **kwargs):
        return ajax_login_required(
            require_GET(super(ItemList, cls).as_view(*args,
                                                     **kwargs)))

    def get_initial_queryset(self):
        return Item.objects.all()

    def filter_queryset(self, qs):
        sSearch = self.request.GET.get('sSearch', None)
        if sSearch:
            qs = qs.filter(Q(reference_title__icontains=sSearch) |
                           Q(creators__icontains=sSearch) |
                           Q(title__icontains=sSearch))

        return qs


@ajax_login_required
@permission_required('bibliography.change_item')
@require_POST
def reference_title(request, itemKey):
    item = Item.objects.get(item_key=itemKey)
    # An empty field must be normalized to None.
    item.reference_title = request.POST.get('value') or None
    try:
        item.save()
    except IntegrityError:
        return HttpResponseBadRequest(
            "There is already an item with this title.")
    return HttpResponse()


@require_GET
def testjs(request):
    """ Qunit tests view """
    template = loader.get_template('bibliography/Qtests.html')
    context = RequestContext(request)
    return HttpResponse(template.render(context))
