from django.conf.urls import patterns, url
from btw import settings

urlpatterns = patterns(
    'lexicography.views',
    url(r'^$', 'main', name='main'),
    url(r'^search$', 'search'),
    url(r'^collect$', 'collect'),
    url(r'^(?P<entry_id>\d+)/$', 'details', name='details'),
    url(r'^(?P<entry_id>\d+)/update$', 'update', name="update"),
    url(r'^(?P<handle>.+)/save$', 'save', name='save'),
    url(r'^(?P<entry_id>\d+)/raw_update$', 'raw_update',
        name="rawupdate"),
    url(r'^(?P<change_id>\d+)/revert$', 'revert',
        name="revert"),

    url(r'^new$', 'new', name='new'),
    #LoginRequiredCreateView.as_view(form_class=SaveForm,
    # template_name="lexicography/new.html"),
    url(r'^log$', 'log', name='log'),
    )

if settings.DEBUG:
    urlpatterns += patterns(
        'lexicography.views',
        url(r'^editing_data$', 'editing_data'),
        )
