# pylint: disable=W0401,W0614

import os
from lib.settings import s

#
# These settings must be set before anything else is loaded because
# other settings may be computed on the base of these.
#
s.BTW_TESTING = True

# We use the environment variable JENKINS_HOME to detect whether we
# are runnning in a Jenkins environment. (Seems safer than some of the
# other environment variables that Jenkins exports.) We use 'BUILDBOT'
# to know whether we are operating in a buildbot environment.
s.BTW_BUILD_ENV = os.environ.get('JENKINS_HOME', None) or \
    os.environ.get('BUILDBOT', None)

#
# Trigger the loading of the regular settings so that they modify s
#
from . import settings  # noqa, pylint: disable=unused-import

#
# These must be off for WebTest based tests to run without issue.
#

s.SESSION_COOKIE_SECURE = False
s.CSRF_COOKIE_SECURE = False

#
# This must be off so that Selenium tests that run in IE can
# manipulate the session cookie.
#

s.SESSION_COOKIE_HTTPONLY = False

# Yes, we mean to have this be private.
__SILENT = True

s.BTW_DISABLE_MIGRATIONS = True

if not __SILENT:
    loggers = s.LOGGING['loggers']
    loggers[''] = {
        'handlers': ['console'],
        'level': 'NOTSET',
        'propagate': True,
    }
    del s.LOGGING['handlers']['console']['filters']

if s.BTW_SELENIUM_TESTS:
    for name in s.DATABASES.keys():
        db = s.DATABASES[name]
        db['NAME'] = 'test_' + db['NAME']

        if 'TEST_MIRROR' in db:
            raise ValueError("TEST_MIRROR already set for " + name)

        TEST = db.get('TEST')
        if TEST is not None and 'MIRROR' in TEST:
            raise ValueError("TEST['TEST_MIRROR'] already set for " + name)

        if TEST is None:
            TEST = db['TEST'] = {}

        TEST['MIRROR'] = name

# As a base we change the root collection to /test_...
s.EXISTDB_ROOT_COLLECTION = "/test_btw"

if s.BTW_BUILD_ENV:
    builder = os.environ['BUILDER']
    for db in s.DATABASES.itervalues():
        name = db['NAME']
        test_name = name + '_' + builder
        if not test_name.startswith("test_"):
            test_name = "test_" + test_name
        # If we are using TEST_MIRROR then TEST_NAME is not used and thus
        # NAME itself must be altered.
        if not (('TEST_MIRROR' in db) or ('MIRROR' in db.get('TEST', {}))):
            if 'TEST_NAME' in db:
                raise ValueError("TEST_NAME already set for " + name)

            TEST = db.get('TEST')
            if TEST is not None and 'NAME' in TEST:
                raise ValueError("TEST['NAME'] already set for " + name)

            if TEST is None:
                TEST = db['TEST'] = {}

            TEST['NAME'] = test_name
        else:
            db['NAME'] = test_name

    # When we are in a builder we want to use the builder name as part
    # of the root name.
    s.EXISTDB_ROOT_COLLECTION = "/test_" + builder

    # We do not want to use --with-progressive if we are in a builder.
    # The progressive reporter is useful only when manually using the
    # CLI.
    s.NOSE_ARGS.remove("--with-progressive")

globals().update(s.as_dict())
