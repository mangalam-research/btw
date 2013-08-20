# -*- encoding: utf-8 -*-
from django.utils import unittest
import os
import difflib
import util
from . import views

as_editable_table = {}
def as_editable(filepath):
    editable = as_editable_table.get(filepath, None)
    if editable is not None:
        return editable

    data = open(filepath).read().decode('utf-8')

    # We ask xsltproc not to put out a declaration and add our own.
    tidy = '<?xml version="1.0" encoding="UTF-8"?>' + \
        util.run_xsltproc(os.path.join(views.xsl_dirname, "strip.xsl"),
                          data)

    editable = views.storage_to_editable(tidy)
    as_editable_table[filepath] = editable

    return editable


class DataTestCase(unittest.TestCase):
    def test_roundtrip(self):
        # We don't use as_editable() here because we need the tidy
        # intermediary state.
        data = open(os.path.join(views.schemas_dirname, "prasada.xml")) \
            .read().decode('utf-8')

        # We ask xsltproc not to put out a declaration and add our own.
        tidy = '<?xml version="1.0" encoding="UTF-8"?>' + \
            util.run_xsltproc(os.path.join(views.xsl_dirname, "strip.xsl"),
                              data)
        editable = views.storage_to_editable(tidy)
        final = views.editable_to_storage(editable)

        # There's no way to test whether a generator is empty.
        failed = False
        for line in difflib.unified_diff(tidy.split('\n'), final.split('\n')):
            print line.encode('utf-8')
            failed = True

        self.assertFalse(failed)

class XMLTreeTestCase(unittest.TestCase):
    def test_is_data_unclean_passes(self):
        editable = as_editable(os.path.join(views.schemas_dirname,
                                            "prasada.xml"))
        self.assertFalse(views.XMLTree(editable).is_data_unclean())

    def test_is_data_unclean_fails_on_unparseable(self):
        data ='<div'
        self.assertTrue(views.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_processing_instruction(self):
        data ='''
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
        self.assertTrue(views.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_non_div(self):
        data ='''
<div xmlns="http://www.w3.org/1999/xhtml">
  <div class="head _real"><b></b></div>
</div>'''
        self.assertTrue(views.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_foreign_element(self):
        data ='''
<div xmlns="http://www.w3.org/1999/xhtml">
  <div class="head _real"><div xmlns="q"></div></div>
</div>'''
        self.assertTrue(views.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_bad_attribute(self):
        data ='''
<div xmlns="http://www.w3.org/1999/xhtml">
  <div gaga="q" class="head _real"></div>
</div>'''
        self.assertTrue(views.XMLTree(data).is_data_unclean())

    def test_is_data_unclean_fails_on_foreign_attribute(self):
        data ='''
<div xmlns="http://www.w3.org/1999/xhtml">
  <div xmlns:z="z" z:class="k" class="head _real"></div>
</div>'''
        self.assertTrue(views.XMLTree(data).is_data_unclean())

    def test_extract_headword_passes(self):
        editable = as_editable(os.path.join(views.schemas_dirname,
                                            "prasada.xml"))
        self.assertEqual(views.XMLTree(editable).extract_headword(),
                         u"prasāda")

    def test_extract_headword_fails_when_no_headword(self):
        data = '<div xmlns="http://www.w3.org/1999/xhtml"></div>'
        xmltree = views.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertRaisesRegexp(ValueError,
                                "can't find a headword in the data passed",
                                xmltree.extract_headword)

    def test_extract_authority_passes(self):
        editable = as_editable(os.path.join(views.schemas_dirname,
                                            "prasada.xml"))
        self.assertEqual(views.XMLTree(editable).extract_authority(),
                         "LL")

    def test_extract_headword_fails_when_no_authority(self):
        data = '<div xmlns="http://www.w3.org/1999/xhtml"></div>'
        xmltree = views.XMLTree(data)
        self.assertFalse(xmltree.is_data_unclean())
        self.assertRaisesRegexp(ValueError,
                                "can't find the authority in the data passed",
                                xmltree.extract_authority)




class HandleManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.manager = views.HandleManager("q")

    def test_next_name(self):
        self.assertEqual(self.manager._next_name, "q.0")
        self.assertEqual(self.manager._next_name, "q.1")

    def test_make_associated(self):
        self.assertEqual(self.manager.make_associated(1), "q.0")

    def test_make_associated_returns_constant_values(self):
        self.assertEqual(self.manager.make_associated(1),
                         self.manager.make_associated(1))
        self.assertEqual(self.manager.make_associated(2),
                         self.manager.make_associated(2))

    def test_make_associated_returns_diff_values_for_diff_ids(self):
        self.assertNotEqual(self.manager.make_associated(1),
                            self.manager.make_associated(2))

    def test_make_unassociated_returns_unique_values(self):
        self.assertNotEqual(self.manager.make_unassociated(),
                            self.manager.make_unassociated())

    def test_associate_associates(self):
        handle = self.manager.make_unassociated()
        self.manager.associate(handle, 1)
        self.assertEqual(self.manager.make_associated(1), handle)

    def test_associate_fails_on_already_associated_handle(self):
        handle1 = self.manager.make_associated(1)
        self.assertRaisesRegexp(ValueError,
                                "handle q.0 already associated",
                                self.manager.associate, handle1, 1)

    def test_associate_fails_on_already_associated_id(self):
        self.manager.make_associated(1)
        handle2 = self.manager.make_unassociated()
        self.assertRaisesRegexp(ValueError,
                                "id 1 already associated",
                                self.manager.associate, handle2, 1)


    def test_id_works_with_associated_handle(self):
        handle1 = self.manager.make_associated(1)
        self.assertEqual(self.manager.id(handle1), 1)
        handle2 = self.manager.make_associated(2)
        self.assertEqual(self.manager.id(handle2), 2)

    def test_id_works_with_unassociated_handle(self):
        handle1 = self.manager.make_unassociated()
        self.assertIsNone(self.manager.id(handle1))
