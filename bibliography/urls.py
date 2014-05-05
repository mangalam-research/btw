from django.conf.urls import patterns, url
from django.conf import settings

from .views import ItemTable

urlpatterns = patterns('bibliography.views',
                       url(r'^search/$', 'search', name='bibliography_search'),
                       url(r'^manage/$', 'manage', {'editable': True},
                           name='bibliography_manage'),
                       url(r'^(?P<pk>.+?)/abbrev/$', 'abbrev',
                           name='bibliography_abbrev'),
                       url(r'^(?P<pk>.+?)/info/$', 'info',
                           name='bibliography_info'),
                       url(r'^item-table/$', ItemTable.as_view(),
                           name='bibliography_item_table'),
                       url(r'^(?P<pk>.+?)/primary-sources/new$',
                           'new_primary_sources',
                           name='bibliography_new_primary_sources'),
                       url(r'^(?P<pk>.+?)/primary-sources$',
                           'item_primary_sources',
                           name='bibliography_item_primary_sources'),
                       url(r'^primary-sources/(?P<pk>.+?)$',
                           'primary_sources',
                           name='bibliography_primary_sources'),)
