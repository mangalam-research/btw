class Settings(object):

    attrs = {}

    def __getattr__(self, name):
        try:
            val = self.attrs[name]
            if callable(val):
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
