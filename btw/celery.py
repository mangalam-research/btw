from __future__ import absolute_import

import os
import logging.config

from celery import Celery

from django.conf import settings
from core.tests.common_zotero_patch import patch

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'btw.settings')

if settings.BTW_SELENIUM_TESTS:
    # If we are testing, the live server is patched so as to not
    # access the Zotero server. We must apply the same patch here.
    patch.start()

from celery.signals import after_setup_logger
@after_setup_logger.connect
def configure_logging(sender=None, **kwargs):
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'loggers': {
            'lexicography.tasks': {
                'level': 'DEBUG',
                'propagate': True,
            },
            'core.tasks': {
                'level': 'DEBUG',
                'propagate': True,
            },
        }
    }
    # We import information from our Django settings.
    dj_LOGGING = settings.LOGGING
    LOGGING['filters'] = dj_LOGGING['filters']
    LOGGING['handlers'] = {}
    LOGGING['handlers']['mail_admins'] = dj_LOGGING['handlers']['mail_admins']
    logging.config.dictConfig(LOGGING)
    logger = logging.getLogger('celery')
    # Yes, we cheat and access a private variable. There is no simple
    # way to do this.
    logger.addHandler(logging._handlers['mail_admins'])


app = Celery('btw')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
