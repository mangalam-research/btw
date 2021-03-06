from django.apps import AppConfig
from django.core.checks import Error, register, Tags

@register(Tags.security)
def no_csrf_cookie_httponly(app_configs, **kwargs):
    errors = []
    from django.conf import settings
    if settings.CSRF_COOKIE_HTTPONLY:
        errors.append(
            Error(
                'BTW cannot work with CSRF_COOKIE_HTTPONLY set to True. '
                'It only makes attacks somewhat harder, whereas the '
                'BTW\'s JavaScript code needs to get the CSRF token, and '
                'getting it from a cookie is the easiest way.',
                id='core.E001'
            )
        )
    return errors

# We cannot execute the following code at module loading time. Hence
# the function.
def ready():
    from menus.base import Modifier
    from menus.menu_pool import menu_pool

    class SelectedModifier(Modifier):

        """
        This modifier is designed so that if a parent node and a
        descendant of a node point to the same URL, then the deepest
        descendant that point to the URL is the one that is going to be
        selected.

        The default behavior of Django CMS is to select the first node
        that matches a URL.

        Note that this code probably won't behave well if siblings match
        the same URL.
        """

        def modify(self, request, nodes, namespace, root_id, post_cut,
                   breadcrumb):
            sels = [node for node in nodes if node.selected]

            #
            # This block is here only to deal with this issue:
            #
            # https://github.com/divio/django-cms/issues/4118
            #
            # and should be removed when the issue is fixed.
            #
            if not sels:
                # We do not mess with ancestor, descendant, etc. because
                # a) these have not been set yet, and b) they will be set
                # later.
                sel = None
                for node in nodes:
                    node.selected = False
                    if request.path.startswith(node.get_absolute_url()) and \
                       (not sel or len(node.get_absolute_url()) > len(
                           sel.get_absolute_url())):
                        sel = node

                if sel:
                    sel.selected = True
            # End of the block to remove when the issue is fixed.

            for sel in sels:
                url = sel.get_absolute_url()

                # All descendants of the node that match the url are
                # preliminary candidates.
                preliminary = [x for x in sel.get_descendants()
                               if x.get_absolute_url() == url]

                # Those that have any descendant among our preliminary set are
                # excluded.
                candidates = [x for x in preliminary
                              if not any([d for d in x.get_descendants()
                                          if d in preliminary])]

                if candidates:
                    sel.selected = False
                    candidates[0].selected = True

            return nodes

    import cms.cms_menus
    menu_pool.register_modifier(SelectedModifier)

    #
    # Override the default admin site so that all apps will register
    # their administration interfaces to the "full-admin" site. The
    # only people who can access the full-admin site are superusers.
    #
    # To allow staff to edit Django CMS pages, the Django CMS admin
    # models are registered to a limited site which sits at the usual
    # admin URL.
    #
    from django.contrib import admin
    from django.contrib.admin import sites

    class FullAdminSite(admin.AdminSite):

        def has_permission(self, request):
            return request.user.is_superuser

    mysite = FullAdminSite("full-admin")
    admin.site = mysite
    sites.site = mysite


class DefaultAppConfig(AppConfig):
    name = 'core'

    def ready(self):
        ready()
