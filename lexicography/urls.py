from django.conf.urls.defaults import *
from lib.generic import LoginRequiredCreateView, LoginRequiredUpdateView

from views import SaveForm
from models import Entry
from btw import settings

urlpatterns = patterns(
    'lexicography.views',
    url(r'^$', 'main'),
    url(r'^search$', 'search'),
    url(r'^(?P<entry_id>\d+)/$', 'details', name='lexicography-details'),
    url(r'^(?P<entry_id>\d+)/update$', 'update', name="lexicography-update"),
    url(r'^(?P<entry_id>\d+)/raw_update$', 'raw_update',
        name="lexicography-rawupdate"),

    url(r'^log$', 'log', name='lexicography-log'),
    )

if settings.DEBUG:
    urlpatterns += patterns(
        'lexicography.views',
        url(r'^editing_data$', 'editing_data'),
        )

urlpatterns += patterns(
    '',
    url(r'^new$',
        LoginRequiredCreateView.as_view(form_class=SaveForm,
                                        template_name="lexicography/new.html"),
        name="lexicography-new"),

    )
