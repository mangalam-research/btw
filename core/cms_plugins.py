import os

from cms.plugin_pool import plugin_pool
from cmsplugin_iframe.cms_plugins import IframePlugin
from django.conf import settings
from django.utils.translation import ugettext as _
from filer.settings import FILER_STATICMEDIA_PREFIX


class MyIframePlugin(IframePlugin):
    text_enabled = True

    def icon_src(self, instance):
        return os.path.normpath("%s/icons/video_%sx%s.png" %
                                (FILER_STATICMEDIA_PREFIX, 32, 32,))

plugin_pool.unregister_plugin(IframePlugin)
plugin_pool.register_plugin(MyIframePlugin)
