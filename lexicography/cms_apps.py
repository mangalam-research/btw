from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

from .cms_menus import LexicographyMenu

class LexicographyApp(CMSApp):
    name = _("Lexicography")

    def get_urls(self, page=None, language=None, **kwargs):
        return ["lexicography.urls"]

    def get_menus(self, page=None, language=None, **kwargs):
        return [LexicographyMenu]

apphook_pool.register(LexicographyApp)
