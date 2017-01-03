# Django settings for the BTW project.

#
# You have to set all values on the ``s`` object. This object will be
# converted to a regular settings object at the end of this
# file. Values which are callable will be resolved to static value as
# the ``s`` object is converted to regular settings. MAKE SURE NOT TO
# CREATE CIRCULAR DEPENDENCIES BETWEEN SETTINGS. You'll just get a
# stack overflow error if you do.
#
import os
from logging import Filter

from slugify import slugify
from kombu import Queue

from . import _env
from lib.settings import s, join_prefix


# This assumes that this file is settings/__init__.py
s.CURDIR = os.path.dirname(os.path.abspath(__file__))
# This is the directory in which the *module* is located.
s.PARENTDIR = os.path.dirname(s.CURDIR)
# Top of the app hierarchy
s.TOPDIR = os.path.dirname(s.PARENTDIR)

# The Python virtualenv that this instance is run with.
s.ENVPATH = None

# Basic path where to put the logs.
s.BTW_LOGGING_PATH = None
# Basic path where to put the run files (like PID files).
s.BTW_RUN_PATH = None

# The path where BTW-specific logs should be stored.
s.BTW_LOGGING_PATH_FOR_BTW = lambda s: os.path.join(s.BTW_LOGGING_PATH, "btw")
# The path where BTW-specific run-time information should be stored.
s.BTW_RUN_PATH_FOR_BTW = lambda s: os.path.join(s.BTW_RUN_PATH, "btw")

s.DEBUG = False

s.ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

# Introduced in 1.5. This is the default value for 1.5 but we define
# it here so that we can work with 1.4 seamlessly.
s.AUTH_USER_MODEL = 'auth.User'

s.MANAGERS = s.ADMINS

s.LOGIN_URL = '/login/'
s.LOGIN_REDIRECT_URL = 'lexicography_main'

# s.DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(s.TOPDIR, 'btw.sqlite3'),
#     }
# }

s.CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'default'
    },
    'session': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'session'
    },
    'page': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'session'
    },
    'article_display': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'article_display'
    }
}

s.SESSION_CACHE_ALIAS = 'session'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
s.TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
s.LANGUAGE_CODE = 'en-us'

s.SITE_ID = 1

# This is a BTW-ony variable which must match the site name set for
# the SITE_ID set above in the database table created by the Site
# framework. It is not possible to query the value from the database
# here because Django is not guaranteed to be up yet. But we need the
# value to set some other values later. So the solution is to set the
# value here and have a check later.
s.BTW_SITE_NAME = ''

# This is used so that we can use the site name in places that put
# restrictions on the format of names.
s.BTW_SLUGIFIED_SITE_NAME = lambda s: slugify(s.BTW_SITE_NAME.lower(),
                                              separator="_")

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
s.USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
s.USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
s.USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
s.MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
s.MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in s.STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
s.STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
s.STATIC_URL = '/static/'

# Additional locations of static files
s.STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(s.TOPDIR, "build/static-build"),
)

# List of finder classes that know how to find static files in
# various locations.
s.STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'pipeline.finders.PipelineFinder'
)

# We need this for ``pipeline``.
s.STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

s.PIPELINE = {
    "STYLESHEETS": {},
    "JAVASCRIPT": {},
    "CSS_COMPRESSOR": None,
    "JS_COMPRESSOR": None,
    "COMPILERS": (
        'pipeline.compilers.less.LessCompiler',
    ),
    "LESS_BINARY": os.path.join(s.TOPDIR, "./node_modules/.bin/lessc"),
}

#
# This must be set in the installation-specific files.
#
# Make this unique, and don't share it with anybody.
# s.SECRET_KEY = ''

s.MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

    #
    # We do not use XFrameOptionsMiddleware because we set nginx to
    # issue the necessary header for all requests made to the site.
    #
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #

    #
    # We do not use SecurityMiddleware because we set nginx to issue
    # the necessary header for all requests made to the site.
    #
    # 'django.middleware.security.SecurityMiddleware',
    #

    # LocaleMiddleware was added for Django CMS.
    'django.middleware.locale.LocaleMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
    'cms.middleware.utils.ApphookReloadMiddleware',
)

# Don't use a unicode value for this. Webtest does not like it.
s.CSRF_COOKIE_NAME = "csrftoken"

s.CACHE_MIDDLEWARE_KEY_PREFIX = lambda s: s.BTW_SITE_NAME

s.CACHE_MIDDLEWARE_ALIAS = 'page'

s.ATOMIC_REQUESTS = True

s.ROOT_URLCONF = 'btw.urls'

# Python dotted path to the WSGI application used by Django's runserver.
s.WSGI_APPLICATION = 'btw.wsgi.application'

s.CMS_TEMPLATES = (
    ('generic_page.html', 'Generic'),
    ('front_page.html', 'Site Front Page'),
)

s.CMS_PERMISSION = True

# Setting it to ``True`` prevents the toolbar from being shown on
# pages that are not "CMS pages", meaning pages that do not have
# editable contents in the CMS. This effectively prevents the
# ``cms.middleware.toolbar`` middleware from acting on pages served
# statically. If we do not prevent it, it hits the database for each
# static file served and causes issues with running out of
# connections.
#
# In some versions of the 3.1.x series, setting it to ``True`` would
# cause errors.
s.CMS_TOOLBAR_HIDE = True

s.LANGUAGES = [
    ('en-us', 'English'),
]

s.TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(s.TOPDIR, "templates"),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "btw.context_processors.global_context_processor",
                'sekizai.context_processors.sekizai',
                'cms.context_processors.cms_settings',
            ],
        },
    },
]

s.AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

#
# rest_framework is not part of the installed apps. What gives? It is
# not needed to use Django REST Framework, because it only provides
# the browsable API, which we currently do not want to provide.
#
s.INSTALLED_APPS = (
    'core',
    'btw_management',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Add this app only for the static tag that can be used in
    # templates. We must NOT ever use it even in testing because it
    # caches responses.
    'django.contrib.staticfiles',
    # This is required by Django CMS and must appear before
    # 'django.contrib.admin'
    'djangocms_admin_style',
    'django.contrib.admin.apps.SimpleAdminConfig',
    'django.contrib.admindocs',
    'django_nose',
    'wed',
    'lexicography',
    'bibliography',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'invitation',
    # 'allauth.socialaccount.providers.angellist',
    # 'allauth.socialaccount.providers.bitly',
    # 'allauth.socialaccount.providers.dropbox',
    # 'allauth.socialaccount.providers.facebook',
    # 'allauth.socialaccount.providers.feedly',
    # 'allauth.socialaccount.providers.github',
    # 'allauth.socialaccount.providers.google',
    # 'allauth.socialaccount.providers.instagram',
    # 'allauth.socialaccount.providers.linkedin',
    # 'allauth.socialaccount.providers.openid',
    # 'allauth.socialaccount.providers.persona',
    # 'allauth.socialaccount.providers.soundcloud',
    # 'allauth.socialaccount.providers.stackexchange',
    # 'allauth.socialaccount.providers.twitch',
    # 'allauth.socialaccount.providers.twitter',
    # 'allauth.socialaccount.providers.vimeo',
    # 'allauth.socialaccount.providers.vk',
    # 'allauth.socialaccount.providers.weibo',
    'bootstrap3',
    'django_cache_management',
    # Django CMS
    'cms',
    # The following are needed by Django CMS
    'treebeard',
    'menus',
    'sekizai',
    'reversion',
    # For django-filer which is required by Django CMS
    "filer",
    "mptt",
    "easy_thumbnails",
    "djangocms_text_ckeditor",
    'cmsplugin_iframe',
    # For cmsplugin-filer, which is required by Django CMS,
    'cmsplugin_filer_file',
    'cmsplugin_filer_folder',
    'cmsplugin_filer_link',
    'cmsplugin_filer_image',
    'cmsplugin_filer_teaser',
    'cmsplugin_filer_video',
    'eulexistdb',
    'semantic_fields',
    # End of apps required by Django CMS.
    'pipeline',
    'final',
)

# False by default, we make it true in tests.
s.BTW_DISABLE_MIGRATIONS = False

class DisableMigrations(object):

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"

# pylint: disable=redefined-outer-name
def _migration_modules(s):
    if s.BTW_DISABLE_MIGRATIONS:
        return DisableMigrations()

    return {}

s.MIGRATION_MODULES = _migration_modules

# For easy_thumbnails
s.THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    # 'easy_thumbnails.processors.scale_and_crop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)

s.ACCOUNT_AUTHENTICATION_METHOD = "username"
s.ACCOUNT_EMAIL_REQUIRED = True
s.ACCOUNT_EMAIL_VERIFICATION = "mandatory"
s.ACCOUNT_UNIQUE_EMAIL = False
s.ACCOUNT_ADAPTER = 'invitation.account_adapter.AccountAdapter'
s.ACCOUNT_SIGNUP_FORM_CLASS = 'core.forms.SignupForm'

s.INVITATION_EXPIRY_DAYS = 5

s.TEST_RUNNER = 'core.runner.Runner'

class TestingFilter(Filter):

    def filter(self, record):
        from django.conf import settings
        return not settings.BTW_TESTING

# Yes, this is a private variable.
__EMAIL_TEST = False

if __EMAIL_TEST:
    s.EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    s.EMAIL_FILE_PATH = '/tmp/app-messages'  # change this to a proper location
    s.ADMINS = (("Louis Dubeau", "ldd@lddubeau.com"), )

s.LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'testing': {
            '()': TestingFilter
        }
    },
    'formatters': {
        'verbose': {
            'format': ('%(levelname)s %(asctime)s %(module)s '
                       '%(process)d %(thread)d %(message)s')
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': [] if __EMAIL_TEST else ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'filters': ['testing'],
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'lexicography': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'lexicography.tasks': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'core.tasks': {
            'level': 'DEBUG',
            'propagate': True,
        },
        'zotero': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django_datatables_view': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        }
    }
}

s.CELERY_ACCEPT_CONTENT = ['json']
s.CELERY_TASK_SERIALIZER = 'json'
s.CELERY_RESULT_SERIALIZER = 'json'
# We need this to be able to check workers in btwcheck
s.CELERY_WORKER_DIRECT = True
# This is a prefix by which the worker names for this instance of BTW
# must use. The full name must be <prefix>.<suffix> where suffix is
# whatever is needed.
s.BTW_CELERY_WORKER_PREFIX = lambda s: s.BTW_SLUGIFIED_SITE_NAME
s.CELERY_TASK_DEFAULT_QUEUE = \
    lambda s: s.BTW_CELERY_WORKER_PREFIX + ".default"
s.BTW_CELERY_BIBLIOGRAPHY_QUEUE = \
    lambda s: s.BTW_CELERY_WORKER_PREFIX + ".bibliography"

s.CELERY_TASK_DEFAULT_EXCHANGE = 'default'
s.CELERY_TASK_DEFAULT_EXCHANGE_TYPE = 'topic'
s.CELERY_TASK_DEFAULT_ROUTING_KEY = 'default'

s.CELERY_TASK_QUEUES = lambda s: (
    Queue(s.CELERY_TASK_DEFAULT_QUEUE, routing_key='default'),
    Queue(s.BTW_CELERY_BIBLIOGRAPHY_QUEUE, routing_key='bibliography'),
)

s.CELERY_TASK_ROUTES = lambda s: {
    'bibliography.tasks.fetch_items': {
        'queue': s.BTW_CELERY_BIBLIOGRAPHY_QUEUE,
        'routing_key': 'bibliography',
    },
    'bibliography.tasks.periodic_fetch_items': {
        'queue': s.BTW_CELERY_BIBLIOGRAPHY_QUEUE,
        'routing_key': 'bibliography',
    },
}

# This is used to distinguish multiple redis servers running on the
# same machine but for different instances of BTW. For instance, one
# redis for development and another that runs for testing.
s.BTW_REDIS_SITE_PREFIX = lambda s: s.BTW_SLUGIFIED_SITE_NAME

# Unfortunately, due to ``UNIX_MAX_PATH`` (see ``man unix``), we have
# to be careful not to go over 108 characters (on Linux) for the
# socket created by Redis, which means we cannot just put the socket
# wherever we want, so...
s.BTW_REDIS_SOCKET_DIR_PATH = os.path.join("/var", "tmp", "btw", "redis")
s.BTW_REDIS_SOCKET = lambda s: \
    os.path.join(s.BTW_REDIS_SOCKET_DIR_PATH,
                 join_prefix(s.BTW_REDIS_SITE_PREFIX, "redis.sock"))


s.REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
}

s.BTW_BOOTSTRAP_CSS_PATH = \
    '/static/lib/external/bootstrap/css/bootstrap.min.css'
s.BTW_FONTAWESOME_CSS_PATH = \
    '/static/lib/external/font-awesome/css/font-awesome.min.css'
#
# Default:
# s.BTW_DATATABLES_CSS_PATH = \
#    '/static/lib/external/datatables/css/jquery.dataTables.css'
#
# For styling with bootstrap:
s.BTW_DATATABLES_CSS_PATH = \
    '/static/lib/external/datatables/css/dataTables.bootstrap.css'

s.BTW_BOOTSTRAP_EDITABLE__CSS_PATH = \
    '/static/lib/external/bootstrap3-editable/css/bootstrap-editable.css'
s.BTW_REQUIREJS_PATH = None
# We don't load classList from the external directory because it is
# needed only for IE 9 and we don't support it for BTW.
s.BTW_WED_POLYFILLS = tuple('/static/lib/wed/polyfills/{0}.js'.format(x)
                            for x in ('contains', 'matches', 'closest',
                                      'innerHTML_for_XML',
                                      'firstElementChild_etc', 'normalize'))
s.BTW_WED_USE_REQUIREJS = None
s.BTW_WED_PATH = None
s.BTW_WED_CSS = None
s.BTW_WED_LOGGING_PATH = \
    lambda s: os.path.join(s.BTW_LOGGING_PATH_FOR_BTW, "wed")
s.BTW_QUNIT_CSS_PATH = None

s.BTW_JQUERY_GROWL_CSS_PATH = \
    '/static/lib/external/jquery-growl/css/jquery.growl.css'

s.BTW_DEMO = False
if not hasattr(s, "BTW_TESTING"):
    s.BTW_TESTING = False
s.BTW_SELENIUM_TESTS = False

# This setting is used to force BTW to install its apps somewhere. On
# a normally deployed site (and even in the development site), some
# BTW applications are available as apphooks attached to Django CMS
# pages. In testing, this is not always desirable. For intance, when
# manipulating fixtures for testing, a virgin database is created in
# which fixtures to be edited are loaded. This new database obviously
# has no CMS page. Turning this setting on is the solution. It should not
# be used in production. It will be ignored if DEBUG is not also True.
s.BTW_DIRECT_APP_MODE = False

# This has to be set to a real value for running the project. This
# variable contains a list of forename, surname, genName fields (this
# mirrors what we accept in the schema that determines article
# structure). The list of names here determines the editor names that
# are used for citing the project *as a whole*.
#
# Why a setting and not a table. Table queries are relatively costly
# compared to reading a setting. Also, this setting is not going to
# change very often during the life of the project. In fact, we expect
# it won't ever change, but we want to have some flexibility.
s.BTW_EDITORS = None

# If the debug_toolbar is used, we don't want it to patch the settings
# itself because debug_panel (which extends debug_toolbar) requires
# some specific changes.
s.DEBUG_TOOLBAR_PATCH_SETTINGS = False
s.INTERNAL_IPS = ('127.0.0.1', '::1')

# These are custom settings...
# Either "full" or "standalone". Full provides the web server used to provide
# eXide, etc.
s.BTW_EXISTDB_SERVER_TYPE = "full"
s.BTW_EXISTDB_SERVER_ADMIN_USER = None
s.BTW_EXISTDB_SERVER_ADMIN_PASSWORD = None

# These are eulexistdb settings
s.EXISTDB_SERVER_USER = None
s.EXISTDB_SERVER_PASSWORD = None
# This is the default location, port and URL when using eXist as
# a standalone server.
def _server_url(s):
    host = "http://127.0.0.1"
    return {
        "standalone": host + ":8088/",
        "full": host + ":8080/exist/"
    }[s.BTW_EXISTDB_SERVER_TYPE]

s.EXISTDB_SERVER_URL = _server_url
s.EXISTDB_ROOT_COLLECTION = "/btw"

# The directory that contains eXist-db's bin.
s.EXISTDB_HOME_PATH = os.path.join(os.environ["HOME"], "local", "eXist-db")

# Do not collapse those ChangeRecord objects that are younger than
# this number of days.
s.BTW_COLLAPSE_CRS_OLDER_THAN = 30
s.BTW_CLEAN_CRS_OLDER_THAN = 90

# This is the default value. We have to populate it with the default
# if we want ot *modify* it elsewhere because changing the value to
# something else than the default amounts to cancelling the
# default. So if we want to *add* a new panel, we have to add to the
# defaults.
s.DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]

exec _env.find_config("btw")  # pylint: disable=exec-used

# Execute per-app overrides.
for app in s.INSTALLED_APPS:
    if app.find(".") < 0:
        if os.path.exists(os.path.join(s.CURDIR, app + ".py")):
            # pylint: disable=exec-used
            exec open(os.path.join(s.CURDIR, app + ".py"))
        exec _env.find_config(app)  # pylint: disable=exec-used

#
# Export everything to the global space. This is where we convert
# ``s`` to the regular settings.
#
globals().update(s.as_dict())
