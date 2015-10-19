from unittest import TestCase

from lib import existdb

class ExistDBTest(TestCase):

    def setUp(self):
        self.assertTrue(existdb.running(),
                        "eXist has to be running already, just like this"
                        "application's DB backend")
        return super(ExistDBTest, self).setUp()

    def test_is_lucene_query_clean_with_clean_query(self):
        """
        A clean Lucene query returns a ``True`` value.
        """
        db = existdb.ExistDB()
        self.assertTrue(existdb.is_lucene_query_clean(db, "foo"))

    def test_is_lucene_query_clean_with_unclean_query(self):
        """
        An unclean Lucene query returns a ``False`` value.
        """
        db = existdb.ExistDB()
        self.assertFalse(existdb.is_lucene_query_clean(db, '"foo'))
