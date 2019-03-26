# -*- encoding: utf-8 -*-
import os

import mock
import lxml.etree
from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import caches
from django.core.urlresolvers import reverse
from pyexistdb.exceptions import ExistDBException

from ..models import Chunk, ChangeRecord, Entry
from .. import tasks, depman, xml
from .util import launch_fetch_task, create_valid_article, \
    extract_inter_article_links
from bibliography.models import Item, PrimarySource
from bibliography.tests import mock_zotero
from bibliography.tasks import fetch_items
from lib.util import WithStringIO, DisableMigrationsMixin
from lib.testutil import wipd
from lib.existdb import ExistDB, get_collection_path

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

hte_fixture = os.path.join(
    dirname, "..", "..", "semantic_fields", "tests", "fixtures", "hte.json")

# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)

@override_settings(CELERY_TASK_ALWAYS_EAGER=True,
                   CELERY_BROKER_TRANSPORT='memory',
                   ROOT_URLCONF='lexicography.tests.urls')
class TaskTestCase(DisableMigrationsMixin, TestCase):

    def assertLogRegexp(self, handler, stream, regexp):
        handler.flush()
        self.assertRegex(stream.getvalue(), regexp)

    def check_already_set(self):
        cr = ChangeRecord.objects.get(pk=1)
        chunk = cr.c_hash
        self.task.delay(chunk.c_hash).get()
        with WithStringIO(tasks.logger) as (stream, handler):
            self.task.delay(chunk.c_hash).get()
            self.assertLogRegexp(
                handler,
                stream,
                "^{0} is set; ending task.$".format(
                    chunk.display_key(self.kind)))

    def check_vanish(self):
        cr = ChangeRecord.objects.get(pk=1)
        chunk = cr.c_hash
        cache.clear()
        self.task.delay(chunk.c_hash, test={"vanish": True}).get()
        with WithStringIO(tasks.logger) as (stream, handler):
            self.task.delay(chunk.c_hash).get()
            self.assertLogRegexp(
                handler,
                stream,
                "^{0} is held by (?:.*?); ending task.$".format(
                    chunk.display_key(self.kind)))

    def check_fail(self):
        cr = ChangeRecord.objects.get(pk=1)
        chunk = cr.c_hash
        try:
            self.task.delay(chunk.c_hash, test={"fail": True}).get()
        except Exception as ex:  # pylint: disable=broad-except
            self.assertEqual(str(ex), "failing")
        else:
            self.assertFalse("did not fail!")

        self.assertIsNone(
            cache.get(chunk.display_key(self.kind)),
            "there should not be any information recorded in "
            "the cache for this change record")


class PrepareXMLTestCase(TaskTestCase):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "views.json")) + [hte_fixture]
    maxDiff = None
    kind = "xml"
    task = tasks.prepare_xml

    def setUp(self):
        cache.clear()
        super(PrepareXMLTestCase, self).setUp()

    def test_complex_document(self):
        # Yeah, we launch it here. The other tests don't need this
        # data so...
        launch_fetch_task()
        entry = create_valid_article()

        cr = entry.latest
        chunk = cr.c_hash
        tasks.prepare_xml.delay(chunk.c_hash).get()

        # Check that the correct results are in the cache.
        result = cache.get(chunk.display_key("xml"))
        db = ExistDB()
        self.assertTrue(db.hasDocument(chunk.exist_path("display")))
        tree = lxml.etree.fromstring(result)

        senses = tree.xpath(
            "/btw:entry/btw:sense-discrimination/btw:sense",
            namespaces=xml.default_namespace_mapping)
        self.assertEqual(len(senses), 4)

        expected_values = [
            [
                "01.02.11n",
                "Person (01.04.04n)",
                "01.04.08n",
                "01.05.05.09.01n",
                "01.06.07.03n",
                "Beautification (02.02.18n)",
                "Lack of beauty (02.02.19n)",
                "Written laws (03.05.01n)",
            ],
            [
                "Belief (02.01.13n)",
                "Belief, trust, confidence (02.01.13.02n)",
                "Act of convincing, conviction (02.01.13.02.02n)",
                "Absence of doubt, confidence (02.01.13.08.11n)",
                "Making certain, assurance (02.01.13.08.11.01.01n)",
                "Expectation (02.01.14n)",
                "02.01.17n",
                "Good taste (02.02.12n)",
                "Bad taste (02.02.13n)",
                "Fashionableness (02.02.14n)",
                "02.02.22n",
                "Education (03.07n)",
            ],
            [
                "01.05.05.12.01n"
            ],
            [
                "02.01.17n",
                "Good taste (02.02.12n)",
                "Bad taste (02.02.13n)",
                "03.07.00.23n",
                "Learning (03.07.03n)"
            ],
        ]

        for ix, (sense, expected) in enumerate(zip(senses, expected_values)):
            sense_label = "sense " + str(ix + 1)
            sfss = sense.xpath("./btw:semantic-fields",
                               namespaces=xml.default_namespace_mapping)
            self.assertEqual(len(sfss), 1,
                             "there should be only one btw:semantic-fields "
                             "in " + sense_label)
            sfs = [sf.text for sf in sfss[0]]
            self.assertEqual(sfs, expected,
                             "the list of semantic fields should be correct "
                             "in " + sense_label)

        sfss = tree.xpath("/btw:entry/btw:overview/btw:semantic-fields",
                          namespaces=xml.default_namespace_mapping)
        self.assertEqual(len(sfss), 1,
                         "there should be only one btw:semantic-fields "
                         "element")
        sfs = [sf.text for sf in sfss[0]]
        self.assertEqual(sfs, [
            "01.02.11n",
            "Person (01.04.04n)",
            "01.04.08n",
            "By eating habits (01.05.05n)",
            "01.06.07n",  # By family relationships ,
            "Belief (02.01.13n)",
            "Expectation (02.01.14n)",
            "02.01.17n",
            "Good taste (02.02.12n)",
            "Bad taste (02.02.13n)",
            "Fashionableness (02.02.14n)",
            "Beautification (02.02.18n)",
            "Lack of beauty (02.02.19n)",
            "02.02.22n",
            "Written laws (03.05.01n)",
            "Education (03.07n)",
            "03.07.00n",
            "Learning (03.07.03n)"
        ],
            "the list of semantic fields should be correct")
        self.assertIsNone(sfss[0].getnext())

@mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                     get_item=get_item_mock)
class PrepareBiblTestCase(TaskTestCase):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "views.json")) + [hte_fixture]
    maxDiff = None
    kind = "bibl"
    task = tasks.prepare_bibl

    def setUp(self):
        cache.clear()
        super(PrepareBiblTestCase, self).setUp()

    def assertDependsOn(self, chunk, man, name):
        result = man.get(name)
        key = chunk.display_key("bibl")
        self.assertCountEqual(result,
                              [key],
                              "the change record should depend on " + name)

    def assertDependsOnBibl(self, cr, name):
        self.assertDependsOn(cr, depman.bibl, name)

    def test_no_bibl(self):
        """
        Tests that data for which we have no bibliographical information
        results is an empty ``bibl_data``.
        """

        cr = Entry.objects.get(
            lemma="antonym with citations, followed by another "
            "antonym").latest
        chunk = cr.c_hash

        tasks.prepare_bibl.delay(chunk.c_hash).get()

        # Check that the correct results are in the cache.
        result = cache.get(chunk.display_key("bibl"))
        self.assertEqual(result, {}, "the bibl data should be empty")

    def test_bibliography(self):
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
        chunk = cr.c_hash

        tasks.prepare_bibl.delay(chunk.c_hash).get()

        # Check that the correct results are in the cache.
        result = cache.get(chunk.display_key("bibl"))
        self.assertEqual(result, {
            "/bibliography/2": item.as_dict()
        }, "the bibl_data should be correct.")

        # Check that the dependency of this article on
        # "/bibliography/2" has been recorded in the cache.
        for item in result.keys():
            self.assertDependsOnBibl(chunk, item)

    def test_complex_document(self):
        # Yeah, we launch it here. The other tests don't need this
        # data so...
        launch_fetch_task()
        item = Item(pk=1,
                    item_key="3",
                    uid=Item.objects.zotero.full_uid)
        item.save()
        ps = PrimarySource(pk=1,
                           item=item,
                           reference_title="Foo",
                           genre="SU")
        ps.save()

        entry = create_valid_article()

        cr = entry.latest
        chunk = cr.c_hash
        self.assertFalse(chunk.published)
        tasks.prepare_bibl.delay(chunk.c_hash).get()

        # Check that the correct results are in the cache.
        result = cache.get(chunk.display_key("bibl"))
        self.assertEqual(
            result,
            {'/bibliography/1': item.as_dict(),
             '/bibliography/primary-sources/1': ps.as_dict()},
            "the bibl data should be correct")

        # Check that the dependency of this article on
        # "/bibliography/1" has been recorded in the cache.
        for item in result.keys():
            self.assertDependsOnBibl(chunk, item)

    def test_already_set(self):
        """
        Tests that if the key is already set, we do not recalculate
        it.
        """
        self.check_already_set()

    def test_vanish(self):
        """
        Tests that if a task is already in progress, new tasks stop
        running early.
        """
        self.check_vanish()

    def test_fail(self):
        """
        Tests that a catastrophic failure does not leave a
        record in the cache.
        """
        self.check_fail()

class FetchXMLTestCase(TaskTestCase):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "views.json")) + [hte_fixture]

    def setUp(self):
        Chunk.objects.prepare("xml", True)
        super(FetchXMLTestCase, self).setUp()

    def test_no_data_nowhere(self):
        """
        When both the cache and eXist do not have the data. Return ``None``.
        """
        cr = ChangeRecord.objects.get(pk=1)
        chunk = cr.c_hash
        key = chunk.display_key("xml")
        self.assertIsNotNone(cache.get(key))

        cache.delete(key)
        chunk.chunkmetadata.delete()
        self.assertIsNone(tasks.fetch_xml(chunk.c_hash))
        self.assertIsNone(cache.get(key))

    def test_no_exist_document(self):
        """
        When the exist document is missing, raise an error. We want an
        error because it indicates something really broken about our
        internal state. We should never have metadata without a
        corresponding XML file.
        """
        cr = ChangeRecord.objects.get(pk=1)
        chunk = cr.c_hash
        self.assertIsNotNone(cache.get(chunk.display_key("xml")))

        cache.clear()
        db = ExistDB()
        db.removeCollection(get_collection_path("display"), True)

        with self.assertRaises(ExistDBException):
            tasks.fetch_xml(chunk.c_hash)

    def test_cached(self):
        """
        When the data is cached, return that. Do not contact eXist.
        """
        cr = ChangeRecord.objects.get(pk=1)
        chunk = cr.c_hash
        key = chunk.display_key("xml")
        cached = cache.get(key)
        self.assertIsNotNone(cached)

        with mock.patch('lexicography.models.ExistDB.getDocument') as get_mock:
            self.assertEqual(tasks.fetch_xml(chunk.c_hash), cached)
            self.assertEqual(cache.get(key), cached)
            self.assertEqual(get_mock.call_count, 0)

    def test_not_cached(self):
        """
        When the data is not cached, get it from eXist.
        """
        cr = ChangeRecord.objects.get(pk=1)
        chunk = cr.c_hash
        key = chunk.display_key("xml")
        xml_doc = cache.get(key)
        _, xml_doc = xml.strip_xml_decl(xml_doc)
        self.assertIsNotNone(xml)

        db = ExistDB()
        cache.delete(key)
        with mock.patch('lexicography.models.ExistDB.getDocument',
                        wraps=db.getDocument) as get_mock:
            self.assertEqual(tasks.fetch_xml(chunk.c_hash), xml_doc)
            self.assertEqual(cache.get(key), xml_doc)
            self.assertEqual(get_mock.call_count, 1)
