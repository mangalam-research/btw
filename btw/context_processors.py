from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils.functional import SimpleLazyObject


def global_context_processor(request):
    return {
        # These originate from the settings but are specific to BTW.
        'btw_globals': {
            'requirejs_path': settings.BTW_REQUIREJS_PATH,
            'requirejs_config_path': settings.BTW_REQUIREJS_CONFIG_PATH,
            'btw_bootstrap_css_path': settings.BTW_BOOTSTRAP_CSS_PATH,
            'btw_bootstrap_treeview_css_path':
            settings.BTW_BOOTSTRAP_TREEVIEW_CSS_PATH,
            'btw_fontawesome_css_path': settings.BTW_FONTAWESOME_CSS_PATH,
            'btw_datatables_css_path': settings.BTW_DATATABLES_CSS_PATH,
            'wed_css': settings.BTW_WED_CSS,
            'btw_mode_css': settings.BTW_MODE_CSS,
            'wed_polyfills': settings.BTW_WED_POLYFILLS,
            'demo': settings.BTW_DEMO,
            'editors': settings.BTW_EDITORS,
            'testing': settings.BTW_TESTING,
        },
        # Vanilla Django settings.
        'settings': {
            'DEBUG': settings.DEBUG
        },
        # Other globals that do not come from settings.
        'globals': {
            'site_name': SimpleLazyObject(
                lambda: get_current_site(request).name),
            'site_url': request.build_absolute_uri('/')
        }
    }
