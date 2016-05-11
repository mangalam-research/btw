from django_datatables_view.base_datatable_view import BaseDatatableView
from django.utils.html import mark_safe
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from django import forms
from django.views.decorators.cache import never_cache
from rest_framework import viewsets, mixins, renderers, parsers, permissions
from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import NotAcceptable
from rest_framework import serializers

from .models import SemanticField
from .serializers import SemanticFieldSerializer
from .forms import SemanticFieldForm

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

RELATED_BY_POS = "related_by_pos"
CHILD = "child"

class SemanticFieldViewSet(mixins.RetrieveModelMixin,
                           mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    queryset = SemanticField.objects.all()
    serializer_class = SemanticFieldSerializer
    lookup_field = "pk"

    permission_classes = (permissions.IsAuthenticated, )
    renderer_classes = (
        renderers.JSONRenderer, SemanticFieldHTMLRenderer, FormRenderer)
    parser_classes = (parsers.FormParser, )

    @never_cache
    def retrieve(self, request, *args, **kwargs):
        if request.accepted_renderer.media_type == "text/html":
            return Response({'instance': self.get_object()})

        return super(SemanticFieldViewSet, self) \
            .retrieve(request, *args, **kwargs)

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
                                     possible_poses=possible_poses)
            return Response({'form': form}, content_type="text/html")

        raise NotAcceptable

    @detail_route(methods=['get'], url_path='add-child-form')
    def add_child_form(self, request, pk, *args, **kwargs):
        return self.add_form(request, relation=CHILD, *args, **kwargs)

    @detail_route(methods=['post'], url_path='children')
    def add_child(self, request, pk, *args, **kwargs):
        if not request.user.can_add_semantic_fields:
            raise PermissionDenied

        form = SemanticFieldForm(request.data)
        if form.is_valid():
            parent = SemanticField.objects.get(id=pk)
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
    def add_related_by_pos(self, request, pk, *args, **kwargs):
        if not request.user.can_add_semantic_fields:
            raise PermissionDenied

        form = SemanticFieldForm(request.data)
        if form.is_valid():
            parent = SemanticField.objects.get(id=pk)
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
