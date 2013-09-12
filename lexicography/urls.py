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
    url(r'^handle/(?P<handle>.+)/update$', 'handle_update',
        name='lexicography_handle_update'),
    url(r'^handle/(?P<handle>.+)/save$', 'handle_save',
        name='lexicography_handle_save'),
    url(r'^entry/(?P<entry_id>\d+)/raw_update$', 'entry_raw_update',
        name="lexicography_entry_rawupdate"),
    url(r'^change/(?P<change_id>\d+)/revert$', 'change_revert',
        name="lexicography_change_revert"),

    url(r'^entry/new$', 'entry_new', name='lexicography_entry_new'),
    #LoginRequiredCreateView.as_view(form_class=SaveForm,
    # template_name="lexicography/new.html"),
    url(r'^log$', 'log', name='lexicography_log'),
)

if settings.DEBUG:
    urlpatterns += patterns(
        'lexicography.views',
        url(r'^editing_data$', 'editing_data'),
    )
