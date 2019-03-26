# -*- encoding: utf-8 -*-
import os
from unittest import mock

import lxml.etree
from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import caches
from django.core.urlresolvers import reverse

from ..models import ChangeRecord, Entry
from bibliography.models import Item, PrimarySource
from .. import tasks, depman
from bibliography.tests import mock_zotero
from bibliography.tasks import fetch_items
from .util import launch_fetch_task, create_valid_article, \
    copy_entry, extract_inter_article_links, \
    extract_unlinked_terms
from lib.util import DisableMigrationsMixin

dirname = os.path.dirname(__file__)
cache = caches['article_display']

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

@override_settings(CELERY_TASK_ALWAYS_EAGER=True,
                   CELERY_BROKER_TRANSPORT='memory',
                   ROOT_URLCONF='lexicography.tests.urls')
class CachingTestCase(DisableMigrationsMixin, TestCase):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "views.json"))

    ps = None
    item = None

    def setUp(self):
        cache.clear()
        self.patch = mock.patch.multiple("bibliography.zotero.Zotero",
                                         get_all=get_all_mock,
                                         get_item=get_item_mock)
        self.patch.start()
        super(CachingTestCase, self).setUp()

        #
        # This ensures that pk=1 is taken out of circulation.
        #
        fake = Item()
        fake.save()
        fake.delete()

        #
        # We have to do this so that the item with pk=1 is reserved.
        #
        item = Item(pk=1, item_key="3",
                    uid=Item.objects.zotero.full_uid)
        item.save()
        fetch_items()
        self.item = Item.objects.get(pk=1)

    def tearDown(self):
        super(CachingTestCase, self).tearDown()
        self.patch.stop()

    def _create_bibl(self):
        self.ps = ps = PrimarySource(pk=1,
                                     item=self.item, reference_title="Foo",
                                     genre="SU")
        ps.save()

    def _generic_article_available(self, entries, op, expect_data):
        cache.clear()
        dep_keys = []

        for entry in entries:
            cr = entry.latest
            key = cr.c_hash.display_key("bibl")
            tasks.prepare_bibl.delay(cr.c_hash.c_hash).get()
            dep_keys.append(key)

        self.assertCountEqual(
            depman.bibl.get(self.item.abstract_url), dep_keys)
        self.assertCountEqual(depman.bibl.get(self.ps.abstract_url), dep_keys)

        op()

        for entry in entries:
            cr = entry.latest
            result = cache.get(entry.latest.c_hash.c_hash)
            if not expect_data:
                self.assertIsNone(
                    result,
                    ("there should no longer be information about "
                     "article {0} in the article_display cache")
                    .format(entry.lemma))
            else:
                self.assertIsNotNone(
                    result,
                    ("there should be information about "
                     "article {0} in the article_display cache")
                    .format(entry.lemma))

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

        def op():
            self.item.title += "bis"
            self.item.save()
            self.assertIsNone(
                depman.bibl.get(self.item.abstract_url),
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

        def op():
            self.ps.reference_title += "bis"
            self.ps.save()
            self.assertIsNone(
                depman.bibl.get(self.ps.abstract_url),
                "there should no longer be any dependency "
                "information regarding the item that has been "
                "changed")

        self._generic_article_available(entries, op, False)
