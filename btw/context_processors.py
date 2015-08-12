from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.utils.functional import SimpleLazyObject


def global_context_processor(request):
    return {
        # These originate from the settings but are specific to BTW.
        'btw_globals': {
            'requirejs_path': settings.BTW_REQUIREJS_PATH,
            'requirejs_config_path': settings.BTW_REQUIREJS_CONFIG_PATH,
            'wed_config': settings.BTW_WED_CONFIG,
            'btw_qunit_css_path': settings.BTW_QUNIT_CSS_PATH,
            'btw_bootstrap_css_path': settings.BTW_BOOTSTRAP_CSS_PATH,
            'btw_fontawesome_css_path': settings.BTW_FONTAWESOME_CSS_PATH,
            'btw_datatables_css_path': settings.BTW_DATATABLES_CSS_PATH,
            'btw_bootstrap_editable_css_path':
            settings.BTW_BOOTSTRAP_EDITABLE__CSS_PATH,
            'wed_polyfills': settings.BTW_WED_POLYFILLS,
            'demo': settings.BTW_DEMO,
            'editors': settings.BTW_EDITORS,
        },
        # Vanilla Django settings.
        'settings': {
            'DEBUG': settings.DEBUG
        },
        # Other globals that do not come from settings.
        'globals': {
            'site_name': SimpleLazyObject(
                lambda: get_current_site(request).name)
        }
    }
