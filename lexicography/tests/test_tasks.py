import os

import mock
import lxml.etree
from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import get_cache
from django.contrib.auth import get_user_model

from ..models import ChangeRecord, Entry
from bibliography.models import Item, PrimarySource
from .. import tasks, depman
from lib.util import WithStringIO
from bibliography.tests import mock_zotero
from bibliography.tasks import fetch_items
from .util import launch_fetch_task, create_valid_article, \
    extract_inter_article_links

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json"))

cache = get_cache('article_display')

mock_records = mock_zotero.Records([
    {
        "data":
        {
            "key": "1",
            "title": "Title 1",
            "date": "Date 1",
            "creators": [
                {"name": "Abelard (Name 1 for Title 1)"},
                {"firstName": "FirstName 2 for Title 1",
                 "lastName": "LastName 2 for Title 1"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "2",
            "title": "Title 2",
            "date": "Date 2",
            "creators": [
                {"name": "Beth (Name 1 for Title 2)"},
                {"firstName": "FirstName 2 for Title 2",
                 "lastName": "LastName 2 for Title 2"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo2.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "3",
            "title": "Title 3",
            "date": "Date 3",
            "creators": [
                {"name": "Zeno (Name 1 for Title 3)"},
                {"firstName": "FirstName 2 for Title 3",
                 "lastName": "LastName 2 for Title 3"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo3.com",
                "type": "text/html"
            }
        }
    }
])

# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)

@mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                     get_item=get_item_mock)
@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_ALWAYS_EAGER_PROPAGATES_EXCEPTIONS=True,
                   BROKER_BACKEND='memory')
class TasksTestCase(TestCase):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        get_cache('article_display').clear()
        super(TasksTestCase, self).setUp()

    def assertDependsOn(self, cr, man, name):
        result = man.get(name)
        self.assertItemsEqual(
            result,
            [cr.article_display_key()],
            "the change record should depend on " + name)

    def assertDependsOnLemma(self, cr, name):
        self.assertDependsOn(cr, depman.lemma, name)

    def assertDependsOnBibl(self, cr, name):
        self.assertDependsOn(cr, depman.bibl, name)

    def test_prepare_changerecord_for_display_no_links(self):
        """
        Tests that the result of the task is the same as the original
        data when there are no references to other articles
        in the change record.
        """
        fetch_items()
        tasks.prepare_changerecord_for_display.delay(1).get()

        cr = ChangeRecord.objects.get(pk=1)
        # Check that the correct results are in the cache
        result = cache.get(cr.article_display_key())
        self.assertEqual(result["xml"], cr.c_hash.data,
                         "the xml should be the same as the "
                         "original")
        self.assertEqual(result["bibl_data"], {},
                         "the bibl data should be empty")
        self.assertIsNone(
            cache.get(cr.article_display_key(not cr.published)),
            "there should not be a record for a change record in a "
            "different published state")

    def test_prepare_changerecord_for_display_candidates_no_links(self):
        """
        Tests that the result of the task is the same as the original
        data when there are only references to non-existing articles
        in the change record.

        """
        cr = Entry.objects.get(
            lemma="antonym with citations, followed by another "
            "antonym").latest

        tasks.prepare_changerecord_for_display.delay(cr.pk).get()

        # Check that the correct results are in the cache.
        result = cache.get(cr.article_display_key())
        self.assertEqual(result["xml"], cr.c_hash.data,
                         "the result should be the same as the "
                         "original data")
        self.assertEqual(result["bibl_data"], {},
                         "the bibl data should be empty")
        self.assertIsNone(
            cache.get(cr.article_display_key(not cr.published)),
            "there should not be a record for a change record in a "
            "different published state")

        # Check that the dependencies have been set for the two terms
        # in the article.
        for item in ("antonym 1", "antonym 2"):
            self.assertDependsOnLemma(cr, item)

    def test_prepare_changerecord_for_display_bibliography(self):
        """
        Tests the bibliographical results.

        """
        # This ensures that pk 2 is free when we use it next.
        for _ in range(1, 3):
            fake = Item(item_key="1")
            fake.save()
            fake.delete()

        # This reserves pk=2 for our item.
        item = Item(pk=2, item_key="1")
        item.save()
        fetch_items()
        # We have to refetch it with the correct data.
        item = Item.objects.get(pk=2)

        cr = Entry.objects.get(
            lemma="citations everywhere possible (subsense)").latest

        tasks.prepare_changerecord_for_display.delay(cr.pk).get()

        # Check that the correct results are in the cache.
        result = cache.get(cr.article_display_key())
        self.assertEqual(result["xml"], cr.c_hash.data,
                         "the result should be the same as the "
                         "original self")
        self.assertEqual(result["bibl_data"], {
            "/bibliography/2": item.as_dict()
        }, "the bibl_data should be correct.")

        # Check that the dependency of this article on
        # "/bibliography/2" has been recorded in the cache.
        for item in result["bibl_data"].iterkeys():
            self.assertDependsOnBibl(cr, item)

        self.assertIsNone(
            cache.get(cr.article_display_key(not cr.published)),
            "there should not be a record for a change record in a "
            "different published state")

    def test_complex_document(self):
        # Yeah, we launch it here. The other tests don't need this
        # data so...
        launch_fetch_task()
        entry = create_valid_article()

        item = Item(pk=1,
                    item_key="3",
                    uid=Item.objects.zotero.full_uid)
        item.save()
        ps = PrimarySource(pk=1,
                           item=item,
                           reference_title="Foo",
                           genre="SU")
        ps.save()

        cr = entry.latest
        tasks.prepare_changerecord_for_display.delay(cr.pk).get()

        # Check that the correct results are in the cache.
        result = cache.get(cr.article_display_key())
        tree = lxml.etree.fromstring(result["xml"])
        refs_by_term = extract_inter_article_links(tree)

        self.assertEqual(refs_by_term,
                         {
                             'foo': '/lexicography/entry/2/',
                             'abcd': '/lexicography/entry/1/'
                         },
                         "the article should have the right links")

        self.assertEqual(
            result["bibl_data"],
            {'/bibliography/1': item.as_dict(),
             '/bibliography/primary-sources/1': ps.as_dict()},
            "the bibl data should be correct")

        # Check that the dependency of this article on
        # "/bibliography/1" has been recorded in the cache.
        for item in result["bibl_data"].iterkeys():
            self.assertDependsOnBibl(cr, item)

        for item in refs_by_term.iterkeys():
            self.assertDependsOnLemma(cr, item)

    def assertLogRegexp(self, handler, stream, regexp):
        handler.flush()
        self.assertRegexpMatches(stream.getvalue(), regexp)

    def test_prepare_changerecord_for_display_already_set(self):
        """
        Tests that if the key is already set, we do not recalculate
        it.
        """
        tasks.prepare_changerecord_for_display.delay(1).get()
        with WithStringIO(tasks.logger) as (stream, handler):
            tasks.prepare_changerecord_for_display.delay(1).get()
            self.assertLogRegexp(
                handler,
                stream,
                "^5af6712b87152507c264a550171d2045936bb64d"
                "_True is set; ending task.$")

    def test_prepare_changerecord_for_display_vanish(self):
        """
        Tests that if a task is already in progress, new tasks stop
        running early.
        """
        tasks.prepare_changerecord_for_display.delay(
            1,
            test={"vanish": True}).get()
        with WithStringIO(tasks.logger) as (stream, handler):
            tasks.prepare_changerecord_for_display.delay(1).get()
            self.assertLogRegexp(
                handler,
                stream,
                "^5af6712b87152507c264a550171d2045936bb64d"
                "_True is being processed by (?:.*?); ending task.$")

    def test_prepare_changerecord_for_display_fail(self):
        """
        Tests that a catastrophic failure does not leave a
        record in the cache.
        """
        try:
            tasks.prepare_changerecord_for_display.delay(
                1,
                test={"fail": True}).get()
        except Exception as ex:  # pylint: disable=broad-except
            self.assertEqual(str(ex), "failing")

        cr = ChangeRecord.objects.get(pk=1)
        self.assertIsNone(
            cache.get(cr.article_display_key()),
            "there should not be any information recorded in "
            "the cache for this change record")
