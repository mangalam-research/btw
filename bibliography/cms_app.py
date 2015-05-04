from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

from .menu import BibliographyMenu

class BibliographyApp(CMSApp):
    name = _("Bibliography")
    urls = ["bibliography.urls"]
    menus = [BibliographyMenu]

apphook_pool.register(BibliographyApp)
