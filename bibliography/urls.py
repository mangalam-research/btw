from django.conf.urls import patterns, url
from django.conf import settings

from .views import ItemList

urlpatterns = patterns('bibliography.views',
                       url(r'^search/$', 'search', name='bibliography_search'),
                       url(r'^title/$', 'title', {'editable': True},
                           name='bibliography_title'),
                       url(r'^(?P<itemKey>.+?)/abbrev/$', 'abbrev',
                           name='bibliography_abbrev'),
                       url(r'^(?P<itemKey>.+?)/info/$', 'info',
                           name='bibliography_info'),
                       url(r'^title-table/$', ItemList.as_view(),
                           name='bibliography_title_table'),
                       url(r'^(?P<itemKey>.+?)/reference-title/$',
                           'reference_title',
                           name='bibliography_reference_title'),)
