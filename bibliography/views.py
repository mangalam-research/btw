import logging
from functools import wraps

from django.http import HttpResponse, HttpResponseBadRequest
from django.template import loader, RequestContext
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required, permission_required
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.db import IntegrityError

from .zotero import Zotero, zotero_settings
from .models import Item

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
    _cache_all()
    # present a unbound form.
    template = loader.get_template('bibliography/search_form.html')
    return HttpResponse(template.render(RequestContext(request)))


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
    template = loader.get_template('bibliography/title.html')
    context = RequestContext(
        request,
        {
            'can_edit': (editable and
                         request.user.has_perm('bibliography.change_item')),
            'submenu': submenu

        })
    return HttpResponse(template.render(context))


@ajax_login_required
@require_GET
def abbrev(request, itemKey):
    item = Item.objects.get(item_key=itemKey)
    ret = ""

    if item.reference_title is not None:
        ret = item.reference_title
    else:
        creators = item.creators
        if creators is not None:
            ret = creators.split(",")[0]

        if ret is None:
            ret = "***ITEM HAS NO AUTHORS***"

        year = item.date
        if year:
            ret += ", " + year

    return HttpResponse(ret)


@ajax_login_required
@require_GET
def info(request, itemKey):
    item = Item.objects.get(item_key=itemKey)
    ret = ""

    creators = item.creators
    ret = creators.split(",")[0] if creators else "***ITEM HAS NO AUTHORS***"

    title = item.title
    ret += ", " + title

    date = item.date
    if date:
        ret += ", " + date

    return HttpResponse(ret)


class ItemList(BaseDatatableView):
    model = Item

    # define the columns that will be returned
    columns = ['item_key', 'reference_title_url', 'reference_title',
               'creators', 'title', 'date']
    order_columns = ['', '', 'reference_title', 'creators', 'title', 'date']

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
