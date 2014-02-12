# -*- encoding: utf-8 -*-
from django.utils import unittest
import os
import difflib
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
                          data)

    editable = xml.storage_to_editable(tidy)
    as_editable_table[filepath] = editable

    return editable


class DataTestCase(unittest.TestCase):
    def test_roundtrip(self):
        # We don't use as_editable() here because we need the tidy
        # intermediary state.
        data = open(os.path.join(xml.schemas_dirname, "prasada.xml")) \
            .read().decode('utf-8')

        # We ask xsltproc not to put out a declaration and add our own.
        tidy = '<?xml version="1.0" encoding="UTF-8"?>' + \
            util.run_xsltproc(os.path.join(xml.xsl_dirname, "strip.xsl"),
                              data)
        editable = xml.storage_to_editable(tidy)
        final = xml.editable_to_storage(editable)

        # There's no way to test whether a generator is empty.
        failed = False
        for line in difflib.unified_diff(tidy.split('\n'), final.split('\n')):
            print line.encode('utf-8')
            failed = True

        self.assertFalse(failed)


class XMLTreeTestCase(unittest.TestCase):
    def test_is_data_unclean_passes(self):
        editable = as_editable(os.path.join(xml.schemas_dirname,
                                            "prasada.xml"))
        self.assertFalse(xml.XMLTree(editable).is_data_unclean())

    def test_is_data_unclean_fails_on_unparseable(self):
        data = '<div'
        self.assertTrue(xml.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_processing_instruction(self):
        data = '''
<div xmlns="http://www.w3.org/1999/xhtml"
     data-wed-xmlns="uri:q" data-wed-xmlns---a="uri:a" class="a:html _real"
     data-wed-a---data-blah--blah----blah="toto" data-wed-z="flex">
  <div class="head _real"><div data-wed-xmlns="uri:default"
       data-wed-xmlns---a="uri:a2" class="a:title _real">ab&amp;
cd&amp;
ef</div></div><?q?>
<div class="body _real">
abc<div class="a:em _real" data-wed-xml---lang="sa-Latn">def&amp;
gh<div class="em _real"></div></div>
</div>
</div>'''
        self.assertTrue(xml.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_non_div(self):
        data = '''
<div xmlns="http://www.w3.org/1999/xhtml">
  <div class="head _real"><b></b></div>
</div>'''
        self.assertTrue(xml.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_foreign_element(self):
        data = '''
<div xmlns="http://www.w3.org/1999/xhtml">
  <div class="head _real"><div xmlns="q"></div></div>
</div>'''
        self.assertTrue(xml.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_bad_attribute(self):
        data = '''
<div xmlns="http://www.w3.org/1999/xhtml">
  <div gaga="q" class="head _real"></div>
</div>'''
        self.assertTrue(xml.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_foreign_attribute(self):
        data = '''
<div xmlns="http://www.w3.org/1999/xhtml">
  <div xmlns:z="z" z:class="k" class="head _real"></div>
</div>'''
        self.assertTrue(xml.XMLTree(data).is_data_unclean())

    def test_extract_headword_passes(self):
        editable = as_editable(os.path.join(xml.schemas_dirname,
                                            "prasada.xml"))
        self.assertEqual(xml.XMLTree(editable).extract_headword(),
                         u"prasāda")

    def test_extract_headword_returns_none_when_no_headword(self):
        data = '<div xmlns="http://www.w3.org/1999/xhtml"></div>'
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_headword())

    def test_extract_headword_returns_none_when_incorrect_class(self):
        # This tests an internal condition in extract_headword
        data = """
<div xmlns="http://www.w3.org/1999/xhtml">
<div class="btw:lemmagaga"></div>
</div>
        """
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_headword())

    def test_extract_headword_returns_none_when_empty_lemma(self):
        data = """
<div xmlns="http://www.w3.org/1999/xhtml">
<div class="btw:lemma"></div>
</div>
        """
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_headword())

    def test_extract_headword_returns_none_when_whitespace_lemma(self):
        data = """
<div xmlns="http://www.w3.org/1999/xhtml">
<div class="btw:lemma">   </div>
</div>
        """
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertIsNone(xmltree.extract_headword())

    def test_extract_authority_passes(self):
        editable = as_editable(os.path.join(xml.schemas_dirname,
                                            "prasada.xml"))
        self.assertEqual(xml.XMLTree(editable).extract_authority(),
                         "LL")

    def test_extract_headword_fails_when_no_authority(self):
        data = '<div xmlns="http://www.w3.org/1999/xhtml"></div>'
        xmltree = xml.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertRaisesRegexp(ValueError,
                                "can't find the authority in the data passed",
                                xmltree.extract_authority)
