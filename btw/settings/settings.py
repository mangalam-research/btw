# Django settings for the BTW project.

#
# You have to set all values on the ``s`` object. This object will be
# converted to a regular settings object at the end of this
# file. Values which are callable will be resolved to static value as
# the ``s`` object is converted to regular settings. MAKE SURE NOT TO
# CREATE CIRCULAR DEPENDENCIES BETWEEN SETTINGS. You'll just get a
# stack overflow error if you do.
#
from lib.settings import s, join_prefix

import os
from slugify import slugify
from . import _env

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
s.TEMPLATE_DEBUG = s.DEBUG

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
    'less.finders.LessFinder'
)

#
# This must be set in the installation-specific files.
#
# Make this unique, and don't share it with anybody.
# s.SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
s.TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

s.MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # LocaleMiddleware was added for Django CMS.
    'django.middleware.locale.LocaleMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
)

s.CACHE_MIDDLEWARE_KEY_PREFIX = lambda s: s.BTW_SITE_NAME

s.CACHE_MIDDLEWARE_ALIAS = 'page'

s.ATOMIC_REQUESTS = True

s.ROOT_URLCONF = 'btw.urls'

# Python dotted path to the WSGI application used by Django's runserver.
s.WSGI_APPLICATION = 'btw.wsgi.application'

s.TEMPLATE_DIRS = (
    os.path.join(s.TOPDIR, "templates"),
)

s.CMS_TEMPLATES = (
    ('generic_page.html', 'Generic'),
    ('front_page.html', 'Site Front Page'),
)

s.CMS_PERMISSION = True

s.LANGUAGES = [
    ('en-us', 'English'),
]

s.TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    # Required by allauth template tags
    "django.core.context_processors.request",
    "django.contrib.messages.context_processors.messages",
    "allauth.account.context_processors.account",
    "allauth.socialaccount.context_processors.socialaccount",
    "btw.context_processors.global_context_processor",
    'sekizai.context_processors.sekizai',
    'cms.context_processors.cms_settings',
)

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
    'less',
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
    'django_forms_bootstrap',
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
    # End of apps required by Django CMS.
    'final',
)

s.MIGRATION_MODULES = {
    'filer': 'filer.migrations_django',
    'cmsplugin_filer_file': 'cmsplugin_filer_file.migrations_django',
    'cmsplugin_filer_folder': 'cmsplugin_filer_folder.migrations_django',
    'cmsplugin_filer_link': 'cmsplugin_filer_link.migrations_django',
    'cmsplugin_filer_image': 'cmsplugin_filer_image.migrations_django',
    'cmsplugin_filer_teaser': 'cmsplugin_filer_teaser.migrations_django',
    'cmsplugin_filer_video': 'cmsplugin_filer_video.migrations_django',
    'djangocms_text_ckeditor': 'djangocms_text_ckeditor.migrations_django'
}

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

s.TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

s.LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
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
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
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
s.CELERY_DEFAULT_QUEUE = \
    lambda s: s.BTW_CELERY_WORKER_PREFIX + ".default"
s.BTW_CELERY_BIBLIOGRAPHY_QUEUE = \
    lambda s: s.BTW_CELERY_WORKER_PREFIX + ".bibliography"

s.CELERY_DEFAULT_EXCHANGE = 'default'
s.CELERY_DEFAULT_EXCHANGE_TYPE = 'topic'
s.CELERY_DEFAULT_ROUTING_KEY = 'default'

from kombu import Queue

s.CELERY_QUEUES = lambda s: (
    Queue(s.CELERY_DEFAULT_QUEUE, routing_key='default'),
    Queue(s.BTW_CELERY_BIBLIOGRAPHY_QUEUE, routing_key='bibliography'),
)

s.CELERY_ROUTES = lambda s: {
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
s.BTW_WED_POLYFILLS = tuple('/static/lib/wed/polyfills/' +
                            x for x in ('contains.js', 'matches.js',
                                        'innerHTML_for_XML.js'))
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
