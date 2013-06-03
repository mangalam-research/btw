import btw.settings as settings

def global_context_processor(request):
    return { 'btw_globals': 
             {
            'requirejs_path': settings.BTW_REQUIREJS_PATH,
            'requirejs_config_path': settings.BTW_REQUIREJS_CONFIG_PATH,
            'wed_config': settings.BTW_WED_CONFIG,
            }
             }
