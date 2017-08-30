# -*- encoding: utf-8 -*-
import cookielib as http_cookiejar
import os
import datetime
import string
import difflib

import lxml.etree
from django_webtest import WebTest, TransactionWebTest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.utils import translation
from cms.test_utils.testcases import BaseCMSTestCase

from .. import models
from ..models import Entry, EntryLock, ChangeRecord, Chunk, PublicationChange
from ..views import REQUIRED_WED_VERSION
from ..xml import get_supported_schema_versions, mods_schema_path, XMLTree, \
    default_namespace_mapping, strip_xml_decl
from . import util as test_util
from . import funcs
import lib.util as util
from .util import inner_normalized_html, launch_fetch_task, \
    create_valid_article
from lib.testutil import wipd

launch_fetch_task()

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json"))

server_name = "http://testserver"
user_model = get_user_model()


def set_lemma(tree, new_lemma):
    return test_util.set_lemma(tree.xpath("//*[@id='id_data']")[0].text,
                               new_lemma)

class ViewsMixin(BaseCMSTestCase):
    fixtures = local_fixtures

    def setUp(self):
        super(ViewsMixin, self).setUp()
        # We must populate the eXist database.
        Chunk.objects.sync_with_exist()
        Chunk.objects.prepare("xml", True)
        translation.activate('en-us')

        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")
        self.noperm = user_model.objects.get(username="noperm")

    def assertSameDBRecord(self, a, b):
        self.assertEqual(type(a), type(b))
        self.assertEqual(a.pk, b.pk)

    def search_table_search(self, title, user,
                            lemmata_only=True,
                            publication_status="both",
                            search_all=False):
        return self.app.get(
            reverse("lexicography_search_table"),
            params={
                "length": -1,
                "search[value]": title,
                "lemmata_only": "true" if lemmata_only else "false",
                "publication_status": publication_status,
                "search_all": "true" if search_all else "false"
            },
            user=user)

    def open_abcd(self, user):
        #
        # User opens for editing the entry with lemma "abcd".
        #
        # Returns the response which has the editing page and the entry
        # object that the user is editing.
        #
        lemma = 'abcd'
        response = self.search_table_search(
            lemma, user, lemmata_only=True)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 1)
        response = self.app.get(hits[lemma]["edit_url"]).follow()
        # Check that a lock as been acquired.
        entry = Entry.objects.get(lemma=lemma)
        lock = EntryLock.objects.get(entry=entry)
        self.assertSameDBRecord(lock.entry, entry)

        # Check the logurl has a good value.
        self.assertEqual(response.form['logurl'].value,
                         reverse('lexicography_log'))
        return response, entry

@override_settings(ROOT_URLCONF='lexicography.tests.urls')
class ViewsTestCase(ViewsMixin, util.DisableMigrationsMixin, WebTest):
    pass

@override_settings(ROOT_URLCONF='lexicography.tests.urls')
class ViewsTransactionTestCase(ViewsMixin,
                               util.DisableMigrationsTransactionMixin,
                               TransactionWebTest):
    pass

class DetailsTestCase(ViewsTestCase):

    def test_has_lemma_in_title(self):
        entry = Entry.objects.get(lemma="abcd")
        response = self.app.get(entry.get_absolute_url())
        self.assertEqual(response.lxml.xpath("/html/head/title/text()")[0]
                         .strip(),
                         "example.com | abcd")

    def test_entry_shows_latest_published(self):
        """
        When a random user views an entry, the default view is that of the
        latest published version.
        """
        entry = Entry.objects.get(lemma="abcd")
        self.assertIsNotNone(entry.latest_published,
                             "the entry should be published")
        response1 = self.app.get(entry.get_absolute_url())

        # We change the entry but do not publish
        c = Chunk(data="""
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma>abcd</btw:lemma>
  <p>
  </p>
</btw:entry>
        """, schema_version="0.10")

        # We lie so that we can perform the test.
        c._valid = True
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        response2 = self.app.get(entry.get_absolute_url())

        self.assertEqual(response1.body, response2.body,
                         "the response should not have changed because "
                         "the new version of the article is not "
                         "published yet")

        # We now publish the change. So the view should be different
        # from the first.
        self.assertTrue(entry.latest.publish(self.foo),
                        "publishing should be successful")
        response3 = self.app.get(entry.get_absolute_url())
        self.assertNotEqual(response1.body, response3.body,
                            "the response should have changed because "
                            "the new version has been published")

    def test_entry_warns_scribe_about_latest_published(self):
        """
        When a scribe views an unpublished entry, and there is a published
        version, there is a warning on the page pointing to the latest
        published version.
        """
        entry = Entry.objects.get(lemma="abcd")
        self.assertIsNotNone(entry.latest_published,
                             "the entry should be published")
        self.assertEqual(entry.latest_published, entry.latest,
                         "the latest version should be the published one")
        response1 = self.app.get(entry.get_absolute_url(), user=self.foo)

        self.assertEqual(
            len(response1.lxml.cssselect('div.article-alert')), 0,
            "there should be no article alerts")

        # We change the entry but do not publish
        c = Chunk(data="""
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma>abcd</btw:lemma>
  <p>
  </p>
</btw:entry>
        """, schema_version="0.10")

        # We lie so that we can perform the test.
        c._valid = True
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        response2 = self.app.get(
            entry.latest.get_absolute_url(), user=self.foo)

        self.assertEqual(
            inner_normalized_html(
                response2.lxml.cssselect("div.article-alert")[0]),
            ('You are looking at an unpublished version of the article. '
             'Follow this <a href="{0}">link</a> to get to the latest '
             'published version.').format(entry.get_absolute_url()),
            "there should be an alert pointing to the latest "
            "published version")

        # We now publish the change. So the alert should be gone.
        self.assertTrue(entry.latest.publish(self.foo),
                        "publishing should be successful")
        response3 = self.app.get(entry.latest.get_absolute_url(),
                                 user=self.foo)
        self.assertEqual(
            len(response1.lxml.cssselect('div.article-alert')), 0,
            "there should be no article alerts")

    def test_warning_does_not_include_link_if_article_never_published(self):
        """
        When a scribe views an unpublished changerecord, and the entry has
        not ever been published, there is no link in the warning.
        """
        entry = Entry.objects.get(lemma="foo")
        self.assertIsNone(entry.latest_published,
                          "the entry should not be published")
        response = self.app.get(
            entry.latest.get_absolute_url(), user=self.foo)

        self.assertEqual(
            inner_normalized_html(
                response.lxml.cssselect("div.article-alert")[0]),
            'You are looking at an unpublished version of the article.',
            "there should be an alert, but not pointing to the latest "
            "published version")

    def test_try_to_view_latest_published_version_of_unpublished_article(self):
        """
        When anyone tries to get the latest published version of an
        unpublished article, they get a 404.
        """
        entry = Entry.objects.get(lemma="foo")
        self.assertIsNone(entry.latest_published,
                          "the entry should not be published")
        response = self.app.get(entry.get_absolute_url(), expect_errors=True)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.body,
                         "You are trying to view the latest published "
                         "version of an article that has never been "
                         "published.")

    def test_try_to_view_a_nonexistent_changerecord(self):
        """
        When anyone tries to view a change record that does not exist,
        they get a nice 404.
        """
        entry = Entry.objects.get(lemma="abcd")
        # We fabricate a URL.
        response = self.app.get(entry.get_absolute_url() + "0/",
                                expect_errors=True)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.body,
                         "You are trying to view a version "
                         "that does not exist.")

    def test_entry_warns_scribe_about_latest_unpublished(self):
        """
        When a scribe views an entry, and there is a newer unpublished
        version, there is a warning on the page.
        """
        entry = Entry.objects.get(lemma="abcd")
        self.assertIsNotNone(entry.latest_published,
                             "the entry should be published")
        self.assertEqual(entry.latest_published, entry.latest,
                         "the latest version should be the published one")
        response1 = self.app.get(entry.get_absolute_url(), user=self.foo)

        self.assertEqual(
            len(response1.lxml.cssselect('div.article-alert')), 0,
            "there should be no article alerts")

        # We change the entry but do not publish
        c = Chunk(data="""
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma>abcd</btw:lemma>
  <p>
  </p>
</btw:entry>
        """, schema_version="0.10")

        # We lie so that we can perform the test.
        c._valid = True
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        response2 = self.app.get(
            entry.get_absolute_url(), user=self.foo)

        self.assertEqual(
            inner_normalized_html(
                response2.lxml.cssselect("div.article-alert")[0]),
            ('There is a <a href="{0}">newer unpublished version</a> '
             'of this article.').format(entry.latest.get_absolute_url()),
            "there should be an alert pointing to the latest "
            "unpublished version")

        # We now publish the change. So the alert should be gone.
        self.assertTrue(entry.latest.publish(self.foo),
                        "publishing should be successful")
        response3 = self.app.get(entry.get_absolute_url(),
                                 user=self.foo)
        self.assertEqual(
            len(response1.lxml.cssselect('div.article-alert')), 0,
            "there should be no article alerts")

    def test_entry_warns_user_about_latest_published(self):
        """
        When a user views an entry, and there is a newer published
        version, there is a warning on the page pointing to the latest
        published version.
        """
        entry = Entry.objects.get(lemma="abcd")
        self.assertIsNotNone(entry.latest_published,
                             "the entry should be published")
        self.assertEqual(entry.latest_published, entry.latest,
                         "the latest version should be the published one")
        response1 = self.app.get(entry.get_absolute_url())

        self.assertEqual(
            len(response1.lxml.cssselect('div.article-alert')), 0,
            "there should be no article alerts")

        old_published = entry.latest_published

        c = Chunk(data="""
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma>abcd</btw:lemma>
  <p>
  </p>
</btw:entry>
        """, schema_version="0.10")

        # We lie so that we can perform the test.
        c._valid = True
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        # We now publish the change. So the alert should be gone.
        self.assertTrue(entry.latest.publish(self.foo),
                        "publishing should be successful")
        response2 = self.app.get(old_published.get_absolute_url())

        self.assertEqual(
            inner_normalized_html(
                response2.lxml.cssselect("div.article-alert")[0]),
            ('There is a <a href="{0}">newer published version</a> '
             'of this article.').format(entry.get_absolute_url()),
            "there should be an alert pointing to the latest "
            "published version")

    def test_entry_history_marks_correct_version_as_the_one_viewed(self):
        """
        When a random user views an entry, the article history shows the
        correct version as the one being viewed.
        """
        entry = Entry.objects.get(lemma="abcd")
        self.assertIsNotNone(entry.latest_published,
                             "the entry should be published")
        first_published = entry.latest_published
        response1 = self.app.get(entry.get_absolute_url())
        lis = response1.lxml.cssselect("div#history-modal ul > li")
        self.assertEqual(len(lis), 1,
                         "there should be one published version")

        self.assertTrue(
            inner_normalized_html(lis[0])
            .endswith("You are currently looking at this version."),
            "the first history entry should be marked as the current one")
        self.assertTrue(
            lis[0].cssselect("i.fa-arrow-right"),
            "the first history entry should have an arrow")

        # We change the entry but do not publish
        c = Chunk(data="""
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma>abcd</btw:lemma>
  <p>
  </p>
</btw:entry>
        """, schema_version="0.10")

        # We lie so that we can perform the test.
        c._valid = True
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        response2 = self.app.get(entry.get_absolute_url())

        self.assertEqual(response1.body, response2.body,
                         "the response should not have changed because "
                         "the new version of the article is not "
                         "published yet")

        # We now publish the change. So the view should be different
        # from the first.
        self.assertTrue(entry.latest.publish(self.foo),
                        "publishing should be successful")
        response3 = self.app.get(entry.get_absolute_url())
        self.assertNotEqual(response1.body, response3.body,
                            "the response should have changed because "
                            "the new version has been published")

        lis = response3.lxml.cssselect("div#history-modal ul > li")
        self.assertEqual(len(lis), 2,
                         "there should be two published versions")
        self.assertTrue(
            inner_normalized_html(lis[0])
            .endswith("You are currently looking at this version."),
            "the first history entry should be marked as the current one")
        self.assertTrue(
            lis[0].cssselect("i.fa-arrow-right"),
            "the first history entry should have an arrow")
        self.assertFalse(
            inner_normalized_html(lis[1])
            .endswith("You are currently looking at this version."),
            "the other history entry should not be marked as the current one")
        self.assertFalse(
            lis[1].cssselect("i.fa-arrow-right"),
            "the other history entry should not have an arrow")

        # Check the URLs too.
        published = entry.changerecord_set.filter(published=True) \
                                          .order_by("-datetime")
        ix = 0
        for pub in published:
            self.assertEqual(lis[ix].cssselect("a")[0].get("href"),
                             pub.get_absolute_url(),
                             ("the URL of item {0} should correspond to the "
                              "URL of published version {0}").format(ix))
            ix += 1

        # We're looking at the earlier published version.
        response4 = self.app.get(first_published.get_absolute_url())
        lis = response4.lxml.cssselect("div#history-modal ul > li")
        self.assertEqual(len(lis), 2,
                         "there should be two published versions")
        self.assertFalse(
            inner_normalized_html(lis[0])
            .endswith("You are currently looking at this version."),
            "the first history entry should not be marked as the current one")
        self.assertFalse(
            lis[0].cssselect("i.fa-arrow-right"),
            "the first history entry should not have an arrow")
        self.assertTrue(
            inner_normalized_html(lis[1])
            .endswith("You are currently looking at this version."),
            "the other history entry should be marked as the current one")
        self.assertTrue(
            lis[1].cssselect("i.fa-arrow-right"),
            "the other history entry should have an arrow")

    def test_scribe_viewing_unpublished_has_nothing_marked_in_history(self):
        """
        When a scribe views an unpublished entry, the article history does
        not mark anything. Also, there is a notice that the history
        shows only published versions.
        """
        entry = Entry.objects.get(lemma="abcd")
        self.assertIsNotNone(entry.latest_published,
                             "the entry should be published")
        self.assertEqual(entry.latest_published, entry.latest,
                         "the latest version should be the published one")

        # We change the entry but do not publish
        c = Chunk(data="""
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma>abcd</btw:lemma>
  <p>
  </p>
</btw:entry>
        """, schema_version="0.10")

        # We lie so that we can perform the test.
        c._valid = True
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        response1 = self.app.get(
            entry.latest.get_absolute_url(), user=self.foo)

        lis = response1.lxml.cssselect("div#history-modal ul > li")
        self.assertEqual(len(lis), 1,
                         "the list should have the single published version")
        self.assertFalse(
            inner_normalized_html(lis[0])
            .endswith("You are currently looking at this version."),
            "the single version in the list should not be marked as the "
            "one being viewed")
        self.assertFalse(
            lis[0].cssselect("i.fa-arrow-right"),
            "the other history entry should not have an arrow")

        modal_body = response1.lxml.cssselect(
            "div#history-modal .modal-body > p")[0]
        self.assertTrue(
            inner_normalized_html(modal_body)
            .startswith("This list here shows only those versions that "
                        "have been published."),
            "the modal should show a warning about unpublished "
            "versions")

    def test_permalinks(self):
        """
        When the details view has a modals that will show correct
        permalinks.
        """
        entry = Entry.objects.get(lemma="abcd")
        self.assertIsNotNone(entry.latest_published,
                             "the entry should be published")
        self.assertEqual(entry.latest_published, entry.latest,
                         "the latest version should be the published one")

        response = self.app.get(entry.get_absolute_url())
        modal = response.lxml.cssselect("div#link-modal")[0]
        links = modal.cssselect("a")
        self.assertEqual(links[0].get("href"),
                         entry.get_absolute_url(),
                         "the first link should be the entry's absolute URL")
        self.assertEqual(links[1].get("href"),
                         entry.latest_published.get_absolute_url(),
                         "the second link should be the latest published "
                         "version's absolute URL")

    def test_permalinks_unpublished(self):
        """
        When a scribe views an unpublished entry, there is a notice that
        the second permalink cannot be used by non-scribes.
        """
        entry = Entry.objects.get(lemma="abcd")
        self.assertIsNotNone(entry.latest_published,
                             "the entry should be published")
        self.assertEqual(entry.latest_published, entry.latest,
                         "the latest version should be the published one")

        # We change the entry but do not publish
        c = Chunk(data="""
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage" \
version="0.10" authority="/1">
  <btw:lemma>abcd</btw:lemma>
  <p>
  </p>
</btw:entry>
        """, schema_version="0.10")

        # We lie so that we can perform the test.
        c._valid = True
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        response = self.app.get(
            entry.latest.get_absolute_url(), user=self.foo)
        modal = response.lxml.cssselect("div#link-modal")[0]
        links = modal.cssselect("a")
        self.assertTrue(inner_normalized_html(links[1].getparent())
                        .endswith("""\
<strong>Note that you are currently viewing an unpublished version of \
the article. If you provide this link to someone who cannot edit BTW \
articles, they will not be able to use the link, unless this exact version is \
published before they use the link.</strong>\
"""),
                        "there should be a warning")

#
# This FormatDict and the method to partially apply a format is taken
# from this StackOverflow answer:
#
# http://stackoverflow.com/a/11284026/
#
class FormatDict(dict):

    def __missing__(self, key):
        return "{" + key + "}"

class ModsTestCase(ViewsTestCase):

    mods_template_without_names = """\
<?xml version="1.0"?>\
<modsCollection xmlns="http://www.loc.gov/mods/v3" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.loc.gov/mods/v3 \
http://www.loc.gov/standards/mods/v3/mods-3-5.xsd"><mods>\
<titleInfo><title>prasāda</title></titleInfo>\
<typeOfResource>text</typeOfResource>\
<genre authority="local">dictionaryEntry</genre>\
<genre authority="marcgt">article</genre>\
{names}\
<relatedItem type="host"><genre authority="marcgt">dictionary</genre>\
<originInfo><edition>version {version}</edition>\
<place><placeTerm type="text">Berkeley</placeTerm></place>\
<publisher>Mangalam Research Center for Buddhist Languages</publisher>\
<dateCreated>{year}</dateCreated><issuance>continuing</issuance></originInfo>\
<titleInfo><title>Buddhist Translators Workbench</title></titleInfo>\
<name type="personal"><namePart type="family">Gómez</namePart>\
<namePart type="given">Luis</namePart>\
<role><roleTerm type="code" authority="marcrelator">edc</roleTerm></role>\
</name>\
<name type="personal"><namePart type="family">Lugli</namePart>\
<namePart type="given">Ligeia</namePart>\
<role><roleTerm type="code" authority="marcrelator">edc</roleTerm></role>\
</name>\
</relatedItem><location><url dateLastAccessed="2015-01-02">{url}</url>\
</location></mods></modsCollection>\n"""

    mods_template = string.Formatter().vformat(mods_template_without_names,
                                               (),
                                               FormatDict({'names': """\
<name type="personal"><namePart type="family">Doe</namePart>\
<namePart type="given">Jane</namePart>\
<role><roleTerm type="code" authority="marcrelator">aut</roleTerm>\
</role></name>\
<name type="personal"><namePart type="family">Doeh</namePart>\
<namePart type="given">John</namePart><role>\
<roleTerm type="code" authority="marcrelator">aut</roleTerm></role></name>\
<name type="personal"><namePart type="family">Lovelace</namePart>\
<namePart type="given">Ada</namePart>\
<role><roleTerm type="code" authority="marcrelator">edt</roleTerm>\
</role></name>\
"""}))

    def setUp(self):
        super(ModsTestCase, self).setUp()
        self.entry = create_valid_article()
        self.assertTrue(self.entry.latest.publish(self.foo))
        # Reacquire the object with the proper value of latest_published.
        self.entry = Entry.objects.get(id=self.entry.id)

    def assertValid(self, mods):
        self.assertTrue(
            util.validate_with_xmlschema(mods_schema_path,
                                         mods.decode("utf-8")),
            "the resulting data should be valid")

    def test_missing_access_date(self):
        """
        Tests that if the access-date parameter is missing, we get a
        reasonable error message.
        """
        entry = self.entry

        response = self.app.get(reverse("lexicography_entry_mods",
                                        args=(entry.id,)),
                                expect_errors=True)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, "access-date is a required parameter")

    def test_unpublished_entry(self):
        """
        Tests that if a non-version-specific MODS is requested and the
        entry has never been published, then we get a reasonable error
        message.
        """
        entry = Entry.objects.get(lemma="foo")
        self.assertIsNone(entry.latest_published,
                          "the entry must not have been published already")

        response = self.app.get(
            reverse("lexicography_entry_mods",
                    args=(entry.id,)),
            params={"access-date": "2015-01-02"},
            expect_errors=True)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, "this entry has never been "
                         "published: you must request a "
                         "specific change record")

    def test_non_version_specific_no_changerecord(self):
        """
        Tests that generating a MODS with a non-version specific URL
        works, when no ChangeRecord is specified.
        """
        entry = self.entry

        response = self.app.get(reverse("lexicography_entry_mods",
                                        args=(entry.id,)),
                                params={
                                    "access-date": "2015-01-02"
        })

        xml_params = {
            'version': util.version(),
            'year': datetime.date.today().year,
            'url': server_name + entry.get_absolute_url()
        }

        self.assertEqual(
            response.body, self.mods_template.format(**xml_params))
        self.assertValid(response.body)

    def test_non_version_specific_changerecord(self):
        """
        Tests that generating a MODS with a non-version specific URL
        works, when a ChangeRecord is specified.
        """
        entry = self.entry
        # We change the entry but do not publish
        entry.update(
            self.foo,
            "q",
            entry.latest.c_hash,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        # Reacquire after the change
        entry = Entry.objects.get(id=entry.id)

        response = self.app.get(reverse("lexicography_entry_mods",
                                        args=(entry.id, entry.latest.id)),
                                params={
                                    "access-date": "2015-01-02"
        })

        xml_params = {
            'version': util.version(),
            'year': datetime.date.today().year,
            'url': server_name + entry.get_absolute_url()
        }

        self.assertEqual(
            response.body, self.mods_template.format(**xml_params))
        self.assertValid(response.body)

    def test_version_specific_no_changerecord_id(self):
        """
        Tests that generating a MODS with a version-specific URL works
        when no ChangeRecord is specified.
        """
        entry = self.entry

        response = self.app.get(reverse("lexicography_entry_mods",
                                        args=(entry.id,)),
                                params={
                                    "access-date": "2015-01-02",
                                    "version-specific": "true"
        })

        xml_params = {
            'version': util.version(),
            'year': datetime.date.today().year,
            'url': server_name + entry.latest_published.get_absolute_url()
        }

        self.assertEqual(
            response.body, self.mods_template.format(**xml_params))
        self.assertValid(response.body)

    def test_version_specific_changerecord_id(self):
        """
        Tests that generating a MODS with a version-specific URL works
        when a ChangeRecord is specified.
        """
        entry = self.entry

        # We change the entry but do not publish
        entry.update(
            self.foo,
            "q",
            entry.latest.c_hash,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        # Reacquire after the change
        entry = Entry.objects.get(id=entry.id)

        response = self.app.get(reverse("lexicography_entry_mods",
                                        args=(entry.id, entry.latest.id)),
                                params={
                                    "access-date": "2015-01-02",
                                    "version-specific": "true"
        })

        xml_params = {
            'version': util.version(),
            'year': datetime.date.today().year,
            'url': server_name + entry.latest.get_absolute_url()
        }

        self.assertEqual(
            response.body, self.mods_template.format(**xml_params))
        self.assertValid(response.body)

    def test_name_without_first_name(self):
        """
        Tests that generating a MODS with a name that does not have a
        first name works.
        """
        entry = self.entry

        tree = XMLTree(entry.latest.c_hash.data)
        forenames = tree.tree.xpath("//tei:forename",
                                    namespaces=default_namespace_mapping)
        for forename in forenames:
            forename.text = ""

        c = Chunk(data=test_util.stringify_etree(tree.tree),
                  schema_version=entry.latest.c_hash.schema_version)
        # Yes, we cheat.
        c._valid = True
        c.save()

        # We change the entry but do not publish
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        # Reacquire after the change
        entry = Entry.objects.get(id=entry.id)

        response = self.app.get(reverse("lexicography_entry_mods",
                                        args=(entry.id, entry.latest.id)),
                                params={"access-date": "2015-01-02"})

        xml_params = {
            'version': util.version(),
            'year': datetime.date.today().year,
            'url': server_name + entry.get_absolute_url(),
            'names': """\
<name type="personal"><namePart type="family">Doe</namePart>\
<role><roleTerm type="code" authority="marcrelator">aut</roleTerm>\
</role></name>\
<name type="personal"><namePart type="family">Doeh</namePart><role>\
<roleTerm type="code" authority="marcrelator">aut</roleTerm></role></name>\
<name type="personal"><namePart type="family">Lovelace</namePart>\
<role><roleTerm type="code" authority="marcrelator">edt</roleTerm>\
</role></name>\
"""
        }

        self.assertEqual(
            response.body,
            self.mods_template_without_names.format(**xml_params))
        self.assertValid(response.body)

    def test_name_with_genName(self):
        """
        Tests that generating a MODS with a genName works.
        """
        entry = self.entry

        tree = XMLTree(entry.latest.c_hash.data)
        names = tree.tree.xpath("//tei:genName",
                                namespaces=default_namespace_mapping)
        for name in names:
            name.text = "fo<o"

        c = Chunk(data=test_util.stringify_etree(tree.tree),
                  schema_version=entry.latest.c_hash.schema_version)
        # Yes, we cheat.
        c._valid = True
        c.save()

        # We change the entry but do not publish
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        # Reacquire after the change
        entry = Entry.objects.get(id=entry.id)

        response = self.app.get(reverse("lexicography_entry_mods",
                                        args=(entry.id, entry.latest.id)),
                                params={"access-date": "2015-01-02"})

        xml_params = {
            'version': util.version(),
            'year': datetime.date.today().year,
            'url': server_name + entry.get_absolute_url(),
            'names': """\
<name type="personal"><namePart type="family">Doe</namePart>\
<namePart type="given">Jane</namePart>\
<namePart type="termsOfAddress">fo&lt;o</namePart>\
<role><roleTerm type="code" authority="marcrelator">aut</roleTerm>\
</role></name>\
<name type="personal"><namePart type="family">Doeh</namePart>\
<namePart type="given">John</namePart>\
<namePart type="termsOfAddress">fo&lt;o</namePart>\
<role><roleTerm type="code" authority="marcrelator">aut</roleTerm>\
</role></name>\
<name type="personal"><namePart type="family">Lovelace</namePart>\
<namePart type="given">Ada</namePart>\
<namePart type="termsOfAddress">fo&lt;o</namePart>\
<role><roleTerm type="code" authority="marcrelator">edt</roleTerm>\
</role></name>\
"""
        }

        self.assertEqual(
            response.body,
            self.mods_template_without_names.format(**xml_params))
        self.assertValid(response.body)


class MainTestCase(ViewsTestCase):

    def test_main(self):
        """
        Tests that a logged in user can view the main page.
        """
        self.app.get(reverse("lexicography_main"), user=self.foo)

    def test_search_table(self):
        """
        Tests that the search table ajax calls can go through.
        """
        self.search_table_search("abcd", self.foo)

    def test_search_by_non_scribe_gets_no_edit_link_on_locked_articles(self):
        """
        Tests that when an article is already locked by user X and user Y
        does a search, and user Y is not able to edit articles, then
        user Y is not going to see any information about locking.
        """
        response, entry = self.open_abcd('foo')

        entry = Entry.objects.get(lemma="abcd")
        response = self.search_table_search("abcd", self.noperm)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 1)
        self.assertEqual(len(hits["abcd"]["hits"]), 1)

        # Check that the edit option is not available
        url = reverse('lexicography_entry_update', args=(entry.id, ))
        self.assertNotIn(url, response)

        # And the user is *NOT* told that the article is locked.
        self.assertNotIn("Locked by", response)

    def test_search_by_non_scribe_does_not_return_unpublished_articles(self):
        """
        Someone who is not a scribe cannot see unpublished articles.
        """
        entry = Entry.objects.get(lemma="foo")
        self.assertIsNone(entry.latest_published,
                          "Our entry must not have been published already")
        response = self.search_table_search("foo", self.noperm)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 0)

        # Simulate a case where the user manually adds the search
        # parameters to a URL.
        response = self.search_table_search("foo", self.noperm,
                                            publication_status="both")
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 0)

    def test_search_by_non_scribe_does_not_return_deleted_articles(self):
        """
        Someone who is not a scribe cannot see deleted articles.
        """
        entry = Entry.objects.get(lemma="abcd")
        response = self.search_table_search("abcd", self.noperm)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 1)
        # But delete it.
        entry.deleted = True
        entry.save()
        response = self.search_table_search("abcd", self.noperm)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 0)

        # Simulate a case where the user manually adds the search
        # parameters to a URL.
        response = self.search_table_search("abcd", self.noperm,
                                            search_all=True)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 0)

    def test_search_lemma_by_scribe_can_return_unpublished_articles(self):
        """
        Someone who is a scribe can see unpublished articles.
        """
        entry = Entry.objects.get(lemma="foo")
        self.assertIsNone(entry.latest_published,
                          "Our entry must not have been published already")

        # Try with "both"
        response = self.search_table_search("foo", self.foo,
                                            publication_status="both")
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 1)
        self.assertEqual(len(hits["foo"]["hits"]), 1)

        # And "unpublished"
        response = self.search_table_search("foo", self.foo,
                                            publication_status="unpublished")
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 1)
        self.assertEqual(len(hits["foo"]["hits"]), 1)

    def test_search_lemma_by_scribe_can_return_deleted_articles(self):
        """
        Someone who is a scribe can see unpublished articles.
        """
        entry = Entry.objects.get(lemma="foo")
        self.assertIsNone(entry.latest_published,
                          "Our entry must not have been published already")
        # Delete it.
        entry.deleted = True
        entry.save()

        response = self.search_table_search("foo", self.foo,
                                            publication_status="both",
                                            search_all=True)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 1)
        self.assertEqual(len(hits["foo"]["hits"]), 1)
        self.assertEqual(hits["foo"]["hits"][0]["deleted"], "Yes")

    def test_search_by_scribe_can_return_unpublished_articles(self):
        """
        Someone who is a scribe can see unpublished articles.
        """
        # This just ensures that there **are** unpublished entries.
        self.assertTrue(
            Entry.objects.filter(latest_published__isnull=True).count() > 0)
        count = Entry.objects.active_entries().count()

        # Try with "both"
        response = self.search_table_search("", self.foo,
                                            publication_status="both")
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(funcs.count_hits(hits), count)

        # And "unpublished"
        response = self.search_table_search("", self.foo,
                                            publication_status="unpublished")
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(funcs.count_hits(hits),
                         Entry.objects.active_entries()
                         .filter(latest_published__isnull=True).count())

    def test_search_by_scribe_can_return_deleted_articles(self):
        """
        Someone who is a scribe can see deleted articles.
        """
        # We delete one.
        entry = Entry.objects.get(lemma="abcd")
        count = Entry.objects.active_entries().count()
        # Delete it.
        entry.deleted = True
        entry.save()

        response = self.search_table_search("", self.foo,
                                            publication_status="both")
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(funcs.count_hits(hits), count - 1)

        # And "unpublished"
        response = self.search_table_search("", self.foo,
                                            publication_status="unpublished",
                                            search_all=True)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(funcs.count_hits(hits),
                         ChangeRecord.objects.filter(published=False)
                         .values_list("entry").count())
        self.assertEqual(funcs.count_hits(hits),
                         ChangeRecord.objects.filter(published=False).count())

    def test_search_by_scribe_shows_schema_version(self):
        """
        Someone who is a scribe can see schema versions.
        """
        entry = Entry.objects.get(lemma="abcd")

        c = Chunk(data=entry.latest.c_hash.data,
                  schema_version="0.0")
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        response = self.search_table_search("abcd", self.foo)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(funcs.count_hits(hits), 1)
        hits = hits["abcd"]["hits"]
        self.assertEqual(hits[0]["schema_version"], "0.0")
        self.assertTrue(hits[0]["schema_update"])

    def test_search_by_scribe_does_not_show_schema_upgrade_warning(self):
        """
        Someone who is a scribe can see schema versions but won't see an
        upgrade warning if there is no need to upgrade.
        """

        entry = Entry.objects.get(lemma="abcd")

        latest_version = get_supported_schema_versions().keys()[-1]
        c = Chunk(data=entry.latest.c_hash.data,
                  schema_version=latest_version)
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        response = self.search_table_search("abcd", self.foo)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(funcs.count_hits(hits), 1)
        hits = hits["abcd"]["hits"]
        self.assertEqual(hits[0]["schema_version"], latest_version)
        self.assertFalse(hits[0]["schema_update"])

    def test_search_link_to_old_records_show_old_records(self):
        """
        The view links to old records show the old data, and not the
        latest version of the article.
        """
        response = self.search_table_search("old and new records", self.foo,
                                            publication_status="both",
                                            search_all=True)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 1)
        hits = hits["old and new records"]["hits"]
        self.assertEqual(len(hits), 3)
        hits.sort(lambda a, b: -cmp(a["datetime"], b["datetime"]))
        # We load the newest version and inspect it. It should contain
        # a paragraph with "Newer" in it.
        response = self.app.get(hits[0]["view_url"])
        tree = response.lxml
        data = tree.xpath("//script[@id='wed-data']")[0].text
        self.assertTrue(data.find("<p>Newer<p>"))

        # The previous version should not have "Newer" in it.
        response = self.app.get(hits[1]["view_url"])
        tree = response.lxml
        data = tree.xpath("//script[@id='wed-data']")[0].text
        self.assertEqual(data.find("<p>Newer<p>"), -1)

    def test_search_old_records_do_not_have_edit_links(self):
        """
        Only the latest change record of an entry should have an edit
        link. Old ones should not have edit links.
        """
        response = self.search_table_search("old and new records", self.foo,
                                            publication_status="both",
                                            search_all=True)
        hits = funcs.parse_search_results(response.body)
        self.assertEqual(len(hits), 1)
        hits = hits["old and new records"]["hits"]
        self.assertEqual(len(hits), 3)
        hits.sort(lambda a, b: -cmp(a["datetime"], b["datetime"]))
        self.assertTrue(hits[0]["edit_url"],
                        "The most recent entry should have an edit link")
        self.assertIsNone(hits[1]["edit_url"],
                          "Older entries should not have an edit link")
        self.assertIsNone(hits[2]["edit_url"],
                          "Older entries should not have an edit link")


class EditingTestCase(ViewsTransactionTestCase):

    def open_new(self, user):
        #
        # User opens a new entry for editing.
        #
        # Returns the response which has the editing page.
        #
        response =\
            self.app.get(
                reverse('lexicography_entry_new'), user=user).maybe_follow()
        # Check the logurl has a good value.
        self.assertEqual(response.form['logurl'].value,
                         reverse('lexicography_log'))

        return response

    def save(self, response, user, data=None, command="save",
             expect_errors=False):
        #
        # Saves the document.
        #
        # response: the response which presents the editing page to the user.
        #
        # data: the data to save, if none we just reuse the data that
        # was provided on the response page.
        #
        # Returns (parsed messages, data that was passed for saving)
        #
        saveurl = response.form['saveurl'].value

        if data is None:
            data = response.lxml.xpath("//*[@id='id_data']")[0].text

        params = {
            "command": command,
            "version": REQUIRED_WED_VERSION,
            "data": data
        }

        etag = response.form['initial_etag'].value.encode('utf-8')
        headers = {
            'X-REQUESTED-WITH': 'XMLHttpRequest',
            'X-CSRFToken':
            response.form['csrfmiddlewaretoken'].value.encode('utf-8'),
        }

        if etag != "":
            # The etag must be put in quotes.
            headers['If-Match'] = '"{}"'.format(etag)

        response = self.app.post(
            saveurl,
            user=user,
            params=params,
            content_type='application/x-www-form-urlencoded; charset=UTF-8',
            expect_errors=expect_errors,
            headers=headers)

        if expect_errors:
            return response
        else:
            return test_util.parse_response_to_wed(response.json), \
                params["data"]

    def close(self, response, entry, user):
        url = reverse('lexicography_handle_update', args=(entry.id, ))
        headers = {
            'X-CSRFToken':
            response.form['csrfmiddlewaretoken'].value.encode('utf-8')
        }
        response = self.app.post(url,
                                 user=user, headers=headers).follow()
        return response

    def test_edit(self):
        """
        Tests that a user with editing rights can edit an entry obtained
        by searching.
        """
        response, old_entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=old_entry).count()

        messages, data = self.save(response, 'foo')

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        self.assertEqual(ChangeRecord.objects.filter(entry=old_entry).count(),
                         nr_changes + 1,
                         "there is one and only one additional record change")

        # Check that we recorded the right thing.
        entry = Entry.objects.get(pk=old_entry.pk)
        self.assertEqual(entry.latest.user, self.foo)
        # The delay used here is arbitrary
        self.assertTrue(util.utcnow() -
                        entry.latest.datetime <= datetime.timedelta(minutes=1))
        self.assertEqual(entry.latest.session, self.app.session.session_key)
        self.assertEqual(entry.latest.ctype, ChangeRecord.UPDATE)
        self.assertEqual(entry.latest.csubtype, ChangeRecord.MANUAL)

        # Check the chunk
        self.assertEqual(entry.latest.c_hash.data, data)
        self.assertTrue(entry.latest.c_hash.is_normal)

        self.assertNotEqual(old_entry.latest.pk, entry.latest.pk)

    def test_edit_corrupted(self):
        """
        Tests that the server responds with an error message upon trying
        to save corrupted data, and that only an abnormal chunk is saved.
        """
        response, entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=entry).count()
        old_abnormal_chunks = [c.pk for c in
                               Chunk.objects.filter(is_normal=False)]

        # "q" is clearly not valid
        messages, _ = self.save(response, 'foo', "q")

        self.assertEqual(len(messages), 1)
        self.assertIn("save_fatal_error", messages)

        self.assertEqual(ChangeRecord.objects.filter(entry=entry).count(),
                         nr_changes,
                         "no change to the entry")

        # Check that the abnormal data was recorded
        abnormal_chunks = Chunk.objects.filter(is_normal=False)
        self.assertEqual(len(old_abnormal_chunks) + 1,
                         abnormal_chunks.count())
        new_abnormal_chunk = [c for c in abnormal_chunks
                              if c.pk not in old_abnormal_chunks][0]
        self.assertEqual(new_abnormal_chunk.data, "q")

    def test_edit_missing_lemma(self):
        """
        Tests that the server responds with an error message upon trying
        to save an entry without lemma, and that nothing is saved.
        """
        # Tests what happens if a user tries to save without a lemma set.
        response, entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=entry).count()
        nr_chunks = Chunk.objects.all().count()

        # Delete the lemma.
        data_tree = set_lemma(response.lxml, None)

        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_transient_error", messages)
        self.assertEqual(len(messages["save_transient_error"]), 1)
        self.assertEqual(messages["save_transient_error"][0]["msg"],
                         "Please specify a lemma for your entry.")

        # Check that no new data was recorded
        self.assertEqual(ChangeRecord.objects.filter(entry=entry).count(),
                         nr_changes,
                         "no change to the entry")

        self.assertEqual(nr_chunks, Chunk.objects.all().count())

    def test_edit_duplicate_lemma(self):
        """
        Tests that the server responds with an error message upon trying
        to save an entry that duplicates another entry's lemma, and
        that nothing is saved.
        """
        response = self.open_new("foo")

        data_tree = set_lemma(response.lxml, u"prasāda")

        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        entry = Entry.objects.get(lemma=u"prasāda")
        nr_changes = ChangeRecord.objects.filter(entry=entry).count()
        nr_chunks = Chunk.objects.all().count()

        response = self.open_new("foo")

        data_tree = set_lemma(response.lxml, u"prasāda")
        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_transient_error", messages)
        self.assertEqual(len(messages["save_transient_error"]), 1)
        self.assertEqual(
            messages["save_transient_error"][0]["msg"],
            u'There is another entry with the lemma "prasāda".')

        # Check that no new data was recorded
        self.assertEqual(ChangeRecord.objects.filter(entry=entry).count(),
                         nr_changes,
                         "no change to the entry")

        self.assertEqual(nr_chunks, Chunk.objects.all().count())

    def test_subsequent_save_is_not_duplicate(self):
        """
        Tests that the server has no problem with saving a new entry
        twice. Namely that it does not issue a duplicate lemma error.
        """

        nr_entries = Entry.objects.count()
        response = self.open_new('foo')

        # Does not create a new entry until we save.
        self.assertEqual(nr_entries, Entry.objects.count())

        # Set a new lemma
        data_tree = set_lemma(response.lxml, "Glerbl")

        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        # The new entry now exists.
        self.assertEqual(nr_entries + 1, Entry.objects.count(),
                         "number of entries after save")
        self.assertEqual(Entry.objects.get(lemma='Glerbl').is_locked(),
                         self.foo, "new entry locked by correct user")
        self.assertEqual(len(Entry.objects.filter(lemma='Glerbl')),
                         1,
                         "number of entries with this lemma after save")

        # Save a second time.
        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        self.assertEqual(len(Entry.objects.filter(lemma='Glerbl')),
                         1, "same number of entries with this lemma")

    def test_new(self):
        """
        Tests editing a new entry.
        """
        nr_entries = Entry.objects.count()
        response = self.open_new('foo')

        # Does not create a new entry until we save.
        self.assertEqual(nr_entries, Entry.objects.count())

        # Set a new lemma
        data_tree = set_lemma(response.lxml, "Glerbl")

        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        # The new entry now exists.
        self.assertEqual(nr_entries + 1, Entry.objects.count(),
                         "number of entries after save")
        self.assertEqual(Entry.objects.get(lemma='Glerbl').is_locked(),
                         self.foo, "new entry locked by correct user")

    def test_new_without_permissions(self):
        response = self.app.get(reverse("lexicography_main"),
                                user=self.noperm)
        url = reverse('lexicography_entry_new')
        self.assertNotIn(url, response,
                         "the url for creating new articles should not "
                         "be present")

    def test_concurrent_edit(self):
        """
        Tests that when an article is already locked by user X and user Y
        does a search, she's not going to get an edit link but will
        get instead a notice that the article is locked.
        """
        response, entry = self.open_abcd('foo')

        response = self.search_table_search("abcd", self.foo2)

        # Check that the option is not available
        url = reverse('lexicography_entry_update', args=(entry.id, ))
        self.assertNotIn(url, response)

        # Conversely the user is told that the article is locked.
        self.assertIn("Locked by foo (Foo Bwip).", response)

    def test_lock_expires(self):
        """
        Tests that when an article is already locked by user X, and the
        lock is expirable by the time user Y does a search, she can
        edit it.
        """
        response, entry = self.open_abcd('foo')

        # Expire the lock manually
        lock = EntryLock.objects.get(entry=entry)
        lock.datetime = lock.datetime - models.LEXICOGRAPHY_LOCK_EXPIRY - \
            datetime.timedelta(seconds=1)
        lock.save()

        response = self.search_table_search("abcd", self.foo2)

        # Check that the option is available
        url = reverse('lexicography_entry_update', args=(entry.id, ))
        self.assertIn(url, response)

        # Conversely the user is told that the article is locked.
        self.assertNotIn("Locked by foo (Foo Bwip).", response)

    def test_cannot_save_after_other_user_modifies_entry(self):
        """
        Tests that when an article is locked by user X, and user Y opens
        it successfully because the lock has expired and saves a
        modified version, then X's next attempt at saving will fail.
        """
        response1, entry1 = self.open_abcd('foo')

        # Expire the lock manually
        lock = EntryLock.objects.get(entry=entry1)
        lock.datetime = lock.datetime - models.LEXICOGRAPHY_LOCK_EXPIRY - \
            datetime.timedelta(seconds=1)
        lock.save()
        initial_etag = entry1.latest.etag

        # The 2nd user opens the article.
        response2, entry2 = self.open_abcd('foo2')
        self.assertEqual(entry2.is_locked(),
                         self.foo2, "new entry locked by correct user")

        # The 2nd user edits the article and saves.
        data_tree = set_lemma(response2.lxml, "Glerbl")
        messages, _ = self.save(
            response2, "foo2", test_util.stringify_etree(data_tree))
        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)
        # The etags should have changed with the new save.
        self.assertNotEqual(initial_etag,
                            Entry.objects.get(id=entry2.id).latest.etag)

        # The 2nd user closes the article.
        self.close(response2, entry2, "foo2")

        # The first user tries to save. Which should fail because
        # their version of the file misses the changes made by the 2nd
        # user.
        response3 = self.save(response1, "foo", expect_errors=True)
        self.assertEqual(response3.status_code, 412,
                         "the save should have failed")

    def test_direct_concurrent_edit(self):
        """
        Tests that when an article is already locked by X and Y somehow
        directly goes to the edit page (maybe due to browser history)
        for this entry, she's going to get a message that the entry is
        locked.
        """
        response, entry = self.open_abcd('foo')

        url = reverse('lexicography_entry_update', args=(entry.id, ))
        response = self.app.get(url, user='foo2')
        self.assertIn("The abcd entry is locked by foo (Foo Bwip).", response)

    def test_save_with_stale_link(self):
        """
        Tests an unlikely situation if somehow someone has a stale link
        id. This could also happen due to hacking. In this case, the entry is
        locked already.
        """
        response, entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=entry).count()
        nr_chunks = Chunk.objects.all().count()

        messages, _ = self.save(response, "foo2")

        self.assertEqual(len(messages), 1)
        self.assertIn("save_transient_error", messages)
        self.assertEqual(len(messages["save_transient_error"]), 1)
        self.assertEqual(messages["save_transient_error"][0]["msg"],
                         "The entry is locked by user foo.")
        # Check that no new data was recorded
        self.assertEqual(ChangeRecord.objects.filter(entry=entry).count(),
                         nr_changes,
                         "no change to the entry")

        self.assertEqual(nr_chunks, Chunk.objects.all().count())

    def test_save_with_invalid_handle(self):
        """
        Tests an unlikely situation if somehow someone has a stale handle
        id. This could also happen due to hacking.  A fatal error is
        issued and nothing is saved.
        """
        response, entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=entry).count()
        nr_chunks = Chunk.objects.all().count()

        response.form["saveurl"].value = reverse("lexicography_handle_save",
                                                 args=("h:9999", ))
        messages, _ = self.save(response, "foo2")

        self.assertEqual(len(messages), 1)
        self.assertIn("save_fatal_error", messages)
        # Check that no new data was recorded
        self.assertEqual(ChangeRecord.objects.filter(entry=entry).count(),
                         nr_changes,
                         "no change to the entry")

        self.assertEqual(nr_chunks, Chunk.objects.all().count())

    def test_save_not_logged_in(self):
        """
        Tests someone trying to save while not logged in.
        """
        response, entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=entry).count()
        nr_chunks = Chunk.objects.all().count()

        # The rigmarole with renew_app and csrftoken is so that we can
        # simulate that the user has logged out. renew_app makes it so
        # that the next request is not with a logged in 'foo'
        # user. The csrftoken manipulation is so that we pass the
        # csrftoken check.
        csrftoken = self.app.cookies[settings.CSRF_COOKIE_NAME]
        self.renew_app()
        self.app.set_cookie(settings.CSRF_COOKIE_NAME, csrftoken)
        messages, _ = self.save(response, None)

        self.assertEqual(len(messages), 1)
        self.assertIn("save_transient_error", messages)
        self.assertEqual(messages["save_transient_error"][0]['msg'],
                         'Save failed because you are not logged in. '
                         'Perhaps you logged out from BTW in another tab?')
        # Check that no new data was recorded
        self.assertEqual(ChangeRecord.objects.filter(entry=entry).count(),
                         nr_changes,
                         "no change to the entry")

        self.assertEqual(nr_chunks, Chunk.objects.all().count())

    def test_recover(self):
        """
        Tests that upon recovery the data is saved.
        """
        response, old_entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=old_entry).count()

        messages, data = self.save(response, "foo", command="recover")

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        self.assertEqual(ChangeRecord.objects.filter(entry=old_entry).count(),
                         nr_changes + 1,
                         "there is one and only one additional record change")

        # Check that we recorded the right thing.
        entry = Entry.objects.get(pk=old_entry.pk)
        self.assertEqual(entry.latest.user, self.foo)
        # The delay used here is arbitrary
        self.assertTrue(util.utcnow() -
                        entry.latest.datetime <= datetime.timedelta(minutes=1))
        self.assertEqual(entry.latest.session, self.app.session.session_key)
        self.assertEqual(entry.latest.ctype, ChangeRecord.UPDATE)
        self.assertEqual(entry.latest.csubtype, ChangeRecord.RECOVERY)

        # Check the chunk
        self.assertEqual(entry.latest.c_hash.data, data)
        self.assertTrue(entry.latest.c_hash.is_normal)

        self.assertNotEqual(old_entry.latest.pk, entry.latest.pk)

    def test_autosave(self):
        """
        Tests that upon autosave the data is saved.
        """
        response, old_entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=old_entry).count()

        messages, data = self.save(response, "foo", command="autosave")

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        self.assertEqual(ChangeRecord.objects.filter(entry=old_entry).count(),
                         nr_changes + 1,
                         "there is one and only one additional record change")

        # Check that we recorded the right thing.
        entry = Entry.objects.get(pk=old_entry.pk)
        self.assertEqual(entry.latest.user, self.foo)
        # The delay used here is arbitrary
        self.assertTrue(util.utcnow() -
                        entry.latest.datetime <= datetime.timedelta(minutes=1))
        self.assertEqual(entry.latest.session, self.app.session.session_key)
        self.assertEqual(entry.latest.ctype, ChangeRecord.UPDATE)
        self.assertEqual(entry.latest.csubtype, ChangeRecord.AUTOMATIC)

        # Check the chunk
        self.assertEqual(entry.latest.c_hash.data, data)
        self.assertTrue(entry.latest.c_hash.is_normal)

        self.assertNotEqual(old_entry.latest.pk, entry.latest.pk)

    def test_check(self):
        """
        Tests that the check command goes through.
        """
        response, _ = self.open_abcd('foo')
        saveurl = response.form['saveurl'].value

        params = {
            "command": "check",
            "version": REQUIRED_WED_VERSION
        }

        headers = {
            'X-REQUESTED-WITH': 'XMLHttpRequest',
            'X-CSRFToken':
            response.form['csrfmiddlewaretoken'].value.encode('utf-8')
        }

        response = self.app.post(
            saveurl,
            user='foo',
            params=params,
            content_type='application/x-www-form-urlencoded; charset=UTF-8',
            headers=headers)

        messages = test_util.parse_response_to_wed(response.json)

        self.assertEqual(len(messages), 0)

    def test_edit_automatically_upgrades(self):
        """
        Editing an article that is saved using an old version of a schema
        automatically upgrades to the latest version.
        """
        entry = Entry.objects.get(lemma="abcd")

        original = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="/1" \
version="0.10">
  <btw:lemma>abcd</btw:lemma>
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
        c = Chunk(data=original, schema_version="0.10")
        c.save()
        entry.update(
            self.foo,
            "q",
            c,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)

        # We force the preparation, otherwise, we'd have to wait for the
        # automatic asynchronous task to be done.
        c.prepare("xml", True)
        self.open_abcd('foo')

        entry = Entry.objects.get(lemma="abcd")
        self.assertEqual("".join(difflib.unified_diff(
            original.splitlines(True),
            strip_xml_decl(entry.latest.c_hash.data)[1].splitlines(True))),
            """\
--- \n\
+++ \n\
@@ -1,19 +1,15 @@
 \n\
-<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" authority="/1" \
version="0.10">
+<btw:entry xmlns="http://www.tei-c.org/ns/1.0" \
xmlns:btw="http://mangalamresearch.org/ns/btw-storage" version="1.1">
   <btw:lemma>abcd</btw:lemma>
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


class CommonPublishUnpublishCases(object):

    def test_not_allowed(self):
        """
        A user who does not have the proper credentials cannot publish.
        """
        cr = ChangeRecord.objects.get(pk=1)
        response = self.app.post(reverse(self.name, args=(cr.id, )),
                                 expect_errors=True)
        self.assertEqual(response.status_code, 403)

    def perform(self, cr):
        # We need to get a token ...
        self.app.get(reverse('lexicography_main'), user=self.foo)
        headers = {
            'X-REQUESTED-WITH': 'XMLHttpRequest',
            'X-CSRFToken': self.app.cookies['csrftoken']
        }

        return self.app.post(reverse(self.name, args=(cr.id, )),
                             headers=headers,
                             user=self.foo)


class PublishTestCase(ViewsTestCase, CommonPublishUnpublishCases):

    name = "lexicography_changerecord_publish"

    def test_publish(self):
        """
        A user can publish a valid version of an article.
        """
        old_count = PublicationChange.objects.count()

        cr = ChangeRecord.objects.get(lemma="foo")
        # THIS IS A LIE, for testing purposes.
        cr.c_hash._valid = True
        cr.c_hash.save()

        response = self.perform(cr)

        self.assertTrue(ChangeRecord.objects.get(pk=cr.pk).published)
        self.assertEqual(PublicationChange.objects.count(), old_count + 1,
                         "There should be a new publication change.")
        self.assertEqual(response.text,
                         "This change record was published.")

    def test_noop(self):
        """
        A user can publish an already published version of an article.
        """
        cr = ChangeRecord.objects.get(lemma="foo")
        # THIS IS A LIE, for testing purposes.
        cr.c_hash._valid = True
        cr.c_hash.save()

        self.perform(cr)

        old_count = PublicationChange.objects.count()

        # And again
        response = self.perform(cr)
        self.assertEqual(response.text,
                         "This change record was already published.")

        self.assertEqual(PublicationChange.objects.count(), old_count,
                         "There should not be a new publication change.")

    def test_publish_fails(self):
        """
        A user cannot publish an invalid version of an article.
        """
        cr = ChangeRecord.objects.get(lemma="foo")

        # We need to get a token ...
        self.app.get(reverse('lexicography_main'), user=self.foo)
        headers = {
            'X-REQUESTED-WITH': 'XMLHttpRequest',
            'X-CSRFToken': self.app.cookies['csrftoken']
        }

        old_count = PublicationChange.objects.count()
        response = self.app.post(reverse('lexicography_changerecord_publish',
                                         args=(cr.id, )),
                                 headers=headers,
                                 user=self.foo,
                                 expect_errors=True)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.text,
                         "This change record cannot be published.")

        self.assertFalse(ChangeRecord.objects.get(pk=cr.pk).published)
        self.assertEqual(PublicationChange.objects.count(), old_count,
                         "There should not be a new publication change.")


class UnpublishTestCase(ViewsTestCase, CommonPublishUnpublishCases):
    name = "lexicography_changerecord_unpublish"

    def test_unpublish(self):
        """
        A user can unpublish an article.
        """

        cr = ChangeRecord.objects.get(lemma="foo")
        # THIS IS A LIE, for testing purposes.
        cr.c_hash._valid = True
        cr.c_hash.save()
        self.assertTrue(cr.publish(self.foo))

        old_count = PublicationChange.objects.count()
        response = self.perform(cr)

        self.assertFalse(ChangeRecord.objects.get(pk=cr.pk).published)
        self.assertEqual(PublicationChange.objects.count(), old_count + 1,
                         "There should be a new publication change.")
        self.assertEqual(response.text,
                         "This change record was unpublished.")

    def test_noop(self):
        """
        A user can publish an already published version of an article.
        """
        cr = ChangeRecord.objects.get(lemma="foo")
        # THIS IS A LIE, for testing purposes.
        cr.c_hash._valid = True
        cr.c_hash.save()
        self.assertTrue(cr.publish(self.foo))

        self.perform(cr)

        old_count = PublicationChange.objects.count()

        # And again
        response = self.perform(cr)
        self.assertEqual(response.text,
                         "This change record was already unpublished.")

        self.assertEqual(PublicationChange.objects.count(), old_count,
                         "There should not be a new publication change.")
