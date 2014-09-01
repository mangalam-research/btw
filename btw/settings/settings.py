# Django settings for btw project.

import os
from . import _env

# This assumes that this file is settings/__init__.py
CURDIR = os.path.dirname(os.path.abspath(__file__))
# This is the directory in which the *module* is located.
PARENTDIR = os.path.dirname(CURDIR)
# Top of the app hierarchy
TOPDIR = os.path.dirname(PARENTDIR)

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

# Introduced in 1.5. This is the default value for 1.5 but we define
# it here so that we can work with 1.4 seamlessly.
AUTH_USER_MODEL = 'auth.User'

MANAGERS = ADMINS

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = 'lexicography_main'

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(TOPDIR, 'btw.sqlite3'),
#     }
# }

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'default'
    },
}


# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(TOPDIR, "build/static-build"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    # 'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'less.finders.LessFinder'
)

#
# This must be set in the installation-specific files.
#
# Make this unique, and don't share it with anybody.
# SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware'
)

ATOMIC_REQUESTS = True

ROOT_URLCONF = 'btw.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'btw.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(TOPDIR, "templates"),
)

TEMPLATE_CONTEXT_PROCESSORS = (
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
)

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    # Add this app only for the static tag that can be used in
    # templates. We must NOT ever use it even in testing because it
    # caches responses.
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'less',
    'south',
    'django_nose',
    'core',
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
    'django_forms_bootstrap'
)

ACCOUNT_AUTHENTICATION_METHOD = "username"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = False
ACCOUNT_ADAPTER = 'invitation.account_adapter.AccountAdapter'
ACCOUNT_SIGNUP_FORM_CLASS = 'core.forms.SignupForm'

INVITATION_EXPIRY_DAYS = 5

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

LOGGING = {
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

SOUTH_TESTS_MIGRATE = False


BTW_BOOTSTRAP_CSS_PATH = \
    '/static/lib/external/bootstrap/css/bootstrap.min.css'
BTW_FONTAWESOME_CSS_PATH = \
    '/static/lib/external/font-awesome/css/font-awesome.min.css'
#
# Default:
# BTW_DATATABLES_CSS_PATH = \
#    '/static/lib/external/datatables/css/jquery.dataTables.css'
#
# For styling with bootstrap:
BTW_DATATABLES_CSS_PATH = \
    '/static/lib/external/datatables/css/dataTables.bootstrap.css'
BTW_BOOTSTRAP_EDITABLE__CSS_PATH = \
    '/static/lib/external/bootstrap3-editable/css/bootstrap-editable.css'
BTW_REQUIREJS_PATH = None
# We don't load classList from the external directory because it is
# needed only for IE 9 and we don't support it for BTW.
BTW_WED_POLYFILLS = tuple('/static/lib/wed/polyfills/' +
                          x for x in ('contains.js', 'matches.js'))
BTW_WED_USE_REQUIREJS = None
BTW_WED_PATH = None
BTW_WED_CSS = None
BTW_WED_LOGGING_PATH = None
BTW_QUNIT_CSS_PATH = None
BTW_SITE_NAME = "BTW"
BTW_TESTING = False

# Execute the env specific overrides
exec _env.find_config("btw") in globals()  # pylint: disable=exec-used

# Execute per-app overrides.
for app in INSTALLED_APPS:
    if app.find(".") < 0:
        if os.path.exists(os.path.join(CURDIR, app + ".py")):
            # pylint: disable=exec-used
            exec open(os.path.join(CURDIR, app + ".py")) in globals()
        exec _env.find_config(app) in globals()  # pylint: disable=exec-used
