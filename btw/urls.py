from django.conf.urls import patterns, include, url
from django.conf import settings
from django.views.generic import TemplateView

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(template_name='main.html'), name="main"),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^login/$', 'allauth.account.views.login', name="login"),
    url(r'^logout/$', 'allauth.account.views.logout', name="logout"),
    url(r'^lexicography/', include('lexicography.urls')),
    url(r'^bibliography/', include('bibliography.urls')),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^invitation/', include('invitation.urls'))
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
