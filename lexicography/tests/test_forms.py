import os
import mock


from django.test import SimpleTestCase

from ..forms import RawSaveForm
from .test_xml import as_editable
from .. import xml

valid_editable = as_editable(os.path.join(xml.schemas_dirname, "prasada.xml"))

class RawSaveFormTest(SimpleTestCase):

    def test_unclean(self):
        form = RawSaveForm(data={'data': 'foo'})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['data'], [u'The XML passed is unclean!'])

    def test_no_version(self):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0"\
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="LL">
  <btw:lemma></btw:lemma>
</btw:entry>
        """
        form = RawSaveForm(data={'data': data})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['data'], [u'The XML has no version!'])

    def test_no_schema(self):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0"\
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" version="0.0" \
  authority="LL">
  <btw:lemma></btw:lemma>
</btw:entry>
        """
        form = RawSaveForm(data={'data': data})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['data'],
                         [u'No schema able to handle schema version: 0.0'])

    # This mock makes the schema check pass so we can get an error for
    # the schematron check.
    @mock.patch("lexicography.xml.schema_for_version_unsafe", lambda *_: "foo")
    def test_no_schematron(self):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0"\
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" version="0.0" \
  authority="LL">
  <btw:lemma></btw:lemma>
</btw:entry>
        """
        form = RawSaveForm(data={'data': data})
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors['data'],
                         [u'No schematron able to handle schema version: 0.0'])

    def test_clean(self):
        form = RawSaveForm(data={'data': valid_editable.decode('utf-8')})
        self.assertTrue(form.is_valid())
        chunk = form.save(commit=False)
        self.assertEqual(chunk.schema_version, "0.10")
