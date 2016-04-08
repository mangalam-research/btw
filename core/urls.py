from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^mods$', views.mods, name='core_mods')
]
