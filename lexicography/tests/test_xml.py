# -*- encoding: utf-8 -*-
import unittest
import os
from collections import OrderedDict

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
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage">
  <btw:lemma></btw:lemma>
</btw:entry>
        """
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_lemma())

    def test_extract_lemma_returns_none_when_whitespace_lemma(self):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage">
  <btw:lemma>   </btw:lemma>
</btw:entry>
        """
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_lemma())

    def test_get_bibliographical_targets(self):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage">
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

class XMLTestCase(unittest.TestCase):

    def test_get_supported_schema_versions(self):
        versions = xml.get_supported_schema_versions()
        expected = OrderedDict([
            ("0.9", xml.VersionInfo(can_revert=False, can_validate=True)),
            ("0.10", xml.VersionInfo(can_revert=False, can_validate=True)),
            ("1.0", xml.VersionInfo(can_revert=True, can_validate=True))
        ])
        self.assertEqual(versions, expected)

    def test_can_revert_to(self):
        # Non-existent version
        self.assertFalse(xml.can_revert_to("0.0"))
        # Old version
        self.assertFalse(xml.can_revert_to("0.9"))
        # New version
        versions = xml.get_supported_schema_versions()
        self.assertTrue(xml.can_revert_to(versions.keys()[-1]))

    def test_convert_to_version_bad_versions(self):
        """
        The function convert_to_version fails if there is no schema for
        conversion.
        """
        with self.assertRaisesRegexp(ValueError,
                                     "cannot convert from 0.0 to 0.0"):
            xml.convert_to_version("", "0.0", "0.0")

    def test_convert_to_version_0_10_to_1_0(self):
        """
        The function convert_to_version converts 0.10 to 1.0.
        """
        result = xml.convert_to_version("""
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
  <p>
  <ref target="/bibliography/1">foo</ref>
  <ref target="/bibliography/2"/>
  <ref target="/bibliography/2"/>
  </p>
</btw:entry>
        """,
                                        "0.10", "1.0")
        self.assertEqual(result, u"""\
<?xml version="1.0" encoding="UTF-8"?>
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="1.0">
  <btw:lemma/>
  <p>
  <ref target="/bibliography/1">foo</ref>
  <ref target="/bibliography/2"/>
  <ref target="/bibliography/2"/>
  </p>
</btw:entry>""")
