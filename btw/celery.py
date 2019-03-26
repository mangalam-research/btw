

import os
import logging.config

import celery
from celery import Celery
from celery.signals import after_setup_logger, worker_init

from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'btw.settings')

#
# See this bug report:
# https://github.com/celery/celery/issues/2903
#
# Without the following patch, Celery crashes.
#
if celery.VERSION > (3, 1, 24, '', '') and celery.VERSION < (4,):
    raise ValueError("check whether celery still needs a patch")

if celery.VERSION >= (3, 1, 23, '', '') and celery.VERSION < (4,):
    from celery.backends.redis import RedisBackend

    def patched_create_client(self, **params):
        def normalize(param):
            value = params.get(param)
            if value is not None:
                params[param] = float(value)

        normalize('socket_timeout')
        normalize('socket_connect_timeout')
        return self._new_redis_client(**params)

    RedisBackend._create_client = patched_create_client

if settings.BTW_SELENIUM_TESTS:
    # If we are testing, the live server is patched so as to not
    # access the Zotero server. We must apply the same patch here.
    from core.tests.common_zotero_patch import patch
    patch.start()

@after_setup_logger.connect
def configure_logging(sender=None, **kwargs):
    logger = logging.getLogger('celery')
    # Yes, we cheat and access a private variable. There is no simple
    # way to do this.
    logger.addHandler(logging._handlers['mail_admins'])


@worker_init.connect
def handle_worker_init(sender=None, **kwargs):
    #
    # We have to perform here what the test runner does for the main
    # process.
    #
    # The thing is though that we need to do this only if we are *not*
    # running the Selenium tests because if we *are* then the
    # modification is done in test_settings.py.
    #

    if settings.BTW_TESTING and not settings.BTW_SELENIUM_TESTS:
        for name in settings.DATABASES.keys():
            db = settings.DATABASES[name]
            db['NAME'] = 'test_' + db['NAME']


app = Celery('btw')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
