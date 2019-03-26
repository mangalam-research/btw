import collections
class Settings(object):

    attrs = {}

    def __getattr__(self, name):
        try:
            val = self.attrs[name]
            if isinstance(val, collections.Callable):
                val = val(self)
            return val
        except KeyError:
            raise AttributeError("'{0}' object has no attribute '{1}'"
                                 .format(type(self).__name__, name))

    def __setattr__(self, name, value):
        self.attrs[name] = value

    def __delattr__(self, name):
        try:
            del self.attrs[name]
        except KeyError:
            raise AttributeError("'{0}' object has no attribute '{1}'"
                                 .format(type(self).__name__, name))

    def as_dict(self):
        ret = {}

        for key in self.attrs:
            ret[key] = self.__getattr__(key)

        return ret

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
    return prefix + "." + suffix if prefix is not None and len(prefix) \
        else suffix
