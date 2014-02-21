from django.conf.urls import patterns, url
from django.views.generic import TemplateView

urlpatterns = patterns(
    'invitation.views',
    url(r'^invite/$', "invite", name='invitation_invite'),
    url(r'^invite/complete/$',
        TemplateView.as_view(
            template_name='invitation/invitation_complete.html'),
        name='invitation_complete'),
    url(r'^use/(?P<key>\w+)/$', "use", name='invitation_use'),
)
