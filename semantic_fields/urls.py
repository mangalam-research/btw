from django.conf.urls import patterns, url
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from rest_framework import routers

from lib.util import ajax_login_required
from .views import SearchTable, SemanticFieldViewSet

router = routers.SimpleRouter()
router.register(r'semanticfield', SemanticFieldViewSet,
                base_name="semantic_fields_semanticfield")

urlpatterns = patterns(
    'semantic_fields.views',
    url(r'^$',
        login_required(
            TemplateView.as_view(template_name='semantic_fields/main.html')),
        name='semantic_fields_main'),
    url(r'^search-table/$', ajax_login_required(SearchTable.as_view()),
        name='semantic_fields_table'),
) + router.urls
