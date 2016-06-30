from django_datatables_view.base_datatable_view import BaseDatatableView
from django.utils.html import mark_safe
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from django import forms
from django.views.decorators.cache import never_cache
from django.middleware.csrf import CsrfViewMiddleware
from django.http import HttpResponseBadRequest
from rest_framework import viewsets, mixins, renderers, parsers, permissions, \
    generics, filters
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import NotAcceptable
from rest_framework import serializers

from .models import SemanticField
from .serializers import SemanticFieldSerializer
from .forms import SemanticFieldForm
from .util import parse_local_references

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

        search_value = search_value.strip()

        if search_value == "":
            return SemanticField.objects.none()

        if search_value[0] == '"' and search_value[-1] == '"':
            exact = ""  # Exact field lookup
            search_value = search_value[1:-1]  # Dump the quotes!
        else:
            exact = "__icontains"  # Inexact field lookup

        field = {"sf": "heading",
                 "lexemes": "lexeme__searchword__searchword"}[aspect]

        if scope == "all":
            pass
        elif scope == "hte":
            qs = qs.filter(catid__isnull=False)
        elif scope == "btw":
            qs = qs.filter(catid__isnull=True)
        else:
            raise ValueError("unknown value for scope: " + scope)

        return qs.filter(**{field + exact: search_value})


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

    def filter_queryset(self, request, queryset, view):
        paths = request.GET.get('paths', None)
        ids = request.GET.get('ids', None)

        if paths is not None:
            queryset = queryset.filter(path__in=set(paths.split(";")))

        if ids is not None:
            queryset = queryset.filter(ids__in=set(ids.split(";")))

        return queryset


def make_specified_sf(path, fields):
    """
    Create a "fake" semantic field that is the product of a complex
    semantic field expression.
    """
    return SemanticField(path=path,
                         heading=" @ ".join(field["heading"] for field in
                                            fields))


RELATED_BY_POS = "related_by_pos"
CHILD = "child"


class SemanticFieldViewSet(mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           generics.ListAPIView,
                           viewsets.GenericViewSet):
    queryset = SemanticField.objects.all()
    serializer_class = SemanticFieldSerializer
    lookup_field = "pk"

    permission_classes = (permissions.IsAuthenticatedOrReadOnly, )
    renderer_classes = (
        renderers.JSONRenderer, SemanticFieldHTMLRenderer, FormRenderer)
    parser_classes = (parsers.FormParser, )
    filter_backends = (SemanticFieldFilter, )

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()

        scope = self.request.GET.get("scope",
                                     SemanticFieldSerializer.DEFAULT_SCOPE)

        kwargs["scope"] = scope
        kwargs["unpublished"] = self.request.user.can_author
        return serializer_class(*args, **kwargs)

    @never_cache
    def retrieve(self, request, *args, **kwargs):
        if request.accepted_renderer.media_type == "text/html":
            return Response({'instance': self.get_object()})

        return super(SemanticFieldViewSet, self) \
            .retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
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

        if paths is None and ids is None:
            return HttpResponseBadRequest("paths or ids must be specified")

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
                refs = parse_local_references(path)
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
                refs = parse_local_references(path)
                combined = self.get_serializer(
                    make_specified_sf(path,
                                      [sf_by_path[unicode(ref)] for ref in
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
