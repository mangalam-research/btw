
class MinimalQuery(object):
    """
    This is a query that implements minimally the QuerySet functions:
    just enough for the test suite to pass.
    """

    def __init__(self, value):
        self.value = value

    def __getitem__(self, key):
        return self.value[key]

    def order_by(self, *args, **kwargs):
        return self

    def distinct(self, *args, **kwargs):
        return self

class FakeChangeRecord(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def get_absolute_url(self):
        return self.url
