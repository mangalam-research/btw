from django.conf.urls import patterns, url
from btw import settings

urlpatterns = patterns(
    'lexicography.views',
    url(r'^$', 'main', name='main'),
    url(r'^search$', 'search'),
    url(r'^collect$', 'collect'),
    url(r'^entry/(?P<entry_id>\d+)/$', 'entry_details', name='entry_details'),
    url(r'^entry/(?P<entry_id>\d+)/update$', 'entry_update',
        name="entry_update"),
    url(r'^handle/(?P<handle>.+)/save$', 'handle_save', name='handle_save'),
    url(r'^entry/(?P<entry_id>\d+)/raw_update$', 'entry_raw_update',
        name="entry_rawupdate"),
    url(r'^change/(?P<change_id>\d+)/revert$', 'change_revert',
        name="change_revert"),

    url(r'^entry/new$', 'entry_new', name='entry_new'),
    #LoginRequiredCreateView.as_view(form_class=SaveForm,
    # template_name="lexicography/new.html"),
    url(r'^log$', 'log', name='log'),
    )

if settings.DEBUG:
    urlpatterns += patterns(
        'lexicography.views',
        url(r'^editing_data$', 'editing_data'),
        )
