# -*- encoding: utf-8 -*-
import os
import re
import unittest

import lxml.etree
from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

from .. import article, xml
from ..models import ChangeRecord, Entry
from .util import launch_fetch_task, create_valid_article, \
    extract_inter_article_links
from lib.util import DisableMigrationsMixin
from lib.testutil import wipd

dirname = os.path.dirname(__file__)
hte_fixture = os.path.join(
    dirname, "..", "..", "semantic_fields", "tests", "fixtures", "hte.json")

class TruncateToTestCase(unittest.TestCase):

    def test_no_truncation_needed_correct_length(self):
        """
        If the number of levels in the semantic field code is already at
        the desired level, no truncation is performed."
        """
        self.assertEqual(article.truncate_to("01.01.01v", 3), "01.01.01v")

    def test_no_truncation_needed_too_low(self):
        """
        If the number of levels in the semantic field code is lower than
        the desired level, no truncation is performed."
        """
        self.assertEqual(article.truncate_to("01.01v", 3), "01.01v")
        self.assertEqual(article.truncate_to(
            "01.01|02.03v", 3), "01.01|02.03v")

    def test_truncation_due_to_subcat(self):
        """
        If the number of levels in the semantic field code is too deep due
        to a subcat, a truncation is performed."
        """
        self.assertEqual(article.truncate_to(
            "01.01.01|01.01v", 3), "01.01.01n")

    def test_truncation_due_to_too_deep(self):
        """
        If the number of levels in the semantic field code is too deep, a
        truncation is performed."
        """
        self.assertEqual(article.truncate_to("01.01.01.01v", 3), "01.01.01n")


class CombineSemanticFieldTestCase(unittest.TestCase):

    def test_without_maximum_depth(self):
        self.assertEqual(list(article.combine_semantic_fields([
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
        self.assertEqual(list(article.combine_semantic_fields([
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

class CombineSemanticFieldsIntoTestCase(unittest.TestCase):

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
        article.combine_semantic_fields_into(
            tree.xpath("//btw:sf", namespaces=xml.default_namespace_mapping),
            into)
        self.assertEqual(lxml.etree.tostring(into), b"""\
<btw:foo xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
xmlns:tei="http://www.tei-c.org/ns/1.0">\
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
        article.combine_semantic_fields_into(
            tree.xpath("//btw:sf", namespaces=xml.default_namespace_mapping),
            into, 3)
        self.assertEqual(lxml.etree.tostring(into), b"""\
<btw:foo xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
xmlns:tei="http://www.tei-c.org/ns/1.0">\
<btw:sf>01.01n</btw:sf>\
<btw:sf>01.01.01n</btw:sf>\
<btw:sf>01.01.02n</btw:sf>\
</btw:foo>\
""")

class BaseSemanticFieldTestCase(TestCase):
    sf_re = re.compile(r"(<btw:sf>)0(\d)\.")
    id_re = re.compile(r'(xml:id=")')

    sense_with_contrastive_section = """\
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

    no_fields_to_combine = """\
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
        return """\
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
                       self.id_re.sub(r"\1x",
                                      # Modify the semantic fields so that
                                      # they start with "1" rather than "0".
                                      self.sf_re.sub(r"\g<1>1\2.", data)))


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
        modified = article.combine_sense_semantic_fields(tree)
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
        data = """\
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
        modified = article.combine_sense_semantic_fields(tree)
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
        modified = article.combine_sense_semantic_fields(tree)
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
        article.combine_sense_semantic_fields(tree)
        modified = article.combine_all_semantic_fields(tree)
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
        article.combine_sense_semantic_fields(tree)
        modified = article.combine_all_semantic_fields(tree)
        self.assertFalse(modified, "the tree should not be reported modified")
        self.assertEqual(before, lxml.etree.tostring(tree.tree),
                         "the data should be the same")


class NameSemanticFieldsTestCase(TestCase):

    fixtures = [hte_fixture]

    def test_modified(self):
        data = """\
<?xml version="1.0" encoding="UTF-8"?>
<btw:semantic-fields xmlns:btw="{0}">
 <btw:sf>03.07n</btw:sf>
 <btw:sf>02.02.13n</btw:sf>
 <btw:sf>01.01n</btw:sf>
</btw:semantic-fields>
""".format(xml.default_namespace_mapping["btw"])

        tree = xml.XMLTree(data.encode("utf8"))
        self.assertIsNone(tree.parsing_error)
        modified, _ = article.name_semantic_fields(tree)
        self.assertTrue(modified, "the tree should have been modified")

        sfs = [sf.text for sf in tree.tree.xpath(
            "/btw:semantic-fields/btw:sf",
            namespaces=xml.default_namespace_mapping)]
        self.assertEqual(sfs, [
            "Education (03.07n)",
            "Bad taste (02.02.13n)",
            "01.01n"
        ])

    def test_not_modified(self):
        data = """\
<?xml version="1.0" encoding="UTF-8"?>
<btw:semantic-fields xmlns:btw="{0}">
 <btw:sf>01.01n</btw:sf>
</btw:semantic-fields>
""".format(xml.default_namespace_mapping["btw"])

        tree = xml.XMLTree(data.encode("utf8"))
        self.assertIsNone(tree.parsing_error)
        modified, _ = article.name_semantic_fields(tree)
        self.assertFalse(modified, "the tree should not have been modified")

        sfs = [sf.text for sf in tree.tree.xpath(
            "/btw:semantic-fields/btw:sf",
            namespaces=xml.default_namespace_mapping)]
        self.assertEqual(sfs, [
            "01.01n"
        ])

    def test_subcategories(self):
        """
        Test that semantic fields that are subcategories have their
        heading displayed together with the heading of their parents.
        """
        data = """\
<?xml version="1.0" encoding="UTF-8"?>
<btw:semantic-fields xmlns:btw="{0}">
 <btw:sf>02.01.12.10.04|02.01n</btw:sf>
 <btw:sf>02.01.12.10.04|02n</btw:sf>
</btw:semantic-fields>
""".format(xml.default_namespace_mapping["btw"])

        tree = xml.XMLTree(data.encode("utf8"))
        self.assertIsNone(tree.parsing_error)
        modified, _ = article.name_semantic_fields(tree)
        self.assertTrue(modified, "the tree should have been modified")

        sfs = [sf.text for sf in tree.tree.xpath(
            "/btw:semantic-fields/btw:sf",
            namespaces=xml.default_namespace_mapping)]
        self.assertEqual(sfs, [
            "Privacy :: private matter/business :: "
            "confiding of (02.01.12.10.04|02.01n)",
            "Privacy :: private matter/business (02.01.12.10.04|02n)",
        ])


def prepare(chunk):
    data = xml.strip_xml_decl(chunk.data)[1]
    prepared = {
        "xml": data,
        "lemmas": article.get_lemmas_and_terms(xml.XMLTree(data))[0]
    }
    return prepared


@override_settings(ROOT_URLCONF='lexicography.tests.urls')
class HyperlinkPreparedDataTestCase(DisableMigrationsMixin, TestCase):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "views.json")) + [hte_fixture]

    def test_no_links(self):
        """
        Tests that the result is the same as the original data when there
        are no references to other articles in the change record.
        """
        chunk = ChangeRecord.objects.get(pk=1).c_hash
        prepared = prepare(chunk)

        data = article.hyperlink_prepared_data(prepared, True)
        tree = lxml.etree.fromstring(data.encode("utf8"))
        self.assertEqual(
            len(extract_inter_article_links(tree)), 0,
            "the published xml should not contain any article links")

        data = article.hyperlink_prepared_data(prepared, False)
        tree = lxml.etree.fromstring(data.encode("utf8"))
        self.assertEqual(
            len(extract_inter_article_links(tree)), 0,
            "the unpublished xml should not contain any article links")

    def test_candidates_no_links(self):
        """
        Tests that the result is the same as the original data when there
        are only references to non-existing articles in the change
        record.
        """
        cr = Entry.objects.get(
            lemma="antonym with citations, followed by another "
            "antonym").latest
        chunk = cr.c_hash

        prepared = prepare(chunk)

        data = article.hyperlink_prepared_data(prepared, True)
        tree = lxml.etree.fromstring(data.encode("utf8"))
        self.assertEqual(
            len(extract_inter_article_links(tree)), 0,
            "the published xml should not contain any article links")

        data = article.hyperlink_prepared_data(prepared, False)
        tree = lxml.etree.fromstring(data.encode("utf8"))
        self.assertEqual(
            len(extract_inter_article_links(tree)), 0,
            "the unpublished xml should not contain any article links")

    def test_complex_document(self):
        # Yeah, we launch it here. The other tests don't need this
        # data so...
        launch_fetch_task()
        entry = create_valid_article()

        chunk = entry.latest.c_hash
        prepared = prepare(chunk)

        data = article.hyperlink_prepared_data(prepared, False)
        tree = lxml.etree.fromstring(data.encode("utf8"))
        refs_by_term = extract_inter_article_links(tree)

        self.assertEqual(
            refs_by_term,
            {
                'foo': reverse("lexicography_entry_details", args=(2,)),
                'abcd': reverse("lexicography_entry_details", args=(1,))
            },
            "the unpublished XML should have the right links")

        data = article.hyperlink_prepared_data(prepared, True)
        tree = lxml.etree.fromstring(data.encode("utf8"))
        refs_by_term = extract_inter_article_links(tree)
        self.assertEqual(
            refs_by_term,
            {
                'abcd': reverse("lexicography_entry_details", args=(1,))
            },
            "the published xml should not contain correct article links")

@override_settings(ROOT_URLCONF='lexicography.tests.urls')
class AddSemanticFieldsToEnglishRenditionsTestCase(DisableMigrationsMixin,
                                                   TestCase):
    fixtures = [hte_fixture]

    def test_no_english_rendition(self):
        """
        Tests that the result is the same as the original data when there
        are no English renditions.
        """
        original = b"""\
<btw:entry xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
xmlns:tei="http://www.tei-c.org/ns/1.0"/>"""
        tree = xml.XMLTree(original)
        modified = article.add_semantic_fields_to_english_renditions(tree)
        self.assertFalse(modified)
        self.assertEqual(lxml.etree.tostring(tree.tree), original)

    def test_english_renditions(self):
        """
        Tests that English renditions get their semantic fields.
        """
        original = """\
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="/1" \
version="0.10">
  <btw:sense>
    <btw:english-renditions>
      <btw:english-rendition>
        <btw:english-term>clarity</btw:english-term>
      </btw:english-rendition>
      <btw:english-rendition>
        <btw:english-term>serenity</btw:english-term>
      </btw:english-rendition>
    </btw:english-renditions>
  </btw:sense>
</btw:entry>"""
        tree = xml.XMLTree(original)
        modified = article.add_semantic_fields_to_english_renditions(tree)
        self.assertTrue(modified)
        self.assertEqual(lxml.etree.tostring(tree.tree), b"""\
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="/1" \
version="0.10">
  <btw:sense>
    <btw:english-renditions>
      <btw:english-rendition>
        <btw:english-term>clarity</btw:english-term>
      <btw:semantic-fields><btw:sf>02.01.08.01.02|03n</btw:sf><btw:sf>02.01.10.01n</btw:sf></btw:semantic-fields></btw:english-rendition>
      <btw:english-rendition>
        <btw:english-term>serenity</btw:english-term>
      </btw:english-rendition>
    </btw:english-renditions>
  </btw:sense>
</btw:entry>""")
