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

    @classmethod
    def setUpClass(cls):
        # This is really a precondition to the rest of the test
        # suite. If this assertion fails, there's no point in running
        # anything else. It is also a test of sorts because if this
        # fails, then the schematron is wrong or the file is wrong.
        #
        # Running this here instead of checking for every test cuts
        # down considerably on the running time of the test suite.
        #
        assert util.schematron(xml.schematron_for_version(schema_version),
                               valid_editable.decode('utf-8'))

    def test_cognate_without_semantic_fields(self):
        tree = lxml.etree.fromstring(valid_editable)
        # We remove all semantic-fields from one cognate
        sfs = tree.xpath("//btw:cognate[1]//btw:semantic-fields",
                         namespaces=xml.default_namespace_mapping)
        for el in sfs:
            el.getparent().remove(el)
        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertFalse(
            util.schematron(xml.schematron_for_version(schema_version),
                            data))

    def test_sense_without_semantic_fields(self):
        tree = lxml.etree.fromstring(valid_editable)
        # We remove all semantic-fields from one sense
        sfs = tree.xpath(
            "//btw:sense[1]//btw:semantic-fields[not "
            "(ancestor::btw:english-rendition or "
            "ancestor::btw:contrastive-section)]",
            namespaces=xml.default_namespace_mapping)
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
        tree = lxml.etree.fromstring(valid_editable)
        # We remove all semantic-fields from one sense
        sfs = tree.xpath("//btw:sf",
                         namespaces=xml.default_namespace_mapping)
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
        tree = lxml.etree.fromstring(valid_editable)
        sfs = tree.xpath("//btw:sf",
                         namespaces=xml.default_namespace_mapping)

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
        tree = lxml.etree.fromstring(valid_editable)
        sfs = tree.xpath("//btw:sf",
                         namespaces=xml.default_namespace_mapping)

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

    def test_empty_surname(self):
        """
        Test that an empty surname raises an error
        """
        tree = lxml.etree.fromstring(valid_editable)
        surnames = tree.xpath("//tei:surname",
                              namespaces=xml.default_namespace_mapping)

        surnames[0].text = ""

        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertFalse(
            util.schematron(xml.schematron_for_version(schema_version),
                            data))

    def test_no_editor(self):
        """
        Test that a an editor must be recorded.
        """
        tree = lxml.etree.fromstring(valid_editable)
        editors = tree.xpath("//tei:editor",
                             namespaces=xml.default_namespace_mapping)

        for el in editors:
            el.getparent().remove(el)

        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertFalse(
            util.schematron(xml.schematron_for_version(schema_version),
                            data))

    def test_no_author(self):
        """
        Test that a an author must be recorded.
        """
        tree = lxml.etree.fromstring(valid_editable)
        authors = tree.xpath("//btw:credit",
                             namespaces=xml.default_namespace_mapping)

        for el in authors:
            el.getparent().remove(el)

        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertFalse(
            util.schematron(xml.schematron_for_version(schema_version),
                            data))
