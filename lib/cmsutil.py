import sys

def refresh_cms_apps():
    from cms.appresolver import clear_app_resolvers
    clear_app_resolvers()

    from django.core.urlresolvers import clear_url_caches
    clear_url_caches()

    from django.conf import settings
    url_modules = ['cms.urls', settings.ROOT_URLCONF]
    for module in url_modules:
        if module in sys.modules:
            del sys.modules[module]
