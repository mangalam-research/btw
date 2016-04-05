from menus.base import Menu, NavigationNode
from menus.menu_pool import menu_pool

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

class UserMenu(Menu):

    def get_nodes(self, request):
        ret = [
            NavigationNode(
                _("Log in"), reverse('login'), 1,
                attr={
                    'visible_for_authenticated': False,
                    'pull_right': True,
                }),
            NavigationNode(
                request.user.username, "", 2,
                attr={
                    'visible_for_anonymous': False,
                    'pull_right': True,
                })
        ]

        if request.user.is_superuser:
            ret.append(
                NavigationNode(
                    _("Administration"), reverse('full-admin:index'), 3, 2,
                    attr={'visible_for_anonymous': False})
            )

        ret.append(
            NavigationNode(
                _("Log out"), reverse('logout'), 4, 2,
                attr={'visible_for_anonymous': False}),
        )

        return ret

menu_pool.register_menu(UserMenu)
