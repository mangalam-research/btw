from django.conf.urls import patterns, url

urlpatterns = patterns(
    'core.views',
    url(r'^mods$', 'mods', name='core_mods')
)
