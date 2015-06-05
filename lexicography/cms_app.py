from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

from .menu import LexicographyMenu

class LexicographyApp(CMSApp):
    name = _("Lexicography")
    urls = ["lexicography.urls"]
    menus = [LexicographyMenu]

apphook_pool.register(LexicographyApp)
