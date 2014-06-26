# pylint: disable=W0401,W0614
from .settings import *

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
