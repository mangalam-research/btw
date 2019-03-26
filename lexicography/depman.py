from lib import util
from django.core.cache import caches

class DependencyManager(object):
    """
    A dependency manager meant to record the dependencies of cache
    keys. Instance of this class will create new cache entries that
    record these dependencies.

    For the sake of this class, a "dependee" is anything that uniquely
    identifies a resource. For instance, it could be the id of a
    database object, or a URL.

    A "dependent" is anything that uniquely identifies a resource that
    must be recomputed if its "dependee" changes. It could be a cache
    key (which is often the case) or any other unique identifier.

    :param prefix: A prefix to use for keys created by this instance.

    :type prefix: :class:`str`
    """

    def __init__(self, prefix):
        self.prefix = prefix
        self.cache = caches['article_display']

    def make_key(self, key):
        """
        Create the key name to use for recording the depenencies of ``key``.

        :param key: The key to start with. This is normally the key
                    used by the ``dependee`` parameters of the other
                    methods in this class.

        :type key: :class:`str`

        :returns: The key to be used to find the dependencies in the cache.
        :rtype: :class:`str`
        """
        return self.prefix + ":" + key

    def record(self, dependee, dependent):
        """
        Record that the cache key ``dependent`` depends on
        ``dependee``.
        """
        util.add_to_set('article_display', self.make_key(dependee),
                        dependent)

    def remove(self, dependee, dependent):
        """
        Remove ``dependent`` from the list of dependents of ``dependee``.
        """
        util.remove_from_set('article_display', self.make_key(dependee),
                             dependent)

    def delete(self, dependee):
        """
        Remove all dependency information regarding ``dependee``.
        """
        self.cache.delete(self.make_key(dependee))

    def delete_many(self, iterator):
        """
        Remove all dependency information regarding a collection of
        dependees. This method uses the ``delete_many`` functionality
        of the cache.

        :param iterator: This must iterate over a series of dependees.
        """
        self.cache.delete_many([self.make_key(i) for i in iterator])

    def get(self, dependee):
        """
        Get all dependents of ``dependee``.

        :returns: A set of dependents. Will return ``None`` if the set
        is empty.
        """
        ret = util.get_set('article_display', self.make_key(dependee))
        if ret == set():
            return None
        return ret

    def get_union(self, iterator):
        """
        Get the union of all the dependents of a set of dependees.

        :param iterator: This must iterate over a series of dependees.

        :returns: A set of dependents. Will return ``None`` if the set
        is empty.
        """
        ret = util.get_set_union('article_display',
                                 [self.make_key(i) for i in iterator])
        if ret == set():
            return None
        return ret

bibl = DependencyManager("bibl")
