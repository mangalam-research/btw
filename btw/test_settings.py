# pylint: disable=W0401,W0614
from .settings import *

#
# These must be off for WebTest based tests to run without issue.
#

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

#
# This must be off so that Selenium tests that run in IE can
# manipulate the session cookie.
#

SESSION_COOKIE_HTTPONLY = False

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

if BTW_SELENIUM_TESTS:
    for name in DATABASES.keys():
        db = DATABASES[name]
        db['NAME'] = 'test_' + db['NAME']
        if 'TEST_MIRROR' in db:
            raise ValueError("TEST_MIRROR already set for " + name)
        db['TEST_MIRROR'] = name

# We use the environment variable JENKINS_HOME to detect whether we
# are runnning in a Jenkins environment. (Seems safer than some of the
# other environment variables that Jenkins exports.) We use 'BUILDBOT'
# to know whether we are operating in a buildbot environment.
build_env = os.environ.get('JENKINS_HOME', None) or \
    os.environ.get('BUILDBOT', None)

if build_env:
    builder = os.environ['BUILDER']
    for db in DATABASES.itervalues():
        test_name = 'test_' + db['NAME'] + '_' + builder
        # If we are using TEST_MIRROR then TEST_NAME is not used and thus
        # NAME itself must be altered.
        if not db.get('TEST_MIRROR'):
            db['TEST_NAME'] = test_name
        else:
            db['NAME'] = test_name


BTW_TESTING = True
