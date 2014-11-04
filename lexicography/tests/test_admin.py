import os

from django.core.urlresolvers import reverse
from django_webtest import TransactionWebTest

from ..models import Entry
from . import util as test_util

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json"))

class EntryViewTestCase(TransactionWebTest):
    fixtures = ["initial_data.json"] + local_fixtures

    changelist_url = reverse("admin:lexicography_entry_changelist")
    add_raw = reverse("admin:lexicography_entry_rawnew")
    update_raw = reverse("admin:lexicography_entry_rawupdate",
                         args=(1,))

    def generic_unclean(self, url):
        response = self.app.get(url, user="admin")
        form = response.forms['entry_form']
        form['data'] = 'foo'
        response = form.submit()
        self.assertFormError(response, 'form', 'data',
                             [u'The XML passed is unclean!'])

    def generic_no_version(self, url):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0"\
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="LL">
  <btw:lemma></btw:lemma>
</btw:entry>
        """
        response = self.app.get(url, user="admin")
        form = response.forms['entry_form']
        form['data'] = data
        response = form.submit()
        self.assertFormError(response, 'form', 'data',
                             [u'The XML has no version!'])

    def generic_successful(self, url):
        data = Entry.objects.get(lemma='foo').latest.c_hash.data
        data = test_util.stringify_etree(test_util.set_lemma(data, 'foo copy'))
        response = self.app.get(url, user="admin")
        form = response.forms['entry_form']
        form['data'] = data
        form.submit()
        entry = Entry.objects.get(lemma='foo copy')
        chunk = entry.latest.c_hash
        self.assertEqual(chunk.schema_version, "0.10")
        self.assertTrue(chunk.is_normal)
        self.assertEqual(chunk.data, data)

    def test_add_raw_unclean(self):
        self.generic_unclean(self.add_raw)

    def test_add_raw_duplicate(self):
        data = Entry.objects.get(lemma='foo').latest.c_hash.data
        response = self.app.get(self.add_raw, user="admin")
        form = response.forms['entry_form']
        form['data'] = data
        response = form.submit()
        self.assertFormError(response, 'form', 'data',
                             [u'Lemma already present in database: foo'])

    def test_add_raw_no_version(self):
        self.generic_no_version(self.add_raw)

    def test_add_raw_successful(self):
        self.generic_successful(self.add_raw)

    def test_update_raw_unclean(self):
        self.generic_unclean(self.update_raw)

    def test_update_raw_no_version(self):
        self.generic_no_version(self.update_raw)

    def test_update_raw_successful(self):
        self.generic_successful(self.update_raw)
