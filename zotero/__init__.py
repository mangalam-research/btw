from django.conf import settings

if settings.ZOTERO_SETTINGS is None:
    raise ValueError("ZOTERO_SETTINGS must be set in settings.py")

for key in ("uid", "api_key"):
    if settings.ZOTERO_SETTINGS.get(key) is None:
        raise ValueError("ZOTERO_SETTINGS['%s'] must be set" % key)
