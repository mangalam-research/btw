from collections.abc import Callable

NONEXISTENT = object()

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

    def as_dict(self):
        return {key: getattr(self, key) for key in self.attrs}

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
