from django.conf.urls import patterns, url
from django.conf import settings

urlpatterns = patterns('bibsearch.views',
                       url(r'^$', 'search', name='search'),
                       url(r'^exec/$', 'exec_', name='exec'),
                       url(r'^results/$', 'results', name='results'),
                       url(r'^(?P<itemKey>.+?)/abbrev/$', 'abbrev', name='abbrev'),
                       url(r'^(?P<itemKey>.+?)/info/$', 'info', name='info'),
                       url(r'^sync/$', 'sync', name='sync'),)

# tests views are only made available during development
if settings.DEBUG:
    urlpatterns += patterns('bibsearch.views',
                            url(r'^tests/', 'testjs', name='testjs'),)
