from django.views.decorators.cache import never_cache
from django.conf.urls import url

from . import views

urlpatterns = [
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
