from django.conf.urls.defaults import *
from django.views.generic.edit import CreateView, UpdateView

from views import SaveForm, RawSaveForm, UpdateEntryView
from models import Entry
from btw import settings

urlpatterns = patterns(
    'lexicography.views',
    url(r'^$', 'main'),
    url(r'^search$', 'search'),
    url(r'^(?P<entry_id>\d+)/$', 'details', 
        name='lexicography-details'),
    url(r'^(?P<entry_id>\d+)/log$', 'log', name='lexicography-log'),
    )

if settings.DEBUG:
    urlpatterns += patterns(
        'lexicography.views',
        url(r'^editing_data$', 'editing_data'),
        )

urlpatterns += patterns(
    '',
    url(r'^new$', 
        CreateView.as_view(form_class=SaveForm, 
                           template_name="lexicography/new.html"), 
        name="lexicography-new"),

    url(r'^(?P<pk>\d+)/update$', 
        UpdateEntryView.as_view(model=Entry, form_class=SaveForm, 
                           template_name='lexicography/new.html'),
        name="lexicography-update"),

    url(r'^(?P<pk>\d+)/raw_update$', 
        UpdateView.as_view(model=Entry, form_class=RawSaveForm, 
                           template_name='lexicography/new.html'),
        name="lexicography-rawupdate"),
    )

        
