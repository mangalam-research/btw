from lib.settings import s

# These are the same as karma_build but we cannot just import it here because
# this file needs to be read from Docker, and cannot depend on files that are
# not part of the Docker build.
s.ZOTERO_SETTINGS["uid"] = s.ZOTERO_UID
s.ZOTERO_SETTINGS["api_key"] = s.ZOTERO_API_KEY
