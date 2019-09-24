from collections.abc import Callable
import re

NONEXISTENT = object()

name_re = re.compile("^[A-Z_]+$")
bad_char_re = re.compile(r"['\"\\]")

class Secret(object):
    pass

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
        if getattr(self, name, NONEXISTENT) is NONEXISTENT:
            setattr(self, name, Secret())

    def read_secret_file(self, file_path):
        with open(file_path, 'r') as secret:
            for line in secret:
                line = line.strip()
                [name, value] = line.split("=", 1)
                if not name_re.match(name):
                    raise Exception("invalid name syntax")
                value = value.strip()
                if value[0] in ('"', "'"):
                    if value[0] != value[-1]:
                        raise Exception("badly quoted value")
                    value = value[1:-1]
                if bad_char_re.match(value):
                    raise Exception("invalid character in value")

                setattr(self, name.strip(), value.strip())

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
