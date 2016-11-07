from django.contrib import admin

from django.conf.urls import include, url
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from allauth.account.views import login, logout

from lib.admin import limited_admin_site
from .views import ping

admin.autodiscover()

urlpatterns = i18n_patterns(
    url(r'^admin/', limited_admin_site.urls),
    url(r'^full-admin/', admin.site.urls),
    url(r'^login/$', login, name="login"),
    url(r'^logout/$', logout, name="logout"),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^invitation/', include('invitation.urls')),
    url(r'^full-admin/doc/', include('django.contrib.admindocs.urls')),
)

urlpatterns += [
    url(r'^rest/semantic_fields/', include("semantic_fields.rest_urls")),
    url(r'^rest/bibliography/', include("bibliography.rest_urls")),
]


# These have to be inserted before the CMS pattern.
if settings.DEBUG and settings.BTW_DIRECT_APP_MODE:
    urlpatterns += i18n_patterns(
        url(r'^lexicography/', include('lexicography.urls')),
        url(r'^bibliography/', include('bibliography.urls')),
    )

if settings.DEBUG or settings.BTW_TESTING:
    # In production, the nginx server should be responsible for
    # returning a response.
    urlpatterns += [
        url(r'^ping$', ping)
    ]

urlpatterns += i18n_patterns(
    url(r'^core/', include('core.urls')),
    url(r'^', include('cms.urls')),
) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

    # In debug mode we do not want any static files to be cached
    from django.contrib.staticfiles.views import serve
    from django.views.decorators.cache import never_cache

    static_view = never_cache(serve)
    urlpatterns += [
        url(r'^static/(?P<path>.*)$', static_view),
        # We want the test app to be routed too
        url(r'^test/', include('btw_test.urls')),
    ]
