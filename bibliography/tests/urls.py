from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns

from btw.urls import urlpatterns
urlpatterns = i18n_patterns(
    url(r"^bibliography/", include('bibliography.urls')),
) + urlpatterns
