from menus.base import NavigationNode
from menus.menu_pool import menu_pool
from django.utils.translation import ugettext_lazy as _
from cms.menu_bases import CMSAttachMenu
from django.core.urlresolvers import reverse

class BibliographyMenu(CMSAttachMenu):

    name = _("Bibliography")

    def get_nodes(self, request):
        nodes = [
            NavigationNode(
                "General Search",
                reverse("bibliography_search"),
                1
            )
        ]
        if request.user.has_perm("bibliography.add_primarysource") and \
           request.user.has_perm("bibliography.change_primarysource"):
            nodes.append(NavigationNode(
                "Manage",
                reverse("bibliography_manage"),
                2
            ))

        return nodes

menu_pool.register_menu(BibliographyMenu)
