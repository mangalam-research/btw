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

# We use the environment variable JENKINS_HOME to detect whether we
# are runnning in a Jenkins environment. (Seems safer than some of the
# other environment variables that Jenkins exports.) We use 'BUILDBOT'
# to know whether we are operating in a buildbot environment.
build_env = os.environ.get('JENKINS_HOME', None) or \
    os.environ.get('BUILDBOT', None)

if build_env:
    build_id = os.environ['BUILD_TAG']
    for db in DATABASES.itervalues():
        db['TEST_NAME'] = 'test_' + db['NAME'] + '_' + build_id

BTW_TESTING = True
