import os

from django.urls import reverse
from django_webtest import WebTest
from django.test.utils import override_settings
from cms.test_utils.testcases import BaseCMSTestCase

from ..models import Entry
from ..xml import get_supported_schema_versions
from . import util as test_util
from lib.util import DisableMigrationsMixin

dirname = os.path.dirname(__file__)

@override_settings(ROOT_URLCONF='lexicography.tests.urls')
class EntryViewTestCase(BaseCMSTestCase, DisableMigrationsMixin, WebTest):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "views.json"))

    def setUp(self):
        super(EntryViewTestCase, self).setUp()
        from django.utils import translation
        translation.activate('en-us')
        self.changelist_url = reverse(
            "full-admin:lexicography_entry_changelist")
        self.add_raw = reverse("full-admin:lexicography_entry_rawnew")
        self.update_raw = reverse("full-admin:lexicography_entry_rawupdate",
                                  args=(1,))

    def generic_unclean(self, url):
        response = self.app.get(url, user="admin")
        form = response.forms['entry_form']
        form['data'] = 'foo'
        response = form.submit()
        self.assertFormError(response, 'form', 'data',
                             ['The XML passed is unclean!'])

    def generic_no_version(self, url):
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0"\
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage">
  <btw:lemma></btw:lemma>
</btw:entry>
        """
        response = self.app.get(url, user="admin")
        form = response.forms['entry_form']
        form['data'] = data
        response = form.submit()
        self.assertFormError(response, 'form', 'data',
                             ['The XML has no version!'])

    def generic_successful(self, url):
        data = Entry.objects.get(lemma='foo').latest.c_hash.data
        data = test_util.stringify_etree(test_util.set_lemma(data, 'foo copy'))
        response = self.app.get(url, user="admin")
        form = response.forms['entry_form']
        form['data'] = data
        form.submit()
        entry = Entry.objects.get(lemma='foo copy')
        chunk = entry.latest.c_hash
        self.assertEqual(chunk.schema_version, "1.1")
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
                             ['Lemma already present in database: foo'])

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

    def test_revert_available(self):
        """
        The revert option should be available for ChangeRecord instances
        that have supported versions.
        """

        entry = Entry.objects.get(lemma='foo')
        latest = entry.latest
        latest.c_hash.schema_version = \
            list(get_supported_schema_versions().keys())[-1]
        latest.c_hash.save()
        url = reverse("lexicography_change_revert", args=(latest.pk,))
        response = self.app.get(
            reverse("full-admin:lexicography_entry_change",
                    args=(entry.pk, )),
            user="admin")
        self.assertTrue(response.lxml.xpath("//a[@href='{0}']".format(url)))

    def test_revert_unavailable(self):
        """
        The revert option should be unavailable for ChangeRecord instances
        that have unsupported versions.
        """

        entry = Entry.objects.get(lemma='foo')
        latest = entry.latest
        # We cheat by setting the version to 0.0
        latest.c_hash.schema_version = "0.0"
        latest.c_hash.save()

        url = reverse("lexicography_change_revert", args=(latest.pk,))
        response = self.app.get(
            reverse("full-admin:lexicography_entry_change",
                    args=(entry.pk, )),
            user="admin")
        self.assertFalse(response.lxml.xpath("//a[@href='{0}']".format(url)))


@override_settings(ROOT_URLCONF='lexicography.tests.urls')
class ChangeRecordViewTestCase(BaseCMSTestCase, DisableMigrationsMixin,
                               WebTest):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "views.json"))

    def setUp(self):
        super(ChangeRecordViewTestCase, self).setUp()
        from django.utils import translation
        translation.activate('en-us')

    def test_revert_available(self):
        """
        The revert option should be available for ChangeRecord instances
        that have supported versions.
        """

        latest = Entry.objects.get(lemma='foo').latest
        latest.c_hash.schema_version = \
            list(get_supported_schema_versions().keys())[-1]
        latest.c_hash.save()
        url = reverse("lexicography_change_revert", args=(latest.pk,))
        response = self.app.get(
            reverse("full-admin:lexicography_changerecord_changelist"),
            user="admin")
        self.assertTrue(response.lxml.xpath("//a[@href='{0}']".format(url)))

    def test_revert_unavailable(self):
        """
        The revert option should be unavailable for ChangeRecord instances
        that have unsupported versions.
        """

        latest = Entry.objects.get(lemma='foo').latest
        # We cheat by setting the version to 0.0
        latest.c_hash.schema_version = "0.0"
        latest.c_hash.save()

        url = reverse("lexicography_change_revert", args=(latest.pk,))
        response = self.app.get(
            reverse("full-admin:lexicography_changerecord_changelist"),
            user="admin")
        self.assertFalse(response.lxml.xpath("//a[@href='{0}']".format(url)))
