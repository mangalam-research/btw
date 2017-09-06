from lib import env
import rest_framework
from rest_framework.response import Response

#
# This file contains patches to Django and libraries in order to work
# around issues. Usually, we don't want patches but sometimes the
# pragmatic solution rather than wait for a fix in the official code
# (which may take a while) is to monkey patch and move on.
#
# Note that btw/celery.py also contains patches that are proper to
# running in celery.
#
# runner.py contains patches proper to running the test suite but that
# are not used in production.
#

#
# This DRF patch drops the data field from the serialized data of
# response objects. See
# https://github.com/encode/django-rest-framework/issues/5396
#
drf_version = tuple(int(x) for x in rest_framework.VERSION.split("."))

if drf_version > (3, 6, 4):
    raise Exception("check whether the DRF patch is still needed with "
                    "this version of DRF.")

if drf_version <= (3, 6, 4):
    oldGetState = Response.__getstate__

    def newGetState(self):
        state = oldGetState(self)
        for key in ('data', ):
            if key in state:
                del state[key]
        return state

    Response.__getstate__ = newGetState

if env.testing:
    #
    # We modify the connections so that the code cannot access the
    # database before the databases have been set by the test runner.
    #
    # The problem is that it is hard to track which Django operations
    # will result in a database access. For instance, most ``reverse``
    # calls won't result in a database access but some do, if they
    # involve the sites framework, for instance.
    #
    # We patch the code so that any connection that happens before our
    # runner gets a chance to update the databases fails.
    #
    # This requires the use of core.runner.Runner so that the patch is
    # undone when the tests start.
    #

    def fail(*args, **kwargs):
        raise Exception("database access during testing before the "
                        "databases have been set by the test runner")

    from django.db import connections
    for name in connections:
        conn = connections[name]
        if getattr(conn, "_old_connect", None) is not None:
            raise Exception("Django already defines an _old_connect field"
                            "on connections; can't patch them")
        setattr(conn, "_old_connect", conn.connect)
        conn.connect = fail

default_app_config = "core.apps.DefaultAppConfig"
