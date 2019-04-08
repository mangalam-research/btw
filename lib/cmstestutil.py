import sys
from cms.api import create_page

def refresh_cms_apps():
    from cms.appresolver import clear_app_resolvers
    clear_app_resolvers()

    from django.urls import clear_url_caches
    clear_url_caches()

    from django.conf import settings
    url_modules = ['cms.urls', settings.ROOT_URLCONF]
    for module in url_modules:
        if module in sys.modules:
            del sys.modules[module]

def create_test_page(*args, **kwargs):
    page = create_page(*args, **kwargs)
    page.toggle_in_navigation()
    page.publish('en-us')
    return page

def create_stock_test_pages():
    pages = {}
    home = pages["home_page"] = create_test_page("Home", "generic_page.html",
                                                 "en-us")
    home.set_as_homepage(True)
    pages["lexicography_page"] = \
        create_test_page("Lexicography", "generic_page.html",
                         "en-us", apphook='LexicographyApp')
    pages["bibliography_page"] = \
        create_test_page("Bibliography", "generic_page.html",
                         "en-us", apphook='BibliographyApp')

    return pages
