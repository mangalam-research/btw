import unittest
import os
import lxml.etree

import lib.util as util
from .. import xml
from .data import invalid_sf_cases, valid_sf_cases

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
        self.test_valid()
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
        self.test_valid()
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

    def test_incorrect_semantic_field(self):
        """
        Test that the schematron test will report an error if a semantic
        field is incorrect.
        """
        self.test_valid()
        tree = lxml.etree.fromstring(valid_editable)
        # We remove all semantic-fields from one sense
        sfs = tree.xpath(
            "//btw:sf",
            namespaces={
                "btw": "http://mangalamresearch.org/ns/btw-storage"
            })
        sfs[0].text += "x"
        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertFalse(
            util.schematron(xml.schematron_for_version(schema_version),
                            data))

    def test_incorrect_semantic_field_re(self):
        """
        Test various invalid cases for semantic fields.
        """
        self.test_valid()
        tree = lxml.etree.fromstring(valid_editable)
        sfs = tree.xpath(
            "//btw:sf",
            namespaces={
                "btw": "http://mangalamresearch.org/ns/btw-storage"
            })

        x = 0
        for case in invalid_sf_cases:
            sfs[x].text = case
            x += 1

        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        output_tree = lxml.etree.fromstring(
            util.run_saxon(xml.schematron_for_version(schema_version),
                           data).encode('utf-8'))

        found = output_tree.xpath("//svrl:failed-assert",
                                  namespaces={
                                      'svrl': 'http://purl.oclc.org/dsdl/svrl'
                                  })
        self.assertEqual(len(found), len(invalid_sf_cases))

    def test_correct_semantic_field_re(self):
        """
        Test various valid cases for semantic fields.
        """
        self.test_valid()
        tree = lxml.etree.fromstring(valid_editable)
        sfs = tree.xpath(
            "//btw:sf",
            namespaces={
                "btw": "http://mangalamresearch.org/ns/btw-storage"
            })

        x = 0
        for case in valid_sf_cases:
            sfs[x].text = case
            x += 1

        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        output_tree = lxml.etree.fromstring(
            util.run_saxon(xml.schematron_for_version(schema_version),
                           data).encode('utf-8'))

        found = output_tree.xpath("//svrl:failed-assert",
                                  namespaces={
                                      'svrl': 'http://purl.oclc.org/dsdl/svrl'
                                  })
        self.assertEqual(len(found), 0)
