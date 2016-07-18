# -*- encoding: utf-8 -*-
import unittest
import os
from collections import OrderedDict
import difflib

from lxml.etree import XSLTApplyError
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
            ("1.0", xml.VersionInfo(can_revert=False, can_validate=True)),
            ("1.1", xml.VersionInfo(can_revert=True, can_validate=True))
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

    def test_convert_to_version_1_0_to_1_1(self):
        """
        The function convert_to_version converts 1.0 to 1.1.
        """
        original = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="1.0">
  <btw:sense>
    <btw:english-renditions>
      <btw:english-rendition>
        <btw:english-term>clarity</btw:english-term>
        <btw:semantic-fields>
          <btw:sf>01.04.08.01|02.07n</btw:sf>
        </btw:semantic-fields>
      </btw:english-rendition>
      <btw:english-rendition>
        <btw:english-term>serenity</btw:english-term>
        <btw:semantic-fields>
          <btw:sf>01.02.11.02.01|08.01n</btw:sf>
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
          </btw:semantic-fields>
          <btw:cit><ref target="/bibliography/1">XXX</ref>
          <foreign xml:lang="pi-Latn">[...]</foreign></btw:cit>
          <btw:tr>[...]</btw:tr>
        </btw:example-explained>
      </btw:citations>
    </btw:subsense>
  </btw:sense>
</btw:entry>"""
        result = xml.convert_to_version(original, "1.0", "1.1")

        # We need to use \n\ to protect trailing spaces from being removed from
        # the diff.
        self.assertEqual("".join(difflib.unified_diff(
            original.splitlines(True),
            xml.strip_xml_decl(result)[1].splitlines(True))), """\
--- \n\
+++ \n\
@@ -1,18 +1,14 @@
 \n\
-<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" version="1.0">
+<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" version="1.1">
   <btw:sense>
     <btw:english-renditions>
       <btw:english-rendition>
         <btw:english-term>clarity</btw:english-term>
-        <btw:semantic-fields>
-          <btw:sf>01.04.08.01|02.07n</btw:sf>
-        </btw:semantic-fields>
+        \n\
       </btw:english-rendition>
       <btw:english-rendition>
         <btw:english-term>serenity</btw:english-term>
-        <btw:semantic-fields>
-          <btw:sf>01.02.11.02.01|08.01n</btw:sf>
-        </btw:semantic-fields>
+        \n\
       </btw:english-rendition>
     </btw:english-renditions>
     <btw:subsense xml:id="S.a-1">
""")

    def test_convert_to_version_0_10_to_1_1(self):
        """
        The function convert_to_version converts 0.10 to 1.1.
        """
        original = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="/1" \
version="0.10">
  <btw:sense>
    <btw:english-renditions>
      <btw:english-rendition>
        <btw:english-term>clarity</btw:english-term>
        <btw:semantic-fields>
          <btw:sf>01.04.08.01|02.07n</btw:sf>
        </btw:semantic-fields>
      </btw:english-rendition>
      <btw:english-rendition>
        <btw:english-term>serenity</btw:english-term>
        <btw:semantic-fields>
          <btw:sf>01.02.11.02.01|08.01n</btw:sf>
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
          </btw:semantic-fields>
          <btw:cit><ref target="/bibliography/1">XXX</ref>
          <foreign xml:lang="pi-Latn">[...]</foreign></btw:cit>
          <btw:tr>[...]</btw:tr>
        </btw:example-explained>
      </btw:citations>
    </btw:subsense>
  </btw:sense>
</btw:entry>"""
        result = xml.convert_to_version(original, "0.10", "1.1")

        # We need to use \n\ to protect trailing spaces from being removed from
        # the diff.
        self.assertEqual("".join(difflib.unified_diff(
            original.splitlines(True),
            xml.strip_xml_decl(result)[1].splitlines(True))), """\
--- \n\
+++ \n\
@@ -1,18 +1,14 @@
 \n\
-<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="/1" \
version="0.10">
+<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" version="1.1">
   <btw:sense>
     <btw:english-renditions>
       <btw:english-rendition>
         <btw:english-term>clarity</btw:english-term>
-        <btw:semantic-fields>
-          <btw:sf>01.04.08.01|02.07n</btw:sf>
-        </btw:semantic-fields>
+        \n\
       </btw:english-rendition>
       <btw:english-rendition>
         <btw:english-term>serenity</btw:english-term>
-        <btw:semantic-fields>
-          <btw:sf>01.02.11.02.01|08.01n</btw:sf>
-        </btw:semantic-fields>
+        \n\
       </btw:english-rendition>
     </btw:english-renditions>
     <btw:subsense xml:id="S.a-1">
""")

    def test_convert_to_version_1_0_to_1_1_fails_on_bad_version(self):
        """
        The function convert_to_version fails if the version number is not
        1.0 in the input.
        """
        original = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.9">
</btw:entry>"""
        with self.assertRaisesRegexp(
                XSLTApplyError,
                "The input XML has version 0.9 rather than version 1.0."):
            xml.convert_to_version(original, "1.0", "1.1")

    def test_convert_to_version_0_10_to_1_1_fails_on_bad_version(self):
        """
        The function convert_to_version fails if the version number is not
        0.10 in the input.
        """
        original = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.9">
</btw:entry>"""
        with self.assertRaisesRegexp(
                XSLTApplyError,
                "The input XML has version 0.9 rather than version 0.10."):
            xml.convert_to_version(original, "0.10", "1.1")

    def test_strip_xml_decl_without_decl(self):
        """
        ``strip_xml_decl`` does nothing if there is no XML declaration.
        """
        to_convert = """
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
        """
        decl, result = xml.strip_xml_decl(to_convert)
        self.assertEqual(decl, "", "there should be no XML declaration")
        self.assertEqual(result, to_convert, "the result should be the same")

    def test_strip_xml_decl(self):
        """
        ``strip_xml_decl`` removes the XML declaration if present.
        """
        to_convert = """\
<?xml version="1.0" encoding="utf-8"   ?>
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
        """
        decl, result = xml.strip_xml_decl(to_convert)
        self.assertEqual(decl, '<?xml version="1.0" encoding="utf-8"   ?>',
                         "there should an XML declaration")
        self.assertEqual(result, "\n" + to_convert.split("\n", 1)[1],
                         "the result should be the same")

    def test_wrap_btw_document(self):
        """
        Wraps the document and preserves the XML declaration.
        """
        to_convert = """\
<?xml version="1.0" encoding="utf-8"   ?>
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
</btw:entry>
"""
        self.assertEqual(xml.wrap_btw_document(to_convert,
                                               published=True),
                         """\
<?xml version="1.0" encoding="utf-8"   ?>\
<btw:wrapper xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
published="True">
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
</btw:entry>
</btw:wrapper>""")

    def test_wrap_btw_document_no_decl(self):
        """
        Wraps the document when there is no XML declaration.
        """
        to_convert = """\
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
</btw:entry>
"""
        self.assertEqual(xml.wrap_btw_document(to_convert,
                                               published=False),
                         """\
<btw:wrapper xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
published="False"><btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
</btw:entry>
</btw:wrapper>""")

    def test_unwrap_btw_document(self):
        """
        Unwraps the document and preserves the XML declaration.
        """
        to_convert = """\
<?xml version="1.0" encoding="utf-8"   ?>\
<btw:wrapper xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
published="True">
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
</btw:entry>
</btw:wrapper>"""

        self.assertEqual(xml.unwrap_btw_document(to_convert),
                         """\
<?xml version="1.0" encoding="utf-8"   ?>
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
</btw:entry>
""")

    def test_unwrap_btw_document_no_decl(self):
        """
        Unwraps a document without XML declaration.
        """
        to_convert = """\
<btw:wrapper xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
published="True">
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
</btw:entry>
</btw:wrapper>"""

        self.assertEqual(xml.unwrap_btw_document(to_convert),
                         """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma></btw:lemma>
</btw:entry>
""")

    def test_unwrap_btw_document_fails_on_lacking_start_wrapper(self):
        """
        Fails if the start of the wrapper is missing.
        """
        with self.assertRaisesRegexp(ValueError,
                                     r"^value does not start with wrapper$"):
            xml.unwrap_btw_document("")

    def test_unwrap_btw_document_fails_on_lacking_end_wrapper(self):
        """
        Fails if the end of the wrapper is missing.
        """
        with self.assertRaisesRegexp(ValueError,
                                     r"^value does not end with wrapper$"):
            xml.unwrap_btw_document("<btw:wrapper >")
