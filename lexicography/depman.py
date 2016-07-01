from lib import util
from django.core.cache import caches

class DependencyManager(object):

    def __init__(self, prefix):
        self.prefix = prefix
        self.cache = caches['article_display']

    def make_key(self, key):
        return self.prefix + u":" + key

    def record(self, dependee, dependent):
        util.add_to_set('article_display', self.make_key(dependee),
                        dependent)

    def remove(self, dependee, dependent):
        util.remove_from_set('article_display', self.make_key(dependee),
                             dependent)

    def delete(self, dependee):
        self.cache.delete(self.make_key(dependee))

    def delete_many(self, iterator):
        self.cache.delete_many([self.make_key(i) for i in iterator])

    def get(self, dependee):
        ret = util.get_set('article_display', self.make_key(dependee))
        if ret == set():
            return None
        return ret

    def get_union(self, iterator):
        ret = util.get_set_union('article_display',
                                 [self.make_key(i) for i in iterator])
        if ret == set():
            return None
        return ret

bibl = DependencyManager(u"bibl")
