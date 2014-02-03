from django.conf.urls import patterns, url
from django.conf import settings

urlpatterns = patterns('bibliography.views',
                       url(r'^search/$', 'search', name='bibliography_search'),
                       url(r'^exec/$', 'exec_', name='bibliography_exec'),
                       url(r'^results/$', 'results',
                           name='bibliography_results'),
                       url(r'^(?P<itemKey>.+?)/abbrev/$', 'abbrev',
                           name='bibliography_abbrev'),
                       url(r'^(?P<itemKey>.+?)/info/$', 'info',
                           name='bibliography_info'),
                       url(r'^sync/$', 'sync', name='sync'),)

# tests views are only made available during development
if settings.DEBUG:
    urlpatterns += patterns('bibliography.views',
                            url(r'^tests/', 'testjs', name='testjs'),)
