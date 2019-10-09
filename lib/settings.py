from collections.abc import Callable
import re
import subprocess
import json
import sys

NONEXISTENT = object()

name_re = re.compile("^[A-Z_]+$")
bad_char_re = re.compile(r"['\"\\]")

class Secret(object):
    pass

# PWD is automatically set by sh and compatible shells (bash, dash, ...)
# _ and SHLVL are automatically set by bash
# LC_CTYPE is set by python 3 when it starts.
RESTRICTED_SECRET_NAMES = ("PWD", "_", "SHLVL", "LC_CTYPE")


class Settings(object):

    def __init__(self, parent=None):
        self.__dict__["attrs"] = {}
        self.__dict__["parent"] = parent

    def __getattr__(self, name):
        val = self.attrs.get(name, NONEXISTENT)
        if val is NONEXISTENT:
            if self.parent is None:
                raise AttributeError("'{0}' object has no attribute '{1}'"
                                     .format(type(self).__name__, name))
            return getattr(self.parent, name)
        return val(self) if isinstance(val, Callable) else val

    def __setattr__(self, name, value):
        if name in ("parent", "attrs"):
            raise AttributeError("'{}' is a reserved name".format(name))
        attrs = self.attrs
        prev = attrs.get(name, NONEXISTENT)
        if prev is not NONEXISTENT:
            if isinstance(value, Callable):
                override = Settings(self)
                setattr(override, name, prev)
                store = lambda _: value(override)
            elif isinstance(prev, Callable):
                # This is almost always an error.
                raise AttributeError(("trying to override attribute '{0}' "
                                      "from a callable value to a "
                                      "non-callable one")
                                     .format(name))
            else:
                store = value
        else:
            store = value

        attrs[name] = store

    def declare_secret(self, name):
        if name in RESTRICTED_SECRET_NAMES:
            raise ValueError(f"cannot use {name} as a secret name")

        if getattr(self, name, NONEXISTENT) is NONEXISTENT:
            setattr(self, name, Secret())

    def read_secret_file(self, file_path):
        #
        # Adapted from https://stackoverflow.com/a/7198338/
        #
        # A previous version used sys.executable instead of hardcoding
        # ``python``. However, when running in uwsgi, sys.executable is
        # ``uwsgi``, which does not work.
        #
        env = json.loads(subprocess.check_output(
            ["/bin/bash", "-c",
             f'set -a && . {file_path} && python -c '
             '"import os, json; print(json.dumps(dict(os.environ)))"'],
            env={}))
        for name, value in env.items():
            if name in RESTRICTED_SECRET_NAMES:
                continue

            if not isinstance(getattr(self, name), Secret):
                raise Exception(f"trying to set secret {name}, "
                                "which is not a secret")
            setattr(self, name, value)

    def as_dict(self):
        def get(key):
            value = getattr(self, key)
            if isinstance(value, Secret):
                raise Exception("secret unspecified: " + key)
            return value

        return {key: get(key) for key in self.attrs}

s = Settings()

# This is a utility function that is used when computing settings. We
# cannot put it in util.py as the code there loads Django's settings
# and thus we run into a circular dependency issue.
def join_prefix(prefix, suffix):
    """
    Joins an optional prefix with a suffix.

    :returns: The suffix if the prefix is ``None`` or the empty
              string. Otherwise, the prefix concatenated with a period
              and the suffix.
    :rtype: A string of the type passed in.
    """
    return prefix + "." + suffix if prefix else suffix
