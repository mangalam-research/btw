from django.conf.urls import patterns, include, url
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', 'django.contrib.auth.views.login', name="login"),
    url(r'^logout/$', 'core.views.logout', name="logout"),
    url(r'^lexicography/', include('lexicography.urls')),
    url(r'^bibliography/', include('bibliography.urls'))
)


if settings.DEBUG:
    # In debug mode we do not want any static files to be cached
    from django.contrib.staticfiles.views import serve
    from django.views.decorators.cache import never_cache

    static_view = never_cache(serve)
    urlpatterns += patterns('',
                            url(r'^static/(?P<path>.*)$', static_view),
                            # We want the test app to be routed too
                            url(r'^test/', include('btw_test.urls')),
                            )
