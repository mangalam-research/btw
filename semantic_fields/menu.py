from menus.menu_pool import menu_pool
from django.utils.translation import ugettext_lazy as _
from cms.menu_bases import CMSAttachMenu

class SemanticFieldsMenu(CMSAttachMenu):

    name = _("Semantic Fields")

    def get_nodes(self, request):
        return []

menu_pool.register_menu(SemanticFieldsMenu)
