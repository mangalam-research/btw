from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

from .cms_menus import SemanticFieldsMenu

class SemanticFieldsApp(CMSApp):
    name = _("Semantic Fields")

    def get_urls(self, page=None, language=None, **kwargs):
        return ["semantic_fields.urls"]

    def get_menus(self, page=None, language=None, **kwargs):
        return [SemanticFieldsMenu]

apphook_pool.register(SemanticFieldsApp)
