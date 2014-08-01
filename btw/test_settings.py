# pylint: disable=W0401,W0614
from .settings import *

#
# These must be off for WebTest based tests to run without issue.
#

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

__SILENT = True

LOGGING['loggers'] = {}
if __SILENT:
    LOGGING['disable_existing_loggers'] = True
else:
    LOGGING['loggers'][''] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': True,
    }

BTW_TESTING = True
