from django.conf.urls.defaults import *
from django.views.generic import TemplateView

urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(template_name="btw_test/test.html")),
    )
