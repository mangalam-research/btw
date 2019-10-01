# -*- coding: utf-8 -*-
from lib.settings import s, join_prefix
from slugify import slugify

s.BTW_SITE_NAME = "BTW docker_build"

s.DEBUG = True

s.ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

if s.DEBUG:
    s.INSTALLED_APPS += ('btw_test',)

s.BTW_LOGGING_PATH = os.path.join(s.TOPDIR, "var", "log")
s.BTW_RUN_PATH = os.path.join(s.TOPDIR, "var", "run")

s.STATIC_ROOT = os.path.join(s.TOPDIR, '..', 'static')
s.MEDIA_ROOT = os.path.join(s.TOPDIR, '..', 'media')

s.BTW_EDITORS = [{
    "forename": u"Luis",
    "surname": u"Gómez",
    "genName": u""
}, {
    "forename": u"Ligeia",
    "surname": u"Lugli",
    "genName": u""
}]

s.EXISTDB_ROOT_COLLECTION = "/docker-build"
s.EXISTDB_HOME_PATH = "/usr/local/eXist-db/"

s.SERVER_EMAIL = "emailtest@btw.mangalamresearch.org"
s.DEFAULT_FROM_EMAIL = lambda s: s.SERVER_EMAIL
s.EMAIL_HOST = "mail.mangalamresearch.org"
s.EMAIL_INTEGRATION_TEST_HOST = "imap.dreamhost.com"
