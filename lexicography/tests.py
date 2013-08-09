from django.utils import unittest
import os
import subprocess
import views
import difflib
import StringIO
import lxml.etree
import util

def remove_comments(data):
    tree = lxml.etree.fromstring(data)
    comments = tree.xpath('//comment()')
    for c in comments:
        p = c.getparent()
        p.remove(c)

    return lxml.etree.tostring(tree, encoding='unicode')

class RoundTripTestCase(unittest.TestCase):
    def test_roundtrip(self):
        data = open(os.path.join(views.schemas_dirname, "prasada.xml")).read().decode('utf-8')

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
