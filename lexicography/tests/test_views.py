from django_webtest import TransactionWebTest
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

import lxml.etree

import os
import datetime

from ..models import Entry, EntryLock, ChangeRecord, ChangeInfo, Chunk
from ..views import REQUIRED_WED_VERSION
from . import util as test_util
import lib.util as util
from .. import xml

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json"))

server_name = "http://localhost:80"
user_model = get_user_model()


class ViewsTestCase(TransactionWebTest):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")

    def assertSameDBRecord(self, a, b):
        self.assertEqual(type(a), type(b))
        self.assertEqual(a.pk, b.pk)

    def test_main(self):
        """
        Tests that a logged in user can issue a search on the main page.
        """
        form = self.app.get(reverse("lexicography_main"), user=self.foo).form
        form['q'] = 'abcd'
        response = form.submit()
        self.assertEqual(response.context['query_string'], 'abcd')
        self.assertQuerysetEqual(
            Entry.objects.filter(headword='abcd'),
            [repr(x) for x in response.context['found_entries']])

    def open_abcd(self, user):
        #
        # User opens for editing the entry with headword "abcd".
        #
        # Returns the response which has the editing page and the entry
        # object that the user is editing.
        #
        form = self.app.get(reverse("lexicography_main"), user=user).form
        form['q'] = 'abcd'
        response = form.submit()
        headword = 'abcd'
        self.assertEqual(response.context['query_string'], headword)
        self.assertQuerysetEqual(
            Entry.objects.filter(headword=headword),
            [repr(x) for x in response.context['found_entries']])
        entry = Entry.objects.get(headword=headword)
        url = reverse('lexicography_entry_update', args=(entry.id, ))
        response = response.click(href=url).follow()
        # Check that a lock as been acquired.
        lock = EntryLock.objects.get(entry=entry)
        self.assertSameDBRecord(lock.entry, entry)

        # Check the logurl has a good value.
        self.assertEqual(response.form['logurl'].value,
                         reverse('lexicography_log'))
        return response, entry

    def open_new(self, user):
        #
        # User opens a new entry for editing.
        #
        # Returns the response which has the editing page.
        #
        response = self.app.get(reverse("lexicography_main"), user=user)
        url = reverse('lexicography_entry_new')
        response = response.click(href=url).follow()

        # Check the logurl has a good value.
        self.assertEqual(response.form['logurl'].value,
                         reverse('lexicography_log'))

        return response

    def save(self, response, user, data=None, recover=False):
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

        data = data or lxml.etree.tostring(
            response.lxml.xpath("//*[@id='id_data']")[0][0])

        params = {
            "command": "save" if not recover else "recover",
            "version": REQUIRED_WED_VERSION,
            "data": data
        }

        headers = {
            'X-REQUESTED-WITH': 'XMLHttpRequest',
            'X-CSRFToken':
            response.form['csrfmiddlewaretoken'].value.encode('utf-8')
        }

        response = self.app.post(
            saveurl,
            user=user,
            params=params,
            content_type='application/x-www-form-urlencoded; charset=UTF-8',
            headers=headers)

        return test_util.parse_response_to_wed(response.json), params["data"]

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
        self.assertEqual(entry.user, self.foo)
        # The delay used here is arbitrary
        self.assertTrue(util.utcnow() -
                        entry.datetime <= datetime.timedelta(minutes=1))
        self.assertEqual(entry.session, self.app.session.session_key)
        self.assertEqual(entry.ctype, entry.UPDATE)
        self.assertEqual(entry.csubtype, entry.MANUAL)

        # Check the chunk
        self.assertEqual(entry.c_hash.data, data)
        self.assertTrue(entry.c_hash.is_normal)

        # Check that the lastest ChangeRecord corresponds to the old_entry
        change = ChangeRecord.objects.filter(entry=old_entry) \
                                     .order_by('-datetime')[0]

        # pylint: disable=W0212
        for i in ChangeInfo._meta.get_all_field_names():
            self.assertEqual(getattr(old_entry, i), getattr(change, i))

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

        # The data is xhtml so convert it to xml before manipulating the tree.
        data = lxml.etree.tostring(
            response.lxml.xpath("//*[@id='id_data']")[0][0])
        data = xml.xhtml_to_xml(data)

        data_tree = lxml.etree.fromstring(data)

        # This casts a wider net than strictly necessary but it does not
        # matter.
        lemma_hits = data_tree.xpath(
            "xhtml:div[contains(@class, 'btw:lemma')]",
            namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})

        for lemma in lemma_hits:
            lemma.getparent().remove(lemma)

        messages, _ = self.save(response, "foo",
                                lxml.etree.tostring(data_tree))

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
        response, entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=entry).count()
        nr_chunks = Chunk.objects.all().count()

        # The data is xhtml so convert it to xml before manipulating the tree.
        data = lxml.etree.tostring(
            response.lxml.xpath("//*[@id='id_data']")[0][0])
        data = xml.xhtml_to_xml(data)

        data_tree = lxml.etree.fromstring(data)

        # This casts a wider net than strictly necessary but it does not
        # matter.
        lemma_hits = data_tree.xpath(
            "xhtml:div[contains(@class, 'btw:lemma')]",
            namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})

        for lemma in lemma_hits:
            del lemma[:]
            lemma.text = "foo"  # There is a foo entry already.

        messages, _ = self.save(response, "foo",
                                lxml.etree.tostring(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_transient_error", messages)
        self.assertEqual(len(messages["save_transient_error"]), 1)
        self.assertEqual(messages["save_transient_error"][0]["msg"],
                         'There is another entry with the lemma "foo".')

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

        #
        # Set a lemma.
        #

        # The data is xhtml so convert it to xml before manipulating the tree.
        data = lxml.etree.tostring(
            response.lxml.xpath("//*[@id='id_data']")[0][0])
        data = xml.xhtml_to_xml(data)

        data_tree = lxml.etree.fromstring(data)

        # This casts a wider net than strictly necessary but it does not
        # matter.
        lemma_hits = data_tree.xpath(
            "xhtml:div[contains(@class, 'btw:lemma')]",
            namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})

        for lemma in lemma_hits:
            del lemma[:]
            lemma.text = "Glerbl"

        messages, _ = self.save(response, "foo",
                                lxml.etree.tostring(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        # The new entry now exists.
        self.assertEqual(nr_entries + 1, Entry.objects.count(),
                         "number of entries after save")
        self.assertEqual(Entry.objects.get(headword='Glerbl').is_locked(),
                         self.foo, "new entry locked by correct user")
        self.assertEqual(len(Entry.objects.filter(headword='Glerbl')),
                         1,
                         "number of entries with this headword after save")

        # Save a second time.
        messages, _ = self.save(response, "foo",
                                lxml.etree.tostring(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        self.assertEqual(len(Entry.objects.filter(headword='Glerbl')),
                         1, "same number of entries with this headword")

    def test_new(self):
        """
        Tests editing a new entry.
        """
        nr_entries = Entry.objects.count()
        response = self.open_new('foo')

        # Does not create a new entry until we save.
        self.assertEqual(nr_entries, Entry.objects.count())

        #
        # Set a lemma.
        #

        # The data is xhtml so convert it to xml before manipulating the tree.
        data = lxml.etree.tostring(
            response.lxml.xpath("//*[@id='id_data']")[0][0])
        data = xml.xhtml_to_xml(data)

        data_tree = lxml.etree.fromstring(data)

        # This casts a wider net than strictly necessary but it does not
        # matter.
        lemma_hits = data_tree.xpath(
            "xhtml:div[contains(@class, 'btw:lemma')]",
            namespaces={'xhtml': 'http://www.w3.org/1999/xhtml'})

        for lemma in lemma_hits:
            del lemma[:]
            lemma.text = "Glerbl"

        messages, _ = self.save(response, "foo",
                                lxml.etree.tostring(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        # The new entry now exists.
        self.assertEqual(nr_entries + 1, Entry.objects.count(),
                         "number of entries after save")
        self.assertEqual(Entry.objects.get(headword='Glerbl').is_locked(),
                         self.foo, "new entry locked by correct user")

    def test_concurrent_edit(self):
        """
        Tests that when an article is already locked by X and Y does a
        search, she's not going to get an edit link.
        """
        response, entry = self.open_abcd('foo')

        form = self.app.get(reverse("lexicography_main"), user="foo2").form
        form['q'] = 'abcd'
        response = form.submit(user="foo2")

        # Check that the option is not available
        url = reverse('lexicography_entry_update', args=(entry.id, ))
        self.assertNotIn(url, response)

        # Conversely the user is told that the article is locked.
        self.assertIn("Locked by foo (Foo Bwip).", response)

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

    def test_recover(self):
        """
        Tests that upon recovery the data is saved.
        """
        response, old_entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=old_entry).count()

        messages, data = self.save(response, "foo", recover=True)

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        self.assertEqual(ChangeRecord.objects.filter(entry=old_entry).count(),
                         nr_changes + 1,
                         "there is one and only one additional record change")

        # Check that we recorded the right thing.
        entry = Entry.objects.get(pk=old_entry.pk)
        self.assertEqual(entry.user, self.foo)
        # The delay used here is arbitrary
        self.assertTrue(util.utcnow() -
                        entry.datetime <= datetime.timedelta(minutes=1))
        self.assertEqual(entry.session, self.app.session.session_key)
        self.assertEqual(entry.ctype, entry.UPDATE)
        self.assertEqual(entry.csubtype, entry.RECOVERY)

        # Check the chunk
        self.assertEqual(entry.c_hash.data, data)
        self.assertTrue(entry.c_hash.is_normal)

        # Check that the lastest ChangeRecord corresponds to the old_entry
        change = ChangeRecord.objects.filter(entry=old_entry) \
                                     .order_by('-datetime')[0]

        # pylint: disable=W0212
        for i in ChangeInfo._meta.get_all_field_names():
            self.assertEqual(getattr(old_entry, i), getattr(change, i))

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
