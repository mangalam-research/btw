from django.conf.urls import patterns, url
from django.conf import settings

# patterns defined for search url
from .views import search, results, sync, testjs

urlpatterns = patterns('',
                       url(r'^$', search, name='search'),
                       url(r'^results/', results, name='results'),
                       url(r'^sync/', sync, name='sync'),)

# tests views are only made available during development
if settings.DEBUG:
    urlpatterns += patterns('', url(r'^tests/', testjs, name='testjs'),)
