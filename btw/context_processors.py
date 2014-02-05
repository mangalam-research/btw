from django.conf import settings


def global_context_processor(request):
    return {'btw_globals': {
        'requirejs_path': settings.BTW_REQUIREJS_PATH,
        'requirejs_config_path': settings.BTW_REQUIREJS_CONFIG_PATH,
        'wed_config': settings.BTW_WED_CONFIG,
        'btw_qunit_css_path': settings.BTW_QUNIT_CSS_PATH,
        'btw_bootstrap_css_path': settings.BTW_BOOTSTRAP_CSS_PATH,
        'btw_datatables_css_path': settings.BTW_DATATABLES_CSS_PATH

    }}
