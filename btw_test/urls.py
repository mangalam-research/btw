from django.conf.urls import url
from django.views.generic import TemplateView

urlpatterns = [
    # Pylint generates a false positive on the next line of code.
    # pylint: disable=E1120
    url(r'^$', TemplateView.as_view(template_name="btw_test/test.html")),
]
