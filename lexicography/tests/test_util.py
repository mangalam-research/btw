import unittest
import os
import lib.util as util
from .. import xml
import lxml.etree

from .test_xml import as_editable
valid_editable = as_editable(os.path.join(xml.schemas_dirname, "prasada.xml"))
xmltree = xml.XMLTree(valid_editable)
schema_version = xmltree.extract_version()

class SchematronTestCase(unittest.TestCase):

    def test_valid(self):
        self.assertTrue(
            util.schematron(xml.schematron_for_version(schema_version),
                            valid_editable.decode('utf-8')))

    def test_cognate_without_semantic_fields(self):
        self.assertTrue(
            util.schematron(xml.schematron_for_version(schema_version),
                            valid_editable.decode('utf-8')))
        tree = lxml.etree.fromstring(valid_editable)
        # We remove all semantic-fields from one cognate
        sfs = tree.xpath("//btw:cognate[1]//btw:semantic-fields",
                         namespaces={
                             "btw":
                             "http://mangalamresearch.org/ns/btw-storage"
                         })
        for el in sfs:
            el.getparent().remove(el)
        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertFalse(
            util.schematron(xml.schematron_for_version(schema_version),
                            data))

    def test_sense_without_semantic_fields(self):
        self.assertTrue(
            util.schematron(xml.schematron_for_version(schema_version),
                            valid_editable.decode('utf-8')))
        tree = lxml.etree.fromstring(valid_editable)
        # We remove all semantic-fields from one sense
        sfs = tree.xpath(
            "//btw:sense[1]//btw:semantic-fields[not "
            "(ancestor::btw:english-rendition or "
            "ancestor::btw:contrastive-section)]",
            namespaces={
                "btw": "http://mangalamresearch.org/ns/btw-storage"
            })
        for el in sfs:
            el.getparent().remove(el)
        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertFalse(
            util.schematron(xml.schematron_for_version(schema_version),
                            data))
