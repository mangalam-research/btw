import os
import datetime

from cms.plugin_pool import plugin_pool
from cmsplugin_iframe.cms_plugins import IframePlugin
from django.utils.translation import ugettext as _
from filer.settings import FILER_STATICMEDIA_PREFIX
from cms.plugin_base import CMSPluginBase
from cms.models.pluginmodel import CMSPlugin
from django.conf import settings

import lib.util as util


class MyIframePlugin(IframePlugin):
    text_enabled = True

    def icon_src(self, instance):
        return os.path.normpath("%s/icons/video_%sx%s.png" %
                                (FILER_STATICMEDIA_PREFIX, 32, 32,))

plugin_pool.unregister_plugin(IframePlugin)
plugin_pool.register_plugin(MyIframePlugin)

def format_names(names, reverse_first=False, maximum=None):
    ret = ""

    ix = 0
    name = names[0]

    if reverse_first:
        ret += name["surname"]

        if name["forename"]:
            ret += ", " + name["forename"]

        if name["genName"]:
            ret += ", " + name["genName"]

        if len(names) > 1:
            ret += ", " if len(names) > 2 else " and "

        ix += 1

    # maximum is used for MLA format citations. If there are more
    # than 3 authors, then we only list the first author + "et
    #  al.".

    if maximum is not None and len(names) > maximum:
        ret += "et al."

        return ret

    for name in names[ix:]:
        if name["forename"]:
            ret += name["forename"] + " "

        ret += name["surname"]

        if name["genName"]:
            ret += ", " + name["genName"]

        if name is not names[-1]:
            ret += " and " if name is names[-2] else ", "

    return ret

class CitePlugin(CMSPluginBase):
    text_enabled = True
    model = CMSPlugin
    name = _("Cite Plugin")
    render_template = "core/cite.html"
    cache = False

    def __init__(self, *args, **kwargs):
        super(CitePlugin, self).__init__(*args, **kwargs)
        editors = settings.BTW_EDITORS
        self.chicago_authors = format_names(editors, True)
        self.mla_authors = format_names(editors, True, 3)

    def render(self, context, instance, placeholder):
        context.update({
            'instance': instance,
            'bibliographical_data': {
                'version': util.version()
            },
            'chicago_authors': self.chicago_authors,
            'mla_authors': self.mla_authors,
            'year': '2014-' + str(datetime.date.today().year),
        })

        return context

    def icon_src(self, instance):
        return os.path.normpath("%s/images/icons/bookmark_%sx%s.png" %
                                (settings.STATIC_URL, 32, 32))


plugin_pool.register_plugin(CitePlugin)
