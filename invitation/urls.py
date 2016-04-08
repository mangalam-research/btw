from django.conf.urls import url
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    url(r'^invite/$', views.invite, name='invitation_invite'),
    url(r'^invite/complete/$',
        TemplateView.as_view(
            template_name='invitation/invitation_complete.html'),
        name='invitation_complete'),
    url(r'^use/(?P<key>\w+)/$', views.use, name='invitation_use'),
]
