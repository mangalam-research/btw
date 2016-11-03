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
        name='bibliography_item_table')
]
