from django.contrib import admin

from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static

from lib.admin import limited_admin_site

admin.autodiscover()

urlpatterns = i18n_patterns(
    '',
    url(r'^admin/', include(limited_admin_site.urls)),
    url(r'^full-admin/', include(admin.site.urls)),
    url(r'^login/$', 'allauth.account.views.login', name="login"),
    url(r'^logout/$', 'allauth.account.views.logout', name="logout"),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^invitation/', include('invitation.urls')),
    url(r'^full-admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^', include('cms.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


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
