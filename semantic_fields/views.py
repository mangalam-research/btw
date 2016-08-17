from django_datatables_view.base_datatable_view import BaseDatatableView
from django.utils.html import mark_safe
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from django import forms
from django.views.decorators.cache import never_cache
from django.middleware.csrf import CsrfViewMiddleware
from django.http import HttpResponseBadRequest
from rest_framework import viewsets, mixins, renderers, parsers, permissions, \
    generics, filters, pagination, serializers
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import NotAcceptable
from grako.exceptions import FailedParse

from .models import SemanticField, SpecifiedSemanticField, make_specified_sf
from .serializers import SemanticFieldSerializer
from .forms import SemanticFieldForm
from .util import parse_local_references

def filter_by_search_params(qs, search, aspect, scope):
    search = search.strip()

    if search == "":
        return SemanticField.objects.none()

    if search[0] == '"' and search[-1] == '"':
        exact = ""  # Exact field lookup
        search = search[1:-1]  # Dump the quotes!
    else:
        exact = "__icontains"  # Inexact field lookup

    field = {"sf": "heading",
             "lexemes": "lexemes__searchword__searchword"}[aspect]

    if scope == "all":
        pass
    elif scope == "hte":
        qs = qs.filter(catid__isnull=False)
    elif scope == "btw":
        qs = qs.filter(catid__isnull=True)
    else:
        raise ValueError("unknown value for scope: " + scope)

    qs = qs.filter(**{field + exact: search})

    return qs

class SearchTable(BaseDatatableView):
    model = SemanticField

    columns = ['detail_url', 'heading']
    order_columns = ['', 'path']

    def render_column(self, row, column):
        if column == "heading":
            ret = mark_safe("<p>{0}</p>".format(row.linked_breadcrumbs))
            if row.related_by_pos:
                ret += mark_safe("<p>{0}</p>".format(
                    render_to_string("semantic_fields/other_pos.html", {
                        'instance': row
                    })))
            return ret

        return super(SearchTable, self).render_column(row, column)

    def filter_queryset(self, qs):
        search_value = self.request.GET.get('search[value]', None)
        aspect = self.request.GET['aspect']
        scope = self.request.GET['scope']

        return filter_by_search_params(qs, search_value, aspect, scope)

class SemanticFieldHTMLRenderer(renderers.TemplateHTMLRenderer):
    media_type = "text/html"
    template_name = 'semantic_fields/details.html'

class FormRenderer(renderers.TemplateHTMLRenderer):
    media_type = "application/x-form"
    template_name = 'semantic_fields/add.html'

    def render(self, data, media_type=None, renderer_context=None):
        # Allow returning an empty response when the transaction is
        # successful.
        if data is None:
            return ''

        return super(FormRenderer, self).render(data, media_type,
                                                renderer_context)


class SemanticFieldFilter(filters.BaseFilterBackend):

    def filter_queryset(self, request, qs, view):
        paths = request.GET.get('paths', None)
        ids = request.GET.get('ids', None)

        if paths is not None:
            qs = qs.filter(path__in=set(paths.split(";")))

        if ids is not None:
            qs = qs.filter(id__in=set(ids.split(";")))

        search = request.GET.get('search', None)
        if search is not None:
            aspect = request.GET['aspect']
            scope = request.GET['scope']
            qs = filter_by_search_params(qs, search, aspect, scope)
        return qs


RELATED_BY_POS = "related_by_pos"
CHILD = "child"

class SemanticFieldPagination(pagination.LimitOffsetPagination):
    default_limit = 10
    unfiltered_count = None

    def paginate_queryset(self, queryset, request, view=None):

        ret = super(SemanticFieldPagination, self) \
            .paginate_queryset(queryset, request, view)
        self.unfiltered_count = queryset.model.objects.count()
        return ret

    def get_paginated_response(self, data):
        base = super(SemanticFieldPagination,
                     self).get_paginated_response(data)
        base.data["unfiltered_count"] = self.unfiltered_count
        return base

class SemanticFieldViewSet(mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           generics.ListAPIView,
                           viewsets.GenericViewSet):
    queryset = SemanticField.objects.all().order_by("path")
    serializer_class = SemanticFieldSerializer
    pagination_class = SemanticFieldPagination
    lookup_field = "pk"

    permission_classes = (permissions.IsAuthenticatedOrReadOnly, )
    renderer_classes = (
        renderers.JSONRenderer, SemanticFieldHTMLRenderer, FormRenderer)
    parser_classes = (parsers.FormParser, )
    filter_backends = (SemanticFieldFilter, )

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()

        fields = self.request.GET.get("fields", None)
        if fields is not None:
            fields = fields.split(",")
            kwargs["fields"] = fields

        depths = {key[7:]: int(value) for (key, value) in
                  self.request.GET.iteritems() if key.startswith("depths.")}
        if len(depths):
            kwargs["depths"] = depths

        kwargs["unpublished"] = self.request.user.can_author
        return serializer_class(context={"request": self.request},
                                *args, **kwargs)

    @property
    def paginator(self):
        # We want a paginator only if we are doing a search.
        search = self.request.GET.get('search', None)
        if search is None:
            return None
        return super(SemanticFieldViewSet, self).paginator

    @never_cache
    def retrieve(self, request, *args, **kwargs):
        if request.accepted_renderer.media_type == "text/html":
            return Response({'instance': self.get_object()})

        return super(SemanticFieldViewSet, self) \
            .retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        """
        We support multiple arguments for listing semantic fields.

        Exact fields
        ============

        You can use one of:

        * ``paths`` with a semi-colon separated list of paths to retrieve.

        * ``ids`` with a semi-colon separated list of ids to retreive.

        Searching
        =========

        Searching is mutually exclusive with returning exact
        fields. You must use ``search``, ``aspect``, ``scope``:

        * ``search`` is the search text

        * ``aspect`` is where to search:

          + ``sf`` the semantic field headings

          + ``lexemes`` the lexemes

        * ``scope`` is the scope of the search:

          + ``all`: all semantic fields

          + ``hte`: only the fields from the HTE

          + ``btw``: only the fields created for BTW

        Pagination
        ==========

        When using ``search``, pagination is turned on. You can set
        pagination parameters with ``limit`` and ``offset``. ``limit``
        indicates how many records to return, ``offset`` indicates
        where to start in the set of results.  When paging is turned
        on, the results are returned as a dictionary containing:

        * ``count``: the number of matching results,

        * ``next`` and ``previous``: URLs to the next and previous set
          of results,

        * ``results`` an array of results.

        * ``unfiltered_count``: the total count of records that exist,
          ignoring filtering.

        When paging is off (not searching), the results are just an
        array of matching records.

        Selecting Fields
        ================

        You can reduce or expand the set of returned fields by using
        the ``fields`` parameter, which is a comma separated list of
        field names or field sets. The field sets exist:

        * The default: ``url``, ``path``, ``heading``, ``is_subcat``,
          ``verbose_pos``

        * The ``@search`` field set: ``parent``, ``related_by_pos``

        * The ``@details`` field set: ``parent``, ``related_by_pos``,
          ``lexemes``, ``children``

        See
        `:class:semantic_fields.serializers.SemanticFieldSerializer`
        for the full syntax.

        Depths of Relations
        ===================

        Using ``depths.<fieldname>`` allows to set a depth of
        expansion when following relationships. For instance without
        any specified ``depth``, the ``parent`` relation would be
        serialized as a URL to the parent. With ``depths.parent=1`` it
        would be realized as a serialization of the parent and the
        parent would itself contain a URL to its own
        parent. ``depths.parent=-1`` makes the depth infinite.

        ..warning:: Be careful when setting an infinite depth, as it
                    could cause an enormous amount of queries.
        """
        saved_method = request.method
        request.method = "POST"
        request.csrf_processing_done = False
        reason = CsrfViewMiddleware().process_view(request, None, (), {})
        request.method = saved_method

        if reason:
            return reason

        # If not specified, we use the JSON renderer.
        if request.META.get("HTTP_ACCEPT", None) is None:
            request.accepted_renderer = renderers.JSONRenderer()

        # And we can return only JSON.
        if request.accepted_renderer.media_type != "application/json":
            raise NotAcceptable

        # We have to check that these are set *here* because there's
        # nowhere else to check for them. The filter cannot do it.
        paths = request.GET.get('paths', None)
        ids = request.GET.get('ids', None)
        search = request.GET.get('search', None)

        if paths is None and ids is None and search is None:
            return HttpResponseBadRequest(
                "paths or ids or search must be specified")

        complex_paths = set()
        if paths is not None:
            # This interface accepts queries on semantic field
            # *expressions*. To perform such search, we split any
            # expression in its constituent parts and pass that to the
            # search. We then build "fake" semantic fields that we
            # return.
            paths = set(paths.split(";"))
            cleaned = set()
            for path in paths:
                try:
                    refs = parse_local_references(path)
                except FailedParse:
                    continue

                cleaned |= set(unicode(ref) for ref in refs)
                if len(refs) > 1:
                    complex_paths.add(path)

            if len(complex_paths) > 0:
                request.GET = request.GET.copy()  # Make it mutable.
                request.GET["paths"] = ";".join(cleaned)

        ret = super(SemanticFieldViewSet, self).list(request, *args, **kwargs)

        if len(complex_paths) > 0:
            # The return value is a response to the modified `paths`
            # we created. We need to modify it:
            #
            # a) to remove those semantic fields that are *only* the
            # result of breaking down a complex expression, and
            #
            # b) to add the result of complex expressions.

            # First, we add.
            sf_by_path = {sf["path"]: sf for sf in ret.data}
            for path in complex_paths:
                try:
                    refs = parse_local_references(path)
                except FailedParse:
                    continue
                combined = self.get_serializer(
                    make_specified_sf([sf_by_path[unicode(ref)] for ref in
                                       refs]))
                sf_by_path[path] = combined.data

            # This filters out what we need to remove.
            ret.data = [sf for path, sf in sf_by_path.iteritems()
                        if path in paths]

        return ret

    @detail_route(methods=['get'], url_path="edit-form")
    def edit_form(self, request, *args, **kwargs):
        if not request.user.can_change_semantic_fields:
            raise PermissionDenied

        # The default content type for add_child_form, if unspecified
        # is application/x-form.
        if request.META.get("HTTP_ACCEPT", None) is None:
            request.accepted_renderer = FormRenderer()

        if request.accepted_renderer.media_type == "application/x-form":
            form = SemanticFieldForm(title="Edit Heading",
                                     initial={
                                         "heading": self.get_object().heading,
                                     },
                                     class_prefix="edit-field",
                                     possible_poses=())
            return Response({'form': form}, content_type="text/html")

        raise NotAcceptable

    @list_route(methods=['get'], url_path="add-form")
    def add_form(self, request, pk=None, relation=None):
        if not request.user.can_add_semantic_fields:
            raise PermissionDenied

        # The default content type for add_child_form, if unspecified
        # is application/x-form.
        if request.META.get("HTTP_ACCEPT", None) is None:
            request.accepted_renderer = FormRenderer()

        if request.accepted_renderer.media_type == "application/x-form":
            title = {
                RELATED_BY_POS: "New Sibling",
                CHILD: "New Child",
                None: "New Semantic Field"
            }[relation]

            possible_poses = \
                SemanticField.objects.get(id=pk).possible_new_poses \
                if relation is RELATED_BY_POS else None

            form = SemanticFieldForm(title=title,
                                     submit_text="Create",
                                     class_prefix="add-child",
                                     possible_poses=possible_poses)
            return Response({'form': form}, content_type="text/html")

        raise NotAcceptable

    @detail_route(methods=['get'], url_path='add-child-form')
    def add_child_form(self, request, pk, *args, **kwargs):
        return self.add_form(request, relation=CHILD, *args, **kwargs)

    @detail_route(methods=['post'], url_path='children')
    def add_child(self, request, *args, **kwargs):
        if not request.user.can_add_semantic_fields:
            raise PermissionDenied

        form = SemanticFieldForm(request.data)
        if form.is_valid():
            parent = self.get_object()
            try:
                parent.make_child(form.cleaned_data["heading"],
                                  form.cleaned_data["pos"])
                return Response()
            except ValueError as ex:
                form.add_error(None, forms.ValidationError(ex))

        # The data was invalid... return the errors in a format
        # appropriate to the request.
        if request.accepted_renderer.media_type == "application/x-form":
            return Response({'form': form}, content_type="text/html",
                            status=400)

        raise serializers.ValidationError(form.errors)

    @detail_route(methods=['get'], url_path='add-related-by-pos-form')
    def add_related_by_pos_form(self, request, pk, *args, **kwargs):
        return self.add_form(request, pk, relation=RELATED_BY_POS,
                             *args, **kwargs)

    @detail_route(methods=['post'], url_path='related-by-pos')
    def add_related_by_pos(self, request, *args, **kwargs):
        if not request.user.can_add_semantic_fields:
            raise PermissionDenied

        form = SemanticFieldForm(request.data)
        if form.is_valid():
            parent = self.get_object()
            try:
                parent.make_related_by_pos(form.cleaned_data["heading"],
                                           form.cleaned_data["pos"])
                return Response()
            except ValueError as ex:
                form.add_error(None, forms.ValidationError(ex))

        # The data was invalid... return the errors in a format
        # appropriate to the request.
        if request.accepted_renderer.media_type == "application/x-form":
            return Response({'form': form}, content_type="text/html",
                            status=400)

        raise serializers.ValidationError(form.errors)

    def create(self, request, *args, **kwargs):
        if not request.user.can_add_semantic_fields:
            raise PermissionDenied

        form = SemanticFieldForm(request.data)
        if form.is_valid():
            try:
                SemanticField.objects.make_field(form.cleaned_data["heading"],
                                                 form.cleaned_data["pos"])
                return Response()
            except ValueError as ex:
                form.add_error(None, forms.ValidationError(ex))

        # The data was invalid... return the errors in a format
        # appropriate to the request.
        if request.accepted_renderer.media_type == "application/x-form":
            return Response({'form': form}, content_type="text/html",
                            status=400)

        raise serializers.ValidationError(form.errors)

    def update(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not request.user.can_change_semantic_fields:
            raise PermissionDenied

        # Anything not specified in the request is going to be
        # unchanged.  But to get the tests working, we want to
        # initialize to the unchanged value here.
        initial = request.data.copy()
        semantic_field = self.get_object()
        for field in ("heading", "pos"):
            if field not in initial:
                initial[field] = getattr(semantic_field, field)

        form = SemanticFieldForm(initial)
        if form.is_valid():
            try:
                if semantic_field.pos != form.cleaned_data["pos"]:
                    raise ValueError(
                        "it is not possible to change the part of speech "
                        "of a field after creation")
                semantic_field.heading = form.cleaned_data["heading"]
                semantic_field.save()
                return Response()
            except ValueError as ex:
                form.add_error(None, forms.ValidationError(ex))

        # The data was invalid... return the errors in a format
        # appropriate to the request.
        if request.accepted_renderer.media_type == "application/x-form":
            return Response({'form': form}, content_type="text/html",
                            status=400)

        raise serializers.ValidationError(form.errors)
