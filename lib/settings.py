class Settings(object):

    def __getattr__(self, name):
        try:
            return self.__dict__[name]
        except KeyError:
            raise AttributeError("'{0}' object has no attribute '{1}'"
                                 .format(type(self).__name__, name))

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __delattr__(self, name):
        try:
            del self.__dict__[name]
        except KeyError:
            raise AttributeError("'{0}' object has no attribute '{1}'"
                                 .format(type(self).__name__, name))

    def as_dict(self):
        return dict(self.__dict__)

s = Settings()
