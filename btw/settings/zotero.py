import _env

# All sensitive so init with empty dir.
ZOTERO_SETTINGS = {
    }

exec _env.find_config("zotero") in globals()
