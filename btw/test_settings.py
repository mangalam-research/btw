# pylint: disable=W0401,W0614
from .settings import *

#
# These must be off for WebTest based tests to run without issue.
#

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

__SILENT = True

if __SILENT:
    LOGGING_CONFIG = False
else:
    loggers = LOGGING['loggers']
    loggers[''] = {
        'handlers': ['console'],
        'level': 'NOTSET',
        'propagate': True,
    }

BTW_TESTING = True
