from django.conf.urls import patterns, url
from django.conf import settings

urlpatterns = patterns(
    'lexicography.views',
    url(r'^$', 'main', name='lexicography_main'),
    url(r'^search$', 'search'),
    url(r'^collect$', 'collect'),
    url(r'^entry/(?P<entry_id>\d+)/$', 'entry_details',
        name='lexicography_entry_details'),
    url(r'^entry/(?P<entry_id>\d+)/update$', 'entry_update',
        name="lexicography_entry_update"),
    url(r'^handle/(?P<handle_or_entry_id>.+)/update$', 'handle_update',
        name='lexicography_handle_update'),
    url(r'^handle/(?P<handle_or_entry_id>.+)/save$', 'handle_save',
        name='lexicography_handle_save'),
    url(r'^change/(?P<change_id>\d+)/revert$', 'change_revert',
        name="lexicography_change_revert"),

    url(r'^entry/new$', 'entry_new', name='lexicography_entry_new'),
    url(r'^log$', 'log', name='lexicography_log'),
)

if settings.DEBUG:
    urlpatterns += patterns(
        'lexicography.views',
        url(r'^editing_data$', 'editing_data'),
    )

# These are views used only in testing.
if settings.BTW_TESTING:
    urlpatterns += patterns(
        'lexicography.views',
        url(r'^handle/(?P<handle_or_entry_id>.+)/mod$',
            'handle_background_mod',
            name='lexicography_handle_background_mod'),
    )
