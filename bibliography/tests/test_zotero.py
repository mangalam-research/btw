import logging.handlers
import logging
import mock
from unittest import skip
import urllib2

from django.core.cache import get_cache
from django.test import TestCase

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true
from .util import TestMeta, replay, record
from .. import zotero
from ..zotero import Zotero, zotero_settings, logger

# Turn on long messages. This will apply to all assertions unless turned off
# somewhere else.
assert_equal.im_self.longMessage = True


class ListHandler(logging.Handler):

    def __init__(self, level=logging.NOTSET, capacity=100):
        logging.Handler.__init__(self, level)
        self.records = []
        self.capacity = capacity

    def emit(self, record):
        self.records.append(self.format(record))
        if len(self.records) > self.capacity:
            del self.records[0]

logger.addHandler(ListHandler())


class ReturnMock(mock.MagicMock):

    def __init__(self, *args, **kwargs):
        super(ReturnMock, self).__init__(*args, **kwargs)

        #
        # This rigmarole is needed because mock won't automatically handle the
        # "magic" methods.
        #
        wraps = kwargs['wraps']
        if hasattr(wraps, "__contains__"):
            self.__contains__ = ReturnMock(wraps=wraps.__contains__)

        self.values_returned = []

    def __call__(self, *args, **kwargs):
        ret = super(ReturnMock, self).__call__(*args, **kwargs)
        self.values_returned.append(ret)
        return ret


orig_cache = zotero.cache


@mock.patch("bibliography.zotero.cache", wraps=orig_cache,
            new_callable=ReturnMock)
class ZoteroTest(TestCase):
    __metaclass__ = TestMeta

    def __init__(self, *args, **kwargs):
        super(ZoteroTest, self).__init__(*args, **kwargs)
        self.zotero = Zotero(zotero_settings(), 'BTW Library')
        self.longMessage = True

    def setUp(self):
        get_cache('bibliography').clear()

    def assert_miss(self, mock_cache, number_of_sets):
        assert_equal(mock_cache.__contains__.call_count, 1,
                     "the cache should have been checked")
        assert_equal(mock_cache.__contains__.values_returned,
                     [False], "the check should have been a miss")

        assert_equal(mock_cache.get.call_count, 0, "it was a miss")

        assert_equal(mock_cache.set.call_count, number_of_sets, "cache set")

    @replay
    def test_search_no_hit(self, mock_cache):
        """Tests a search with no hits."""
        results, extras = self.zotero.search("%%%$$$%%%")
        assert_equal(len(results), 0)
        assert_equal(len(extras), 0)

        self.assert_miss(mock_cache, 1)

    @replay
    def test_search_hit(self, mock_cache):
        """
        Tests a search with hits saves results in the cache.
        """
        results, extras = self.zotero.search("dharma")
        nr_hits = 5
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        self.assert_miss(mock_cache, nr_hits + 1)

    @replay
    def test_search_again(self, mock_cache):
        """
        Search gets results from the cache.
        """
        results, extras = self.zotero.search("dharma")
        nr_hits = 5
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        self.assert_miss(mock_cache, nr_hits + 1)

        # We repeat the search and check that the results are obtained
        # from the cache.
        results, extras = self.zotero.search("dharma")
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        assert_equal(mock_cache.__contains__.call_count, 2,
                     "the cache should have been checked")
        assert_equal(mock_cache.__contains__.values_returned,
                     [False, True], "sequence of key checks")

        assert_equal(mock_cache.get.call_count, 1,
                     "cache should have been hit")

        # The cache should not be set again. We got a hit, and the
        # data was not changed.
        assert_equal(mock_cache.set.call_count, nr_hits + 1, "cache set")

    @replay
    def test_search_obsolete(self, mock_cache):
        """
        Tests that obsolete cache data is purged. Upon reading data from
        the cache, the library checks the version number of that
        data. If it is older than the latest version, the data is
        purged from the cache.
        """
        results, extras = self.zotero.search("dharma")
        nr_hits = 5
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        self.assert_miss(mock_cache, nr_hits + 1)

        #
        # We change the version number of the entry. We use orig_cache
        # to bypass the mock.
        #
        key = mock_cache.__contains__.call_args_list[0][0][0]
        data = list(orig_cache.get(key))
        data[0] = -1
        orig_cache.set(key, tuple(data))

        # We repeat the search and check that the results are obtained
        # from the cache.
        results, extras = self.zotero.search("dharma")
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        assert_equal(mock_cache.__contains__.call_count, 2,
                     "the cache should have been checked")
        assert_equal(mock_cache.__contains__.values_returned,
                     [False, True], "sequence of key checks")

        assert_equal(mock_cache.get.call_count, 1,
                     assert_equal(mock_cache.get.call_count, 1,
                                  "cache should have been hit"))

        #
        # The cache is set again because the entry was deemed
        # obsolete.
        #
        assert_equal(mock_cache.set.call_count, (nr_hits + 1) * 2, "cache set")

    @replay
    def test_search_corrupt(self, mock_cache):
        """
        Tests that corrupt cache data is purged. The library expects each
        entry to consist of a tuple. If it is not a tuple, it deems
        the data corrupt and purges it from the cache.
        """
        results, extras = self.zotero.search("dharma")
        nr_hits = 5
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        self.assert_miss(mock_cache, nr_hits + 1)

        #
        # We set the entry to `True`. We use orig_cache to bypass the
        # mock.
        #
        key = mock_cache.__contains__.call_args_list[0][0][0]
        orig_cache.set(key, True)

        # We repeat the search and check that the results are obtained
        # from the cache.
        results, extras = self.zotero.search("dharma")
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        assert_equal(mock_cache.__contains__.call_count, 2,
                     "the cache should have been checked")
        assert_equal(mock_cache.__contains__.values_returned,
                     [False, True], "sequence of key checks")

        assert_equal(mock_cache.get.call_count, 1,
                     "cache should have been hit")

        #
        # The cache is set again because the entry was deemed corrupt.
        #
        assert_equal(mock_cache.set.call_count, (nr_hits + 1) * 2, "cache set")

    @replay
    def test_search_modified(self, mock_cache):
        """
        Tests that if the data has been modified at the Zotero server, new
        data is fetched.
        """
        results, extras = self.zotero.search("dharma")
        nr_hits = 5
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        self.assert_miss(mock_cache, nr_hits + 1)

        #
        # Here we patch urlopen to set `If-Modified-Since-Version` to
        # something ridiculous to simulate a case where the data would
        # have changed on the server side.
        #
        orig_urlopen = urllib2.urlopen

        def se(*args, **kwargs):
            args[0].add_header("If-Modified-Since-Version", "-1")
            ret = orig_urlopen(*args, **kwargs)
            assert_equal(ret.code, 200, "status should be 200")
            return ret

        with mock.patch("bibliography.zotero.urllib2.urlopen",
                        new=mock.Mock(side_effect=se)):
            results, extras = self.zotero.search("dharma")

        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        assert_equal(mock_cache.__contains__.call_count, 2,
                     "the cache should have been checked")
        assert_equal(mock_cache.__contains__.values_returned,
                     [False, True], "sequence of key checks")

        assert_equal(mock_cache.get.call_count, 1,
                     "cache should have been hit")

        #
        # The cache is set again because the server returned new data.
        #
        assert_equal(mock_cache.set.call_count, (nr_hits + 1) * 2, "cache set")

    @replay
    def test_get_item_after_search(self, mock_cache):
        """
        Tests that if the a get_item seeks an item which has been returned
        by a previous search, this item is taken from the cache.
        """
        results, extras = self.zotero.search("dharma")
        nr_hits = 5
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        self.assert_miss(mock_cache, nr_hits + 1)

        item = self.zotero.get_item(results[0]["itemKey"])
        assert_equal(item, results[0])

        assert_equal(mock_cache.__contains__.values_returned,
                     [False, True], "sequence of key checks")

        assert_equal(mock_cache.get.call_count, 1,
                     "cache should have been hit")

        assert_equal(mock_cache.set.call_count, nr_hits + 1,
                     "the cache should not have been set")

    @replay
    def test_get_all(self, mock_cache):
        """
        Tests that get_all gets all records.
        """
        results, extras = self.zotero.get_all()
        nr_hits = 47
        assert_equal(len(results), nr_hits)
        assert_equal(len(extras), nr_hits)

        self.assert_miss(mock_cache, nr_hits + 1)
