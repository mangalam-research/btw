from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

from .cms_menus import SemanticFieldsMenu

class SemanticFieldsApp(CMSApp):
    name = _("Semantic Fields")
    urls = ["semantic_fields.urls"]
    menus = [SemanticFieldsMenu]

apphook_pool.register(SemanticFieldsApp)
