from django.conf.urls import url
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

from lib.util import ajax_login_required
from . import views

urlpatterns = [
    url(r'^$',
        login_required(
            TemplateView.as_view(template_name='semantic_fields/main.html')),
        name='semantic_fields_main'),
    url(r'^search-table/$', ajax_login_required(views.SearchTable.as_view()),
        name='semantic_fields_table'),
]
