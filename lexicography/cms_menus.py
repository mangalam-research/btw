from menus.base import NavigationNode
from menus.menu_pool import menu_pool
from django.utils.translation import ugettext_lazy as _
from cms.menu_bases import CMSAttachMenu
from django.core.urlresolvers import reverse

class LexicographyMenu(CMSAttachMenu):

    name = _("Lexicography")

    def get_nodes(self, request):
        nodes = [
            NavigationNode(
                "Search",
                reverse("lexicography_main"),
                1
            )
        ]
        if request.user.has_perm("lexicography.add_entry"):
            nodes.append(NavigationNode(
                "New Entry",
                reverse("lexicography_entry_new"),
                2,
                #
                # We do not use this. This would allow the "New Entry"
                # menu item to appear selected when a user is creating
                # a new entry. However, this would also cause editing
                # any article to make "New Entry" selected.
                #
                # attr={
                #  'redirect_url': reverse("lexicography_entry_new")
                # }
            ))

        return nodes

menu_pool.register_menu(LexicographyMenu)
