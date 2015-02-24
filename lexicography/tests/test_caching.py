# -*- encoding: utf-8 -*-
import os

import mock
import lxml.etree
from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import get_cache

from ..models import ChangeRecord, Entry
from bibliography.models import Item, PrimarySource
from .. import tasks, depman
from bibliography.tests import mock_zotero
from .util import launch_fetch_task, create_valid_article, \
    copy_entry, extract_inter_article_links, \
    extract_unlinked_terms

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

launch_fetch_task()

# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)

@mock.patch.multiple("bibliography.zotero.Zotero",
                     get_all=get_all_mock,
                     get_item=get_item_mock)
@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_ALWAYS_EAGER_PROPAGATES_EXCEPTIONS=True,
                   BROKER_BACKEND='memory')
class CachingTestCase(TestCase):
    fixtures = ["initial_data.json"] + local_fixtures
    ps = None
    item = None

    def setUp(self):
        get_cache('article_display').clear()
        super(CachingTestCase, self).setUp()

    def _create_bibl(self):
        # We need these.
        self.item = item = Item(pk=1, item_key="3",
                                uid=Item.objects.zotero.full_uid)
        item.save()
        self.ps = ps = PrimarySource(pk=1,
                                     item=self.item, reference_title="Foo",
                                     genre="SU")
        ps.save()

    def _generic_article_available(self, entries, op, expect_data):
        dep_keys = []

        for entry in entries:
            cr = entry.latest
            tasks.prepare_changerecord_for_display.delay(cr.pk).get()
            key = cr.article_display_key()
            dep_keys.append(key)
            result = cache.get(key)

            tree = lxml.etree.fromstring(result["xml"])
            refs_by_term = extract_inter_article_links(tree)

            expected = {
                'foo': '/lexicography/entry/2/',
                'abcd': '/lexicography/entry/1/'
            }

            if cr.lemma == u"prasāda copy":
                expected[u"prasāda"] = Entry.objects.get(
                    lemma=u"prasāda").get_absolute_url()

            self.assertEqual(refs_by_term,
                             expected,
                             "the article should have the right links")

            # Yes, we overwrite this with every iteration but it does
            # not matter.
            term = extract_unlinked_terms(tree)[0]

        self.assertItemsEqual(depman.lemma.get(term), dep_keys)
        self.assertItemsEqual(depman.bibl.get(self.item.url), dep_keys)
        self.assertItemsEqual(depman.bibl.get(self.ps.url), dep_keys)

        op(term)

        for entry in entries:
            cr = entry.latest
            result = cache.get(cr.article_display_key())
            if not expect_data:
                self.assertIsNone(
                    result,
                    (u"there should no longer be information about "
                     u"article {0} in the article_display cache")
                    .format(entry.lemma))
            else:
                self.assertIsNotNone(
                    result,
                    (u"there should be information about "
                     u"article {0} in the article_display cache")
                    .format(entry.lemma))

    def test_article_added(self):
        """
        Adding an article removes from the cache the articles
        that depend on it.
        """
        self._create_bibl()

        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        def op(term):
            # An article is created for the term we've saved, which
            # should trigger invalidation of the cache for the two
            # entries.
            new_entry = Entry()
            new_entry.update(
                orig.latest.user,
                "q",
                orig.latest.c_hash,
                term,
                ChangeRecord.CREATE,
                ChangeRecord.MANUAL)

            self.assertIsNone(
                depman.lemma.get(term),
                "there should no longer be any dependency "
                "information regarding the term that has been "
                "added")

        self._generic_article_available(entries, op, False)

    def test_article_undeleted(self):
        """
        Adding an article removes from the cache the articles
        that depend on it.
        """

        self._create_bibl()
        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        cr = orig.latest
        tasks.prepare_changerecord_for_display.delay(cr.pk).get()
        result = cache.get(cr.article_display_key())

        tree = lxml.etree.fromstring(result["xml"])
        term = extract_unlinked_terms(tree)[0]

        new_entry = Entry()
        new_entry.update(
            orig.latest.user,
            "q",
            orig.latest.c_hash,
            term,
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        new_entry.mark_deleted(orig.latest.user)

        # Clear the cache so that we start from a blank state.
        get_cache('article_display').clear()

        def op(_term):
            new_entry.undelete(orig.latest.user)

            self.assertIsNone(
                depman.lemma.get(term),
                "there should no longer be any dependency "
                "information regarding the term that has been "
                "added")

        self._generic_article_available(entries, op, False)

    def test_article_deleted(self):
        """
        Deleting an article removes from the cache the articles
        that depend on it.
        """

        self._create_bibl()
        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        # Clear the cache so that we start from a blank state.
        get_cache('article_display').clear()

        def op(_term):
            foo = Entry.objects.get(lemma="foo")
            foo.mark_deleted(orig.latest.user)

            self.assertIsNone(
                depman.lemma.get("foo"),
                "there should no longer be any dependency "
                "information regarding the term that has been "
                "removed")

        self._generic_article_available(entries, op, False)

    def test_article_published(self):
        """
        Publishing an article removes from the cache the articles
        that depend on it.
        """

        self._create_bibl()
        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        # Clear the cache so that we start from a blank state.
        get_cache('article_display').clear()

        def op(_term):
            foo = Entry.objects.get(lemma="foo")
            foo.latest.c_hash._valid = True
            foo.latest.c_hash.save()
            self.assertTrue(foo.latest.publish(foo.latest.user))

            self.assertIsNone(
                depman.lemma.get("foo"),
                "there should no longer be any dependency "
                "information regarding the term that has been "
                "published")

        self._generic_article_available(entries, op, False)

    def test_article_published_again(self):
        """
        Republishing an article does not from the cache the articles
        that depend on it.
        """

        self._create_bibl()
        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        foo = Entry.objects.get(lemma="foo")
        foo.latest.c_hash._valid = True
        foo.latest.c_hash.save()
        self.assertTrue(foo.latest.publish(foo.latest.user))

        # Clear the cache so that we start from a blank state.
        get_cache('article_display').clear()

        def op(_term):
            foo = Entry.objects.get(lemma="foo")
            foo.update(
                orig.latest.user,
                "q",
                orig.latest.c_hash,
                foo.lemma,
                ChangeRecord.UPDATE,
                ChangeRecord.MANUAL)
            self.assertTrue(foo.latest.publish(foo.latest.user))
            self.assertIsNotNone(
                depman.lemma.get("foo"),
                "there should be dependency "
                "information regarding the term that has been "
                "published")

        self._generic_article_available(entries, op, True)

    def test_article_unpublished(self):
        """
        Publishing an article removes from the cache the articles
        that depend on it.
        """

        self._create_bibl()
        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        foo = Entry.objects.get(lemma="foo")
        foo.latest.c_hash._valid = True
        foo.latest.c_hash.save()
        self.assertTrue(foo.latest.publish(foo.latest.user))

        # Clear the cache so that we start from a blank state.
        get_cache('article_display').clear()

        def op(_term):
            foo = Entry.objects.get(lemma="foo")
            self.assertTrue(foo.latest.unpublish(foo.latest.user))
            self.assertIsNone(
                depman.lemma.get("foo"),
                "there should no longer be any dependency "
                "information regarding the term that has been "
                "published")

        self._generic_article_available(entries, op, False)

    def test_article_incomplete_unpublish(self):
        """
        Unpublishing a change record of an article does not from the cache
        the articles that depend on it, when there is another change
        record which *is* published.
        """

        self._create_bibl()
        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        foo = Entry.objects.get(lemma="foo")
        foo.latest.c_hash._valid = True
        foo.latest.c_hash.save()
        self.assertTrue(foo.latest.publish(foo.latest.user))

        foo = Entry.objects.get(lemma="foo")
        foo.update(
            orig.latest.user,
            "q",
            orig.latest.c_hash,
            foo.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        self.assertTrue(foo.latest.publish(foo.latest.user))
        foo = Entry.objects.get(lemma="foo")

        # Clear the cache so that we start from a blank state.
        get_cache('article_display').clear()

        def op(_term):
            self.assertTrue(foo.latest.unpublish(foo.latest.user))
            self.assertIsNotNone(
                depman.lemma.get("foo"),
                "there should be dependency "
                "information regarding the term that has been "
                "published")

        self._generic_article_available(entries, op, True)

    def test_item_changed(self):
        """
        Changing a bibliographical item invalidates the articles that
        depend on it.
        """
        self._create_bibl()

        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        def op(term):
            self.item.title += "bis"
            self.item.save()
            self.assertIsNone(
                depman.bibl.get(self.item.url),
                "there should no longer be any dependency "
                "information regarding the item that has been "
                "changed")

        self._generic_article_available(entries, op, False)

    def test_primary_source_changed(self):
        """
        Changing a bibliographical item invalidates the articles that
        depend on it.
        """
        self._create_bibl()

        # We'll have two articles with the same dependencies.
        orig = create_valid_article()
        copy = copy_entry(orig)

        entries = [orig, copy]

        def op(term):
            self.ps.reference_title += "bis"
            self.ps.save()
            self.assertIsNone(
                depman.bibl.get(self.ps.url),
                "there should no longer be any dependency "
                "information regarding the item that has been "
                "changed")

        self._generic_article_available(entries, op, False)
