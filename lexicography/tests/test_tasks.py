# -*- encoding: utf-8 -*-
import os
import re

import mock
import lxml.etree
from django.test import TestCase
from django.test.utils import override_settings
from django.core.cache import caches
from django.core.urlresolvers import reverse

from ..models import ChangeRecord, Entry
from bibliography.models import Item, PrimarySource
from .. import tasks, depman, xml
from lib.util import WithStringIO
from bibliography.tests import mock_zotero
from bibliography.tasks import fetch_items
from .util import launch_fetch_task, create_valid_article, \
    extract_inter_article_links

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

# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)

@mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                     get_item=get_item_mock)
@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_ALWAYS_EAGER_PROPAGATES_EXCEPTIONS=True,
                   BROKER_BACKEND='memory',
                   ROOT_URLCONF='lexicography.tests.urls')
class TasksTestCase(TestCase):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "views.json"))

    def setUp(self):
        cache.clear()
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
        tree = lxml.etree.fromstring(result["xml"].encode("utf8"))
        self.assertEqual(len(extract_inter_article_links(tree)), 0,
                         "the xml should not contain any article links")
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
        tree = lxml.etree.fromstring(result["xml"].encode("utf8"))
        self.assertEqual(len(extract_inter_article_links(tree)), 0,
                         "the xml should not contain any article links")
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
        tree = lxml.etree.fromstring(result["xml"])
        self.assertEqual(len(extract_inter_article_links(tree)), 0,
                         "there should be no article links")
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

        self.assertEqual(
            refs_by_term,
            {
                'foo': reverse("lexicography_entry_details", args=(2,)),
                'abcd': reverse("lexicography_entry_details", args=(1,))
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

        senses = tree.xpath(
            "/btw:entry/btw:sense-discrimination/btw:sense",
            namespaces=xml.default_namespace_mapping)
        self.assertEqual(len(senses), 4)

        expected_values = [
            [
                "01.02.11n",
                "01.04.04n",
                "01.04.08n",
                "01.05.05.09.01n",
                "01.06.07.03n",
                "02.02.18n",
                "02.02.19n",
                "03.05.01n",
            ],
            [
                "02.01.13n",
                "02.01.13.02n",
                "02.01.13.02.02n",
                "02.01.13.08.11n",
                "02.01.13.08.11.01.01n",
                "02.01.14n",
                "02.01.17n",
                "02.02.12n",
                "02.02.13n",
                "02.02.14n",
                "02.02.22n",
                "03.07n",
            ],
            [
                "01.05.05.12.01n"
            ],
            [
                "02.01.17n",
                "02.02.12n",
                "02.02.13n",
                "03.07.00.23n",
                "03.07.03n"
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
            "01.04.04n",
            "01.04.08n",
            "01.05.05n",
            "01.06.07n",
            "02.01.13n",
            "02.01.14n",
            "02.01.17n",
            "02.02.12n",
            "02.02.13n",
            "02.02.14n",
            "02.02.18n",
            "02.02.19n",
            "02.02.22n",
            "03.05.01n",
            "03.07n",
            "03.07.00n",
            "03.07.03n"
        ],
            "the list of semantic fields should be correct")
        self.assertIsNone(sfss[0].getnext())

    def assertLogRegexp(self, handler, stream, regexp):
        handler.flush()
        self.assertRegexpMatches(stream.getvalue(), regexp)

    def test_prepare_changerecord_for_display_already_set(self):
        """
        Tests that if the key is already set, we do not recalculate
        it.
        """
        cr = ChangeRecord.objects.get(pk=1)
        key = cr.article_display_key(cr.published)
        tasks.prepare_changerecord_for_display.delay(1).get()
        with WithStringIO(tasks.logger) as (stream, handler):
            tasks.prepare_changerecord_for_display.delay(1).get()
            self.assertLogRegexp(
                handler,
                stream,
                "^{0} is set; ending task.$".format(key))

    def test_prepare_changerecord_for_display_vanish(self):
        """
        Tests that if a task is already in progress, new tasks stop
        running early.
        """
        cr = ChangeRecord.objects.get(pk=1)
        key = cr.article_display_key(cr.published)
        tasks.prepare_changerecord_for_display.delay(
            1,
            test={"vanish": True}).get()
        with WithStringIO(tasks.logger) as (stream, handler):
            tasks.prepare_changerecord_for_display.delay(1).get()
            self.assertLogRegexp(
                handler,
                stream,
                "^{0} is held by (?:.*?); ending task.$".format(key))

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


class TruncateToTestCase(TestCase):

    def test_no_truncation_needed_correct_length(self):
        """
        If the number of levels in the semantic field code is already at
        the desired level, no truncation is performed."
        """
        self.assertEqual(tasks.truncate_to("01.01.01v", 3), "01.01.01v")

    def test_no_truncation_needed_too_low(self):
        """
        If the number of levels in the semantic field code is lower than
        the desired level, no truncation is performed."
        """
        self.assertEqual(tasks.truncate_to("01.01v", 3), "01.01v")
        self.assertEqual(tasks.truncate_to("01.01|02.03v", 3), "01.01|02.03v")

    def test_truncation_due_to_subcat(self):
        """
        If the number of levels in the semantic field code is too deep due
        to a subcat, a truncation is performed."
        """
        self.assertEqual(tasks.truncate_to("01.01.01|01.01v", 3), "01.01.01n")

    def test_truncation_due_to_too_deep(self):
        """
        If the number of levels in the semantic field code is too deep, a
        truncation is performed."
        """
        self.assertEqual(tasks.truncate_to("01.01.01.01v", 3), "01.01.01n")


class CombineSemanticFieldTestCase(TestCase):

    def test_without_maximum_depth(self):
        self.assertEqual(list(tasks.combine_semantic_fields([
            "02.03v",
            "01.01.01n",
            "01.01.01.02v",
            "01.01.01.02v",
            "01.01.01.02n",
            "01.01|01.02v",
            "01.01|01.02v",
            "01.01.01.01.01.01.99v",
            "01.01.01.01.01.01.100v",
            "01.01n",
            "01.01n",
        ])), [
            "01.01n",
            "01.01|01.02v",
            "01.01.01n",
            "01.01.01.01.01.01.99v",
            "01.01.01.01.01.01.100v",
            "01.01.01.02n",
            "01.01.01.02v",
            "02.03v"
        ])

    def test_with_maximum_depth(self):
        self.assertEqual(list(tasks.combine_semantic_fields([
            "02.03v",
            "01.01.01n",
            "01.01.01.02v",
            "01.01.01.02v",
            "01.01.01.02n",
            "01.01|01.02v",
            "01.01|01.02v",
            "01.01.01.01.01.01.99v",
            "01.01.01.01.01.01.100v",
            "01.01n",
            "01.01n",
        ], 3)), [
            "01.01n",
            "01.01|01.02v",
            "01.01.01n",
            "02.03v"
        ])

class CombineSemanticFieldsIntoTestCase(TestCase):

    def test_no_depth(self):
        """
        Combines semantic fields correctly if no depth is specified.
        """
        data = """\
<?xml version="1.0" encoding="UTF-8"?>
<btw:semantic-fields xmlns:btw="{0}">
<btw:sf>01.01.02n</btw:sf>
<btw:sf>01.01.01n</btw:sf>
<btw:sf>01.01.01.04n</btw:sf>
<btw:sf>01.01n</btw:sf>
<btw:sf>01.01n</btw:sf>
</btw:semantic-fields>
""".format(xml.default_namespace_mapping["btw"])
        tree = lxml.etree.fromstring(data.encode("utf8"))
        into = lxml.etree.Element(
            "{{{0}}}foo".format(xml.default_namespace_mapping["btw"]),
            nsmap=xml.default_namespace_mapping)
        tasks.combine_semantic_fields_into(
            tree.xpath("//btw:sf", namespaces=xml.default_namespace_mapping),
            into)
        self.assertEqual(lxml.etree.tostring(into), """\
<btw:foo xmlns:tei="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage">\
<btw:sf>01.01n</btw:sf>\
<btw:sf>01.01.01n</btw:sf>\
<btw:sf>01.01.01.04n</btw:sf>\
<btw:sf>01.01.02n</btw:sf>\
</btw:foo>\
""")

    def test_depth(self):
        """
        Combines semantic fields correctly if a depth is specified.
        """
        data = """\
<?xml version="1.0" encoding="UTF-8"?>
<btw:semantic-fields xmlns:btw="{0}">
<btw:sf>01.01.02n</btw:sf>
<btw:sf>01.01.01n</btw:sf>
<btw:sf>01.01.01.04n</btw:sf>
<btw:sf>01.01n</btw:sf>
<btw:sf>01.01n</btw:sf>
</btw:semantic-fields>
""".format(xml.default_namespace_mapping["btw"])
        tree = lxml.etree.fromstring(data.encode("utf8"))
        into = lxml.etree.Element(
            "{{{0}}}foo".format(xml.default_namespace_mapping["btw"]),
            nsmap=xml.default_namespace_mapping)
        tasks.combine_semantic_fields_into(
            tree.xpath("//btw:sf", namespaces=xml.default_namespace_mapping),
            into, 3)
        self.assertEqual(lxml.etree.tostring(into), """\
<btw:foo xmlns:tei="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage">\
<btw:sf>01.01n</btw:sf>\
<btw:sf>01.01.01n</btw:sf>\
<btw:sf>01.01.02n</btw:sf>\
</btw:foo>\
""")

class BaseSemanticFieldTestCase(TestCase):
    sf_re = re.compile(ur"(<btw:sf>)0(\d)\.")
    id_re = re.compile(ur'(xml:id=")')

    sense_with_contrastive_section = u"""\
<btw:sense>
  <btw:english-renditions>
    <btw:english-rendition>
      <btw:english-term>clarity</btw:english-term>
      <btw:semantic-fields>
        <btw:sf>01.04.08.01|02.07n</btw:sf>
        <btw:sf>01.04.08.09n</btw:sf>
        <btw:sf>01.07.04.01.02|07n</btw:sf>
        <btw:sf>02.01.08.01.02|03n</btw:sf>
        <btw:sf>02.01.10.01n</btw:sf>
        <btw:sf>02.01.10.02.03|04n</btw:sf>
        <btw:sf>17.05.03|07n</btw:sf>
        <btw:sf>03.11.03.03.05.01n</btw:sf>
        <!-- Unique to the English rendition to test that fields in
             English renditions are not included in the combination. -->
        <btw:sf>88.88.88n</btw:sf>
      </btw:semantic-fields>
    </btw:english-rendition>
    <btw:english-rendition>
      <btw:english-term>serenity</btw:english-term>
      <btw:semantic-fields>
        <btw:sf>01.02.11.02.01|08.01n</btw:sf>
        <btw:sf>01.05.05.09.01|00n</btw:sf>
        <btw:sf>02.02.18n</btw:sf>
        <btw:sf>02.02.19.06n</btw:sf>
        <btw:sf>03.01.06.01.03.03|09.06n</btw:sf>
      </btw:semantic-fields>
    </btw:english-rendition>
  </btw:english-renditions>
  <btw:subsense xml:id="S.a-1">
    <btw:explanation>[...]</btw:explanation>
    <btw:citations>
      <btw:example>
        <btw:semantic-fields>
          <btw:sf>01.04.08n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/1">XXX</ref>
        <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example>
      <btw:example-explained>
        <btw:explanation>[...]</btw:explanation>
        <btw:semantic-fields>
          <btw:sf>01.04.04n</btw:sf>
          <btw:sf>01.02.11n</btw:sf>
          <btw:sf>01.06.07.03n</btw:sf>
          <btw:sf>02.02.18n</btw:sf>
          <btw:sf>02.02.19n</btw:sf>
          <btw:sf>01.05.05.09.01n</btw:sf>
          <btw:sf>03.05.01n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/1">XXX</ref>
        <foreign xml:lang="pi-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example-explained>
      <btw:example>
        <btw:semantic-fields>
          <btw:sf>01.04.04n</btw:sf>
          <btw:sf>01.02.11n</btw:sf>
          <btw:sf>01.06.07.03n</btw:sf>
          <btw:sf>02.02.18n</btw:sf>
          <btw:sf>02.02.19n</btw:sf>
          <btw:sf>01.05.05.09.01n</btw:sf>
          <btw:sf>03.05.01n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/1">XXX</ref>
        <foreign xml:lang="pi-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example>
    </btw:citations>
    <btw:other-citations>
      <btw:semantic-fields>
        <btw:sf>03.05.01n</btw:sf>
      </btw:semantic-fields>
      <btw:cit><ref target="/bibliography/1">XXX</ref>
      <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
    </btw:other-citations>
  </btw:subsense>
  <btw:subsense xml:id="S.a-2">
    <btw:explanation>[...]</btw:explanation>
    <btw:citations>
      <btw:example>
        <btw:semantic-fields>
          <btw:sf>01.04.04n</btw:sf>
          <btw:sf>01.02.11n</btw:sf>
          <btw:sf>01.06.07.03n</btw:sf>
          <btw:sf>02.02.18n</btw:sf>
          <btw:sf>02.02.19n</btw:sf>
          <btw:sf>01.05.05.09.01n</btw:sf>
          <btw:sf>03.05.01n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/primary-sources/1">XXX</ref>
        <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example>
      <btw:example>
        <btw:semantic-fields>
          <btw:sf>01.04.04n</btw:sf>
          <btw:sf>01.02.11n</btw:sf>
          <btw:sf>01.06.07.03n</btw:sf>
          <btw:sf>02.02.18n</btw:sf>
          <btw:sf>02.02.19n</btw:sf>
          <btw:sf>01.05.05.09.01n</btw:sf>
          <btw:sf>03.05.01n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/1">XXX</ref>
        <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example>
    </btw:citations>
    <btw:other-citations>
      <btw:semantic-fields>
        <btw:sf>03.05.01n</btw:sf>
      </btw:semantic-fields>
      <btw:cit><ref target="/bibliography/1">XXX</ref>\
      <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
    </btw:other-citations>
  </btw:subsense>
  <btw:contrastive-section>
    <btw:antonyms>
      <btw:antonym>
        <btw:term><foreign xml:lang="sa-Latn">aprasāda</foreign></btw:term>
        <btw:citations>
          <btw:example>
            <btw:cit><ref target="/bibliography/1">XXX</ref>
            <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
            <btw:tr>[...]</btw:tr>
          </btw:example>
        </btw:citations>
        <btw:other-citations>
          <btw:semantic-fields>
            <btw:sf>03.05.01n</btw:sf>
          </btw:semantic-fields>
          <btw:cit><ref target="/bibliography/1">XXX</ref>
          <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        </btw:other-citations>
      </btw:antonym>
      <btw:antonym>
        <btw:term><foreign xml:lang="sa-Latn">kāluṣya</foreign></btw:term>
        <btw:citations>
          <btw:example>
            <btw:cit><ref target="/bibliography/1">XXX</ref>
            <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
            <btw:tr>[...]</btw:tr>
          </btw:example>
        </btw:citations>
        <btw:other-citations>
          <btw:semantic-fields>
            <btw:sf>03.05.01n</btw:sf>
          </btw:semantic-fields>
          <btw:cit><ref target="/bibliography/1">[...]</ref>
          <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        </btw:other-citations>
      </btw:antonym>
    </btw:antonyms>
    <btw:cognates>
      <btw:cognate>
        <btw:term><foreign xml:lang="sa-Latn">pra√sad</foreign></btw:term>
        <btw:citations>
          <btw:example>
            <btw:semantic-fields>
              <btw:sf>01.02.11n</btw:sf>
              <btw:sf>01.04.04n</btw:sf>
              <btw:sf>01.04.08n</btw:sf>
              <btw:sf>01.05.05n</btw:sf>
              <btw:sf>01.05.05.09.01n</btw:sf>
              <btw:sf>02.01.10n</btw:sf>
              <btw:sf>03.11.03n</btw:sf>
              <!-- Unique to the contrastive section to ensure
                   semantic fields in contrastive sections are not included.
                   -->
              <btw:sf>99.99.99n</btw:sf>
            </btw:semantic-fields>
            <btw:cit><ref target="/bibliography/1">[...]</ref>
            <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
            <btw:tr>[...]</btw:tr>
          </btw:example>
        </btw:citations>
        <btw:other-citations>
          <btw:semantic-fields>
            <btw:sf>03.05.01n</btw:sf>
            <!-- Unique to the contrastive section to ensure
                 semantic fields in contrastive sections are not included. -->
            <btw:sf>99.99.99a</btw:sf>
          </btw:semantic-fields>
          <btw:cit><ref target="/bibliography/1">[...]</ref>
          <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        </btw:other-citations>
      </btw:cognate>
      <btw:cognate>
        <btw:term><foreign xml:lang="sa-Latn">saṃprasāda</foreign></btw:term>
        <btw:citations>
          <btw:example xml:id="E.1">
            <btw:semantic-fields>
              <btw:sf>01.02.11n</btw:sf>
            </btw:semantic-fields>
            <btw:cit><ref target="/bibliography/1">[...]</ref>
            <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
            <btw:tr>[...]</btw:tr>
          </btw:example>
          <btw:example>
            <btw:semantic-fields>
              <btw:sf>01.04.04n</btw:sf>
              <btw:sf>01.04.08n</btw:sf>
              <btw:sf>01.05.05.09.01n</btw:sf>
              <btw:sf>01.06.07.03n</btw:sf>
              <btw:sf>02.02.11n</btw:sf>
              <btw:sf>02.02.18n</btw:sf>
              <btw:sf>02.02.19n</btw:sf>
              <btw:sf>03.05.01n</btw:sf>
            </btw:semantic-fields>
            <btw:cit><ref target="/bibliography/1">[...]</ref>
            <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
            <btw:tr>[...]</btw:tr>
          </btw:example>
          <btw:example>
            <btw:semantic-fields>
              <btw:sf>01.04.04n</btw:sf>
              <btw:sf>01.04.08n</btw:sf>
              <btw:sf>01.05.05.09.01n</btw:sf>
              <btw:sf>01.06.07.03n</btw:sf>
              <btw:sf>02.02.11n</btw:sf>
              <btw:sf>02.02.18n</btw:sf>
              <btw:sf>02.02.19n</btw:sf>
              <btw:sf>03.05.01n</btw:sf>
            </btw:semantic-fields>
            <btw:cit><ref target="/bibliography/1">[...]</ref>
            <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
            <btw:tr>[...]</btw:tr>
          </btw:example>
        </btw:citations>
        <btw:other-citations>
          <btw:semantic-fields>
            <btw:sf>03.05.01n</btw:sf>
          </btw:semantic-fields>
          <btw:cit><ref target="/bibliography/1">[...]</ref>
          <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        </btw:other-citations>
      </btw:cognate>
    </btw:cognates>
    <btw:conceptual-proximates>
      <btw:conceptual-proximate>
        <btw:term><foreign xml:lang="sa-Latn">saṃprasāda</foreign></btw:term>
        <btw:citations>
          <ptr target="#E.1"/>
        </btw:citations>
        <btw:other-citations>
          <btw:semantic-fields>
            <btw:sf>03.05.01n</btw:sf>
          </btw:semantic-fields>
          <btw:cit><ref target="/bibliography/1">[...]</ref>
          <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        </btw:other-citations>
      </btw:conceptual-proximate>
      <btw:conceptual-proximate>
        <btw:term><foreign xml:lang="sa-Latn">foo</foreign></btw:term>
        <btw:citations>
          <ptr target="#E.1"/>
        </btw:citations>
      </btw:conceptual-proximate>
    </btw:conceptual-proximates>
  </btw:contrastive-section>
</btw:sense>
"""

    no_fields_to_combine = u"""\
<btw:sense>
  <btw:english-renditions>
    <btw:english-rendition>
      <btw:english-term>clarity</btw:english-term>
      <btw:semantic-fields>
        <btw:sf>01.04.08.01|02.07n</btw:sf>
        <btw:sf>01.04.08.09n</btw:sf>
        <btw:sf>01.07.04.01.02|07n</btw:sf>
        <btw:sf>02.01.08.01.02|03n</btw:sf>
        <btw:sf>02.01.10.01n</btw:sf>
        <btw:sf>02.01.10.02.03|04n</btw:sf>
        <btw:sf>17.05.03|07n</btw:sf>
        <btw:sf>03.11.03.03.05.01n</btw:sf>
        <!-- Unique to the English rendition to test that fields in
             English renditions are not included in the combination. -->
        <btw:sf>88.88.88n</btw:sf>
      </btw:semantic-fields>
    </btw:english-rendition>
    <btw:english-rendition>
      <btw:english-term>serenity</btw:english-term>
      <btw:semantic-fields>
        <btw:sf>01.02.11.02.01|08.01n</btw:sf>
        <btw:sf>01.05.05.09.01|00n</btw:sf>
        <btw:sf>02.02.18n</btw:sf>
        <btw:sf>02.02.19.06n</btw:sf>
        <btw:sf>03.01.06.01.03.03|09.06n</btw:sf>
      </btw:semantic-fields>
    </btw:english-rendition>
  </btw:english-renditions>
  <btw:subsense xml:id="S.a-1">
    <btw:explanation>[...]</btw:explanation>
    <btw:citations>
    </btw:citations>
    <btw:other-citations>
    </btw:other-citations>
  </btw:subsense>
  <btw:subsense xml:id="S.a-2">
    <btw:explanation>[...]</btw:explanation>
    <btw:citations>
    </btw:citations>
    <btw:other-citations>
    </btw:other-citations>
  </btw:subsense>
</btw:sense>
"""

    def double_senses(self, data):
        # What we are doing here is creating two senses. For the
        # second sense, all the semantic fields are modified to start
        # with "1" instead of "0".
        return u"""\
<?xml version="1.0" encoding="UTF-8"?>\
<btw:entry xmlns:btw="{0}">
<btw:overview>
  <btw:definition/>
</btw:overview>
<btw:sense-discrimination>
{1}{2}
</btw:sense-discrimination>
</btw:entry>""".format(xml.default_namespace_mapping["btw"],
                       data,
                       # Modify the ids so that they do not clash.
                       self.id_re.sub(ur"\1x",
                                      # Modify the semantic fields so that
                                      # they start with "1" rather than "0".
                                      self.sf_re.sub(ur"\g<1>1\2.", data)))


class CombineSenseSemanticFieldsTestCase(BaseSemanticFieldTestCase):

    def test_senses_with_contrastive_section(self):
        """
        When operating on senses with a contrastive section, it combines
        the semantic fields properly and puts the combined fields in
        front of the contrastive section. The fields found uniquely in
        the contrastive section are not included in the combination of
        fields.
        """

        # This allows us to make sure the code does not trip when
        # there is more than one semantic field.
        data = self.double_senses(self.sense_with_contrastive_section)

        expected_values = [
            [
                "01.02.11n",
                "01.04.04n",
                "01.04.08n",
                "01.05.05.09.01n",
                "01.06.07.03n",
                "02.02.18n",
                "02.02.19n",
                "03.05.01n",
            ]
        ]

        # What we expect for the second sense is built from the 1st
        # one.
        expected_values.append(["1" + sf[1:] for sf in expected_values[0]])

        tree = xml.XMLTree(data.encode("utf8"))
        self.assertIsNone(tree.parsing_error)
        modified = tasks.combine_sense_semantic_fields(tree)
        self.assertTrue(modified, "the tree should have been modified")
        senses = tree.tree.xpath(
            "/btw:entry/btw:sense-discrimination/btw:sense",
            namespaces=xml.default_namespace_mapping)
        self.assertEqual(len(senses), 2, "there should be two senses")
        for ix, (sense, expected) in enumerate(zip(senses, expected_values)):
            sense_label = "sense " + str(ix + 1)
            sfss = sense.xpath("./btw:semantic-fields",
                               namespaces=xml.default_namespace_mapping)
            self.assertEqual(len(sfss), 1,
                             "there should be only one btw:semantic-fields "
                             "element in " + sense_label)
            sfs = [sf.text for sf in sfss[0]]
            self.assertEqual(sfs, expected,
                             "the list of semantic fields should be correct "
                             "in " + sense_label)
            self.assertEqual(
                sfss[0].getnext().tag,
                "{{{0}}}contrastive-section"
                .format(xml.default_namespace_mapping["btw"]),
                "the combined fields should be just before the contrastive "
                "section in " + sense_label)

    def test_senses_without_contrastive_section(self):
        """
        When operating on senses without a contrastive section, it combines
        the semantic fields properly and puts the combined fields at the end
        of the sense.
        """
        data = u"""\
<btw:sense>
  <btw:english-renditions>
    <btw:english-rendition>
      <btw:english-term>clarity</btw:english-term>
      <btw:semantic-fields>
        <btw:sf>01.04.08.01|02.07n</btw:sf>
        <btw:sf>01.04.08.09n</btw:sf>
        <btw:sf>01.07.04.01.02|07n</btw:sf>
        <btw:sf>02.01.08.01.02|03n</btw:sf>
        <btw:sf>02.01.10.01n</btw:sf>
        <btw:sf>02.01.10.02.03|04n</btw:sf>
        <btw:sf>17.05.03|07n</btw:sf>
        <btw:sf>03.11.03.03.05.01n</btw:sf>
        <!-- Unique to the English rendition to test that fields in
             English renditions are not included in the combination. -->
        <btw:sf>88.88.88n</btw:sf>
      </btw:semantic-fields>
    </btw:english-rendition>
    <btw:english-rendition>
      <btw:english-term>serenity</btw:english-term>
      <btw:semantic-fields>
        <btw:sf>01.02.11.02.01|08.01n</btw:sf>
        <btw:sf>01.05.05.09.01|00n</btw:sf>
        <btw:sf>02.02.18n</btw:sf>
        <btw:sf>02.02.19.06n</btw:sf>
        <btw:sf>03.01.06.01.03.03|09.06n</btw:sf>
      </btw:semantic-fields>
    </btw:english-rendition>
  </btw:english-renditions>
  <btw:subsense xml:id="S.a-1">
    <btw:explanation>[...]</btw:explanation>
    <btw:citations>
      <btw:example>
        <btw:semantic-fields>
          <btw:sf>01.04.08n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/1">XXX</ref>
        <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example>
      <btw:example-explained>
        <btw:explanation>[...]</btw:explanation>
        <btw:semantic-fields>
          <btw:sf>01.04.04n</btw:sf>
          <btw:sf>01.02.11n</btw:sf>
          <btw:sf>01.06.07.03n</btw:sf>
          <btw:sf>02.02.18n</btw:sf>
          <btw:sf>02.02.19n</btw:sf>
          <btw:sf>01.05.05.09.01n</btw:sf>
          <btw:sf>03.05.01n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/1">XXX</ref>
        <foreign xml:lang="pi-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example-explained>
      <btw:example>
        <btw:semantic-fields>
          <btw:sf>01.04.04n</btw:sf>
          <btw:sf>01.02.11n</btw:sf>
          <btw:sf>01.06.07.03n</btw:sf>
          <btw:sf>02.02.18n</btw:sf>
          <btw:sf>02.02.19n</btw:sf>
          <btw:sf>01.05.05.09.01n</btw:sf>
          <btw:sf>03.05.01n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/1">XXX</ref>
        <foreign xml:lang="pi-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example>
    </btw:citations>
    <btw:other-citations>
      <btw:semantic-fields>
        <btw:sf>03.05.01n</btw:sf>
      </btw:semantic-fields>
      <btw:cit><ref target="/bibliography/1">XXX</ref>
      <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
    </btw:other-citations>
  </btw:subsense>
  <btw:subsense xml:id="S.a-2">
    <btw:explanation>[...]</btw:explanation>
    <btw:citations>
      <btw:example>
        <btw:semantic-fields>
          <btw:sf>01.04.04n</btw:sf>
          <btw:sf>01.02.11n</btw:sf>
          <btw:sf>01.06.07.03n</btw:sf>
          <btw:sf>02.02.18n</btw:sf>
          <btw:sf>02.02.19n</btw:sf>
          <btw:sf>01.05.05.09.01n</btw:sf>
          <btw:sf>03.05.01n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/primary-sources/1">XXX</ref>
        <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example>
      <btw:example>
        <btw:semantic-fields>
          <btw:sf>01.04.04n</btw:sf>
          <btw:sf>01.02.11n</btw:sf>
          <btw:sf>01.06.07.03n</btw:sf>
          <btw:sf>02.02.18n</btw:sf>
          <btw:sf>02.02.19n</btw:sf>
          <btw:sf>01.05.05.09.01n</btw:sf>
          <btw:sf>03.05.01n</btw:sf>
        </btw:semantic-fields>
        <btw:cit><ref target="/bibliography/1">XXX</ref>
        <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
        <btw:tr>[...]</btw:tr>
      </btw:example>
    </btw:citations>
    <btw:other-citations>
      <btw:semantic-fields>
        <btw:sf>03.05.01n</btw:sf>
      </btw:semantic-fields>
      <btw:cit><ref target="/bibliography/1">XXX</ref>\
      <foreign xml:lang="sa-Latn">[...]</foreign></btw:cit>
    </btw:other-citations>
  </btw:subsense>
</btw:sense>
"""

        data = self.double_senses(data)

        expected_values = [
            [
                "01.02.11n",
                "01.04.04n",
                "01.04.08n",
                "01.05.05.09.01n",
                "01.06.07.03n",
                "02.02.18n",
                "02.02.19n",
                "03.05.01n",
            ]
        ]

        # What we expect for the second sense is built from the 1st
        # one.
        expected_values.append(["1" + sf[1:] for sf in expected_values[0]])

        tree = xml.XMLTree(data.encode("utf8"))
        self.assertIsNone(tree.parsing_error)
        modified = tasks.combine_sense_semantic_fields(tree)
        self.assertTrue(modified, "the tree should have been modified")
        senses = tree.tree.xpath(
            "/btw:entry/btw:sense-discrimination/btw:sense",
            namespaces=xml.default_namespace_mapping)
        self.assertEqual(len(senses), 2, "there should be two senses")
        for ix, (sense, expected) in enumerate(zip(senses, expected_values)):
            sense_label = "sense " + str(ix + 1)
            sfss = sense.xpath("./btw:semantic-fields",
                               namespaces=xml.default_namespace_mapping)
            self.assertEqual(len(sfss), 1,
                             "there should be only one btw:semantic-fields "
                             "element in " + sense_label)
            sfs = [sf.text for sf in sfss[0]]
            self.assertEqual(sfs, expected,
                             "the list of semantic fields should be "
                             "correct in " + sense_label)
            self.assertIsNone(sfss[0].getnext(),
                              "the combined semantic fields "
                              "should be at the end in " + sense_label)

    def test_no_modification(self):
        """
        When operating on senses that do not need modification, the senses
        are not modified.
        """

        data = self.double_senses(self.no_fields_to_combine)

        tree = xml.XMLTree(data.encode("utf8"))
        before = lxml.etree.tostring(tree.tree)
        self.assertIsNone(tree.parsing_error)
        modified = tasks.combine_sense_semantic_fields(tree)
        self.assertFalse(modified, "the tree should not be reported modified")
        self.assertEqual(before, lxml.etree.tostring(tree.tree),
                         "the data should be the same")

class CombineAllSemanticFieldsTestCase(BaseSemanticFieldTestCase):

    def test_modified(self):

        # This allows us to make sure the code does not trip when
        # there is more than one semantic field.
        data = self.double_senses(self.sense_with_contrastive_section)

        expected = [
            "01.02.11n",
            "01.04.04n",
            "01.04.08n",
            "01.05.05n",
            "01.06.07n",
            "02.02.18n",
            "02.02.19n",
            "03.05.01n",
            "11.02.11n",
            "11.04.04n",
            "11.04.08n",
            "11.05.05n",
            "11.06.07n",
            "12.02.18n",
            "12.02.19n",
            "13.05.01n",
        ]

        tree = xml.XMLTree(data.encode("utf8"))
        self.assertIsNone(tree.parsing_error)
        tasks.combine_sense_semantic_fields(tree)
        modified = tasks.combine_all_semantic_fields(tree)
        self.assertTrue(modified, "the tree should have been modified")
        sfss = tree.tree.xpath(
            "/btw:entry/btw:overview/btw:semantic-fields",
            namespaces=xml.default_namespace_mapping)
        self.assertEqual(len(sfss), 1,
                         "there should be only one btw:semantic-fields "
                         "element")
        sfs = [sf.text for sf in sfss[0]]
        self.assertEqual(sfs, expected,
                         "the list of semantic fields should be correct")
        self.assertIsNone(sfss[0].getnext())

    def test_no_modification(self):
        """
        When operating on senses that do not need modification, the senses
        are not modified.
        """

        data = self.double_senses(self.no_fields_to_combine)

        tree = xml.XMLTree(data.encode("utf8"))
        before = lxml.etree.tostring(tree.tree)
        self.assertIsNone(tree.parsing_error)
        tasks.combine_sense_semantic_fields(tree)
        modified = tasks.combine_all_semantic_fields(tree)
        self.assertFalse(modified, "the tree should not be reported modified")
        self.assertEqual(before, lxml.etree.tostring(tree.tree),
                         "the data should be the same")
