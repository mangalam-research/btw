from django.conf.urls.defaults import *

urlpatterns = patterns(
    'zotero.views',
    url(r'^$', 'main'),
    url(r'^search$', 'search'),
    url(r'^associate$', 'associate'),
)
