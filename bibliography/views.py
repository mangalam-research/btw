import logging
import json
from functools import wraps

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, QueryDict
from django.template import loader, RequestContext
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_GET, require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.core.urlresolvers import resolve

from .zotero import Zotero, zotero_settings
from .models import Item, PrimarySource
from .forms import PrimarySourceForm

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
        manage(request, submenu="btw-bibliography-general-sub")


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
def manage(request, editable=False, submenu="btw-bibliography-manage-sub"):
    _cache_all()
    template = loader.get_template('bibliography/manage.html')
    context = RequestContext(
        request,
        {
            'can_edit': (
                editable and
                request.user.has_perm('bibliography.add_primarysource') and
                request.user.has_perm('bibliography.change_primarysource')),
            'submenu': submenu
        })
    return HttpResponse(template.render(context))


def _item_to_dict(item):
    """
    Converts a database item to a dictionary of values. The set of
    values included in the dictionary is limited to what we want to
    expose from the database.

    We expose ``pk``, ``date``, ``title``, and ``creators``.

    :param item: The item.
    :type item: :class:`models.Item`
    :returns: The dictionary of values.
    """
    return {k: getattr(item, k)
            for k in ("pk", "date", "title", "creators")}


@require_GET
def items(request, pk):
    if not request.is_ajax():
        return HttpResponseBadRequest("only AJAX requests are supported")

    fmt = request.META.get('HTTP_ACCEPT', 'application/json')
    if fmt != 'application/json':
        return HttpResponseBadRequest("unknown content type: " + fmt)
    # This narrows down the set of fields we are sending back to a
    # limited set.
    return HttpResponse(json.dumps(_item_to_dict(Item.objects.get(pk=pk))),
                        content_type="application/json")


def targets_to_dicts(targets):
    """
    :param target: The targets to resolve.
    :type target: An iteratable structure.
    :returns: A dictionary that maps targets to a dictionary of values.
    """
    return dict([(target,
                  _item_to_dict(Item.objects.get(pk=resolve(target)
                                                 .kwargs['pk'])))
                 for target in targets])


class ItemTable(BaseDatatableView):
    columns = ['url', 'primary_sources_url', 'primary_sources',
               'new_primary_source_url', 'creators', 'title', 'date']
    order_columns = ['', '', '', '', 'creators', 'title', 'date']

    max_display_length = 500

    @classmethod
    def as_view(cls, *args, **kwargs):
        return ajax_login_required(
            require_GET(super(ItemTable, cls).as_view(*args,
                                                      **kwargs)))

    def get_initial_queryset(self):
        return Item.objects.all()

    def filter_queryset(self, qs):
        sSearch = self.request.GET.get('sSearch', None)
        if sSearch:
            qs = qs.filter(
                Q(creators__icontains=sSearch) |
                Q(title__icontains=sSearch) |
                Q(primary_sources__reference_title__icontains=sSearch)) \
                .distinct()

        return qs

    def prepare_results(self, qs):
        data = super(ItemTable, self).prepare_results(qs)
        for d in data:
            d[2] = d[2].all().count()
        return data


@ajax_login_required
@permission_required('bibliography.add_primarysource')
@require_http_methods(["GET", "POST"])
def new_primary_sources(request, pk):
    status = 200
    if request.method == 'POST':
        form = PrimarySourceForm(request.POST)

        if form.is_valid():
            source = form.save(commit=False)
            source.item = Item.objects.get(pk=pk)
            source.save()
            return HttpResponse()

        status = 400
    else:
        item = Item.objects.get(pk=pk)
        form = PrimarySourceForm(instance=PrimarySource(item=item))

    return render(request, 'bibliography/add_primary_source.html',
                  {'form': form}, status=status)


class PrimarySourceTable(BaseDatatableView):
    columns = ['url', 'reference_title', 'genre']
    order_columns = ['', 'reference_title', 'genre']

    max_display_length = 500
    item_pk = None

    def __init__(self, item_pk, *args, **kwargs):
        self.item_pk = item_pk
        self.item = Item.objects.get(pk=self.item_pk)
        super(PrimarySourceTable, self).__init__(*args, **kwargs)

    @classmethod
    def as_view(cls, *args, **kwargs):
        return ajax_login_required(
            require_GET(super(PrimarySourceTable, cls).as_view(*args,
                                                               **kwargs)))

    def get_initial_queryset(self):
        return self.item.primary_sources.all()

    def filter_queryset(self, qs):
        sSearch = self.request.GET.get('sSearch', None)
        if sSearch:
            qs = qs.filter(Q(reference_title__icontains=sSearch) |
                           Q(genre__icontains=sSearch))

        return qs


@ajax_login_required
@require_GET
def item_primary_sources(request, pk):
    return PrimarySourceTable.as_view(item_pk=pk)(request)


@ajax_login_required
@permission_required('bibliography.change_primarysource')
@require_http_methods(["GET", "PUT"])
def primary_sources(request, pk):
    fmt = request.META.get('HTTP_ACCEPT', 'application/json')
    instance = PrimarySource.objects.get(pk=pk)
    if request.method == "GET":
        if fmt == "application/x-form":
            form = PrimarySourceForm(instance=instance)
            return render(request, 'bibliography/add_primary_source.html',
                          {'form': form})
        elif fmt == "application/json":
            ret = {k: getattr(instance, k)
                   for k in ("reference_title", "genre", "pk")}
            ret["item"] = _item_to_dict(instance.item)
            return HttpResponse(json.dumps(ret),
                                content_type="application/json")
    elif request.method == "PUT":
        ctype = request.META["CONTENT_TYPE"]
        if ctype != "application/x-www-form-urlencoded; charset=UTF-8":
            return HttpResponseBadRequest("content type is not supported")
        form = PrimarySourceForm(QueryDict(request.body), instance=instance)
        if form.is_valid():
            form.save()
            return HttpResponse()
        elif fmt == "application/x-form":
            return render(request, 'bibliography/add_primary_source.html',
                          {'form': form}, status=400)

    # If we get here the query is for something still unimplemented.
    return HttpResponseBadRequest("unimplemented")
