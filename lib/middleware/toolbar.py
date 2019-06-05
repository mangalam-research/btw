from django import forms
from django.core.exceptions import ValidationError
from django.urls import resolve

from cms.middleware.toolbar import ToolbarMiddleware
from cms.utils.conf import get_cms_setting
from cms.utils.request_ip_resolvers import get_request_ip_resolver

get_request_ip = get_request_ip_resolver()

# See
# https://github.com/divio/django-cms/issues/6523
class CMSToolbarMiddleware(ToolbarMiddleware):

    def is_cms_request(self, request):
        toolbar_hide = get_cms_setting('TOOLBAR_HIDE')
        internal_ips = get_cms_setting('INTERNAL_IPS')

        if internal_ips:
            client_ip = get_request_ip(request)
            try:
                client_ip = forms.GenericIPAddressField().clean(client_ip)
            except ValidationError:
                return False
            else:
                if client_ip not in internal_ips:
                    return False

        if not toolbar_hide:
            return True

        try:
            match = resolve(request.path_info)
        except:
            return False

        return match.url_name in ('pages-root', 'pages-details-by-slug',
                                  'cms_page_add_plugin',
                                  'cms_page_edit_plugin')
