import logging
import json
from functools import wraps
import itertools

from django.shortcuts import render
from django.http import HttpResponse, HttpResponseBadRequest, QueryDict
from django.template import loader, RequestContext
from django.core.exceptions import PermissionDenied
from django.views.decorators.http import require_GET, require_POST,  \
    require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from django_datatables_view.base_datatable_view import BaseDatatableView
from django.db.models import Q
from django.core.urlresolvers import resolve, reverse
from django.views.decorators.cache import never_cache
from django.core.cache import caches
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework import viewsets, generics, mixins, permissions, \
    parsers, renderers
from rest_framework.response import Response

from .zotero import Zotero, zotero_settings
from .models import Item, PrimarySource
from .forms import PrimarySourceForm
from .serializers import ItemSerializer, ItemAndPrimarySourceSerializer, \
    PrimarySourceSerializer
from . import tasks

logger = logging.getLogger(__name__)

btw_zotero = Zotero(zotero_settings(), 'BTW Library')
cache = caches["bibliography"]

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


@never_cache
@ajax_login_required
@require_GET
def _ajax_search(request):
    # present a unbound form.
    template = loader.get_template('bibliography/search_form.html')
    return HttpResponse(template.render(RequestContext(request)))


def previously_refreshed():
    return cache.get(tasks.FETCH_DATE_KEY) or "Unknown"

@ajax_login_required
@require_POST
def initiate_refresh(request):
    tasks.fetch_items.delay()
    return HttpResponse(json.dumps(previously_refreshed(),
                                   cls=DjangoJSONEncoder),
                        content_type="application/json")


@never_cache
@ajax_login_required
@require_GET
def check_refresh(request):
    return HttpResponse(json.dumps(previously_refreshed(),
                                   cls=DjangoJSONEncoder),
                        content_type="application/json")


# Never cache so that we can have an number for prev_refreshed.
@never_cache
@login_required
@require_GET
def manage(request, editable=False, submenu="btw-bibliography-manage-sub"):
    template = loader.get_template('bibliography/manage.html')
    context = RequestContext(
        request,
        {
            'can_edit': (
                editable and
                request.user.has_perm('bibliography.add_primarysource') and
                request.user.has_perm('bibliography.change_primarysource')),
            'submenu': submenu,
            'prev_refreshed': json.loads(json.dumps(previously_refreshed(),
                                                    cls=DjangoJSONEncoder)),
            'check_refresh_url': reverse('bibliography_check_refresh'),
            'initiate_refresh_url': reverse('bibliography_initiate_refresh')
        })
    return HttpResponse(template.render(context))


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

class AllListView(generics.ListAPIView):

    def get_queryset(self):
        return itertools.chain(Item.objects.all(), PrimarySource.objects.all())

    serializer_class = ItemAndPrimarySourceSerializer

def targets_to_dicts(targets):
    """
    :param target: The targets to resolve.
    :type target: An iteratable structure.
    :returns: A dictionary that maps targets to a dictionary of values.
    """
    ret = {}
    for target in targets:
        resolved = resolve(target)
        try:
            class_ = {
                "bibliography_primary_sources": PrimarySource,
                "bibliography_items": Item
            }[resolved.url_name]
        except KeyError:
            raise ValueError("cannot determine where this target "
                             "comes from: " + target)
        ret[target] = class_.objects.get(pk=resolved.kwargs['pk']) \
                                    .as_dict()

    return ret


def _narrow_to_matching_items(qs, text, primary_sources=True):
    q = Q(creators__icontains=text) | Q(title__icontains=text)

    if primary_sources:
        q = q | Q(primary_sources__reference_title__icontains=text)

    return qs.filter(q).distinct()

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
            qs = _narrow_to_matching_items(qs, sSearch)

        return qs

    def prepare_results(self, qs):
        data = super(ItemTable, self).prepare_results(qs)
        for d in data:
            d[2] = d[2].all().count()
        return data

@never_cache
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
        # We want to narrow the list *only* if the search
        # does not match our parent
        if sSearch and \
            not _narrow_to_matching_items(
                Item.objects.filter(pk=self.item.pk), sSearch,
                False).count():
            qs = qs.filter(Q(reference_title__icontains=sSearch) |
                           Q(genre__icontains=sSearch))

        return qs


@ajax_login_required
@require_GET
def item_primary_sources(request, pk):
    return PrimarySourceTable.as_view(item_pk=pk)(request)

class UpdateListRetrieveViewSet(mixins.ListModelMixin,
                                mixins.RetrieveModelMixin,
                                viewsets.GenericViewSet):
    pass

class PrimarySourcePermissions(permissions.DjangoModelPermissions):

    def __init__(self, *args, **kwargs):
        # We make this very restrictive: only people who can change
        # primary sources can access the interface.
        self.perms_map = dict(self.perms_map)
        for method in ("GET", "OPTIONS", "HEAD", "POST", "DELETE"):
            self.perms_map[method] = self.perms_map["PUT"]
        super(PrimarySourcePermissions, self).__init__(*args, **kwargs)

class FormRenderer(renderers.TemplateHTMLRenderer):
    media_type = "application/x-form"

    def render(self, data, media_type=None, renderer_context=None):
        # Allow returning an empty response when the transaction is
        # successful.
        if data is None:
            return ''

        return super(FormRenderer, self).render(data, media_type,
                                                renderer_context)

class PrimarySourceViewSet(UpdateListRetrieveViewSet):
    queryset = PrimarySource.objects.all()
    serializer_class = PrimarySourceSerializer
    permission_classes = (PrimarySourcePermissions, )
    parser_classes = (parsers.FormParser, )
    renderer_classes = (renderers.JSONRenderer,
                        FormRenderer,)
    lookup_field = "pk"
    template_name = 'bibliography/add_primary_source.html'

    def update(self, request, pk):
        instance = PrimarySource.objects.get(pk=pk)
        form = PrimarySourceForm(request.data, instance=instance)
        if form.is_valid():
            form.save()
            return Response()

        return Response({'form': form}, status=400, content_type="text/html")

    def retrieve(self, request, *args, **kwargs):
        if request.accepted_renderer.media_type == "application/x-form":
            pk = kwargs["pk"]
            instance = PrimarySource.objects.get(pk=pk)
            form = PrimarySourceForm(instance=instance)
            return Response({'form': form}, content_type="text/html")

        return super(PrimarySourceViewSet, self).retrieve(request,
                                                          *args, **kwargs)

@never_cache
def primary_sources(request, pk):
    # For historical reasons, we have this rather than plug the
    # viewset directly into the urls.py configuration. Eventually,
    # this should be reworked to use the Django REST Framework pattern
    # of urls.
    if request.method == "GET":
        return PrimarySourceViewSet.as_view({'get': 'retrieve'})(request,
                                                                 **{'pk': pk})
    elif request.method == "PUT":
        return PrimarySourceViewSet.as_view({'put': 'update'})(request, pk)

    # If we get here the query is for something still unimplemented.
    return HttpResponseBadRequest("unimplemented")
