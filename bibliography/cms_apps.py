from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

from .cms_menus import BibliographyMenu

class BibliographyApp(CMSApp):
    name = _("Bibliography")

    def get_urls(self, page=None, language=None, **kwargs):
        return ["bibliography.urls"]

    def get_menus(self, page=None, language=None, **kwargs):
        return [BibliographyMenu]

apphook_pool.register(BibliographyApp)
