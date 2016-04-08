from django.conf.urls import url
from django.conf import settings

from . import views

urlpatterns = [
    url(r'^$', views.main, name='lexicography_main'),
    url(r'^collect$', views.collect),
    url(r'^entry/(?P<entry_id>\d+)(?:/(?P<changerecord_id>\d+))?/$',
        views.entry_details,
        name='lexicography_entry_details'),
    url(r'^entry/(?P<entry_id>\d+)(?:/(?P<changerecord_id>\d+))?/mods$',
        views.mods, name='lexicography_entry_mods'),
    url(r'^changerecord/(?P<changerecord_id>\d+)/$',
        views.changerecord_details, name='lexicography_changerecord_details'),
    url(r'^changerecord/(?P<changerecord_id>\d+)/publish$',
        views.changerecord_publish, name='lexicography_changerecord_publish'),
    url(r'^changerecord/(?P<changerecord_id>\d+)/unpublish$',
        views.changerecord_unpublish,
        name='lexicography_changerecord_unpublish'),
    url(r'^entry/(?P<entry_id>\d+)/update$', views.entry_update,
        name="lexicography_entry_update"),
    url(r'^handle/(?P<handle_or_entry_id>.+)/update$', views.handle_update,
        name='lexicography_handle_update'),
    url(r'^handle/(?P<handle_or_entry_id>.+)/save$', views.handle_save,
        name='lexicography_handle_save'),
    url(r'^change/(?P<change_id>\d+)/revert$', views.change_revert,
        name="lexicography_change_revert"),
    url(r'^search-table/$', views.SearchTable.as_view(),
        name='lexicography_search_table'),

    url(r'^entry/new$', views.entry_new, name='lexicography_entry_new'),
    url(r'^log$', views.log, name='lexicography_log'),
]

if settings.DEBUG:
    urlpatterns += [
        url(r'^editing_data$', views.editing_data),
    ]

# These are views used only in testing.
if settings.BTW_TESTING:
    urlpatterns += [
        url(r'^handle/(?P<handle_or_entry_id>.+)/mod$',
            views.handle_background_mod,
            name='lexicography_handle_background_mod'),
        url(r'^entry/(?P<lemma>.+)/testing-mark-valid$',
            views.entry_testing_mark_valid,
            name='lexicography_entry_testing_mark_valid')
    ]
