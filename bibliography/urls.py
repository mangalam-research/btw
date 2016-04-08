from django.conf.urls import url
from django.views.decorators.cache import never_cache

from . import views

urlpatterns = [
    url(r'^search/$', views.search, name='bibliography_search'),
    url(r'^manage/$', views.manage, name='bibliography_manage'),
    url(r"^initiate-refresh/$", views.initiate_refresh,
        name="bibliography_initiate_refresh"),
    url(r"^check-refresh/$", views.check_refresh,
        name="bibliography_check_refresh"),
    url(r'^item-table/$', views.ItemTable.as_view(),
        name='bibliography_item_table'),
    url(r'^(?P<pk>.+?)/primary-sources/new$', views.new_primary_sources,
        name='bibliography_new_primary_sources'),
    url(r'^(?P<pk>.+?)/primary-sources$', views.item_primary_sources,
        name='bibliography_item_primary_sources'),
    url(r'^primary-sources/(?P<pk>.+?)$', views.primary_sources,
        name='bibliography_primary_sources'),
    url(r'^all$', never_cache(views.AllListView.as_view()),
        name="bibliography_all"),
    url(r'^(?P<pk>.+?)$',
        never_cache(views.ItemViewSet.as_view({'get': 'retrieve'})),
        name='bibliography_items'),
    url(r'^$',
        never_cache(views.ItemViewSet.as_view({'get': 'list'})),
        name="bibliography_items_list"),
]
