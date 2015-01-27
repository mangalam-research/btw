# -*- encoding: utf-8 -*-
import unittest
import os
import lib.util as util
from .. import xml

as_editable_table = {}


def as_editable(filepath):
    editable = as_editable_table.get(filepath, None)
    if editable is not None:
        return editable

    data = open(filepath).read().decode('utf-8')

    # We ask xsltproc not to put out a declaration and add our own.
    tidy = '<?xml version="1.0" encoding="UTF-8"?>' + \
        util.run_xsltproc(os.path.join(xml.xsl_dirname, "strip.xsl"),
                          data).encode("utf-8")

    as_editable_table[filepath] = tidy
    return tidy


class XMLTreeTestCase(unittest.TestCase):

    def test_is_data_unclean_passes(self):
        editable = as_editable(os.path.join(xml.schemas_dirname,
                                            "prasada.xml"))
        self.assertFalse(xml.XMLTree(editable).is_data_unclean())

    def test_is_data_unclean_fails_on_unparseable(self):
        data = '<div'
        self.assertTrue(xml.XMLTree(data).is_data_unclean())

    def test_extract_lemma_passes(self):
        editable = as_editable(os.path.join(xml.schemas_dirname,
                                            "prasada.xml"))
        self.assertEqual(xml.XMLTree(editable).extract_lemma(),
                         u"prasāda")

    def test_extract_lemma_returns_none_when_no_lemma(self):
        data = '<div xmlns="http://www.w3.org/1999/xhtml"></div>'
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_lemma())

    def test_extract_lemma_returns_none_when_empty_lemma(self):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="LL">
  <btw:lemma></btw:lemma>
</btw:entry>
        """
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_lemma())

    def test_extract_lemma_returns_none_when_whitespace_lemma(self):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="LL">
  <btw:lemma>   </btw:lemma>
</btw:entry>
        """
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_lemma())

    def test_extract_authority_passes(self):
        editable = as_editable(os.path.join(xml.schemas_dirname,
                                            "prasada.xml"))
        self.assertEqual(xml.XMLTree(editable).extract_authority(),
                         "LL")

    def test_extract_lemma_fails_when_no_authority(self):
        data = '<div xmlns="http://www.w3.org/1999/xhtml"></div>'
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertRaisesRegexp(ValueError,
                                "can't find the authority in the data passed",
                                xmltree.extract_authority)

    def test_get_bibliographical_targets(self):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="LL">
  <btw:lemma></btw:lemma>
  <p>
  <ref target="/bibliography/1">foo</ref>
  <ref target="/bibliography/2"/>
  <ref target="/bibliography/2"/>
  </p>
</btw:entry>
        """
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertEqual(xmltree.get_bibilographical_targets(),
                         set(["/bibliography/1", "/bibliography/2"]))
