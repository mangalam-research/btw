from django.conf.urls import patterns, url
from django.views.decorators.cache import never_cache

from .views import ItemTable, ItemViewSet, AllListView

urlpatterns = patterns('bibliography.views',
                       url(r'^search/$', 'search', name='bibliography_search'),
                       url(r'^manage/$', 'manage', name='bibliography_manage'),
                       url(r"^initiate-refresh/$", "initiate_refresh",
                           name="bibliography_initiate_refresh"),
                       url(r"^check-refresh/$", "check_refresh",
                           name="bibliography_check_refresh"),
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
                           name='bibliography_primary_sources'),
                       url(r'^all$',
                           never_cache(AllListView.as_view()),
                           name="bibliography_all"),
                       url(r'^(?P<pk>.+?)$',
                           never_cache(ItemViewSet.as_view(
                               {'get': 'retrieve'})),
                           name='bibliography_items'),
                       url(r'^$',
                           never_cache(ItemViewSet.as_view(
                               {'get': 'list'})),
                           name="bibliography_items_list"),
                       )
