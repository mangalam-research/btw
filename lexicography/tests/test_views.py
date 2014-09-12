from django_webtest import TransactionWebTest
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
import cookielib as http_cookiejar

import os
import datetime

import requests
import lxml.etree

from .. import models
from ..models import Entry, EntryLock, ChangeRecord, ChangeInfo, Chunk
from ..views import REQUIRED_WED_VERSION
from . import util as test_util
import lib.util as util

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json"))

server_name = "http://localhost:80"
user_model = get_user_model()


def set_lemma(tree, new_lemma):
    return test_util.set_lemma(tree.xpath("//*[@id='id_data']")[0].text,
                               new_lemma)


class ViewsTestCase(TransactionWebTest):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")
        self.noperm = user_model.objects.get(username="noperm")

    def assertSameDBRecord(self, a, b):
        self.assertEqual(type(a), type(b))
        self.assertEqual(a.pk, b.pk)

    def search_table_search(self, title, user):
        return self.app.get(reverse("lexicography_search_table"),
                            params={
                                "sEcho": 1,
                                "iColumns": 1,
                                "iDisplayStart": 0,
                                "iDisplayLength": -1,
                                "mDataProp_0": 0,
                                "bSearchable_0": "true",
                                "bSortable_0": "true",
                                "sSearch": "abcd",
                                "bRegex": "false",
                                "iSortCol_0": 0,
                                "sSortDir_0": "asc",
                                "iSortingCols": 1,
                                "bHeadwordsOnly": "true"},
                            user=user)

    def test_main(self):
        """
        Tests that a logged in user can view the main page.
        """
        self.app.get(reverse("lexicography_main"), user=self.foo)

    def test_search_table(self):
        """
        Tests that the search table ajax calls can go through for a logged
        in user.
        """
        self.search_table_search("abcd", self.foo)

    def open_abcd(self, user):
        #
        # User opens for editing the entry with headword "abcd".
        #
        # Returns the response which has the editing page and the entry
        # object that the user is editing.
        #
        headword = 'abcd'
        response = self.app.get(reverse("lexicography_search"),
                                params={"q": headword},
                                user=user)
        data = response.json
        self.assertEqual(
            Entry.objects.filter(headword=headword).count(),
            len(data))
        response = self.app.get(data[headword]["edit_url"]).follow()
        # Check that a lock as been acquired.
        entry = Entry.objects.get(id=data[headword]["id"])
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

        headers = {
            'X-REQUESTED-WITH': 'XMLHttpRequest',
            'X-CSRFToken':
            response.form['csrfmiddlewaretoken'].value.encode('utf-8'),
            'If-Match': response.form['initial_etag'].value.encode('utf-8'),
        }

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
        response, entry = self.open_abcd('foo')

        nr_changes = ChangeRecord.objects.filter(entry=entry).count()
        nr_chunks = Chunk.objects.all().count()

        # There is a foo entry already
        data_tree = set_lemma(response.lxml, "foo")

        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

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

        # Set a new lemma
        data_tree = set_lemma(response.lxml, "Glerbl")

        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

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
        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

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

        # Set a new lemma
        data_tree = set_lemma(response.lxml, "Glerbl")

        messages, _ = self.save(
            response, "foo", test_util.stringify_etree(data_tree))

        self.assertEqual(len(messages), 1)
        self.assertIn("save_successful", messages)

        # The new entry now exists.
        self.assertEqual(nr_entries + 1, Entry.objects.count(),
                         "number of entries after save")
        self.assertEqual(Entry.objects.get(headword='Glerbl').is_locked(),
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
        Tests that when an article is already locked by X and Y does a
        search, she's not going to get an edit link.
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
        csrftoken = self.app.cookies['csrftoken']
        self.renew_app()
        cookie = http_cookiejar.Cookie(
            version=0,
            name='csrftoken',
            value=csrftoken,
            port=None,
            port_specified=False,
            domain='.localhost',
            domain_specified=True,
            domain_initial_dot=False,
            path='/',
            path_specified=True,
            secure=False,
            expires=None,
            discard=False,
            comment=None,
            comment_url=None,
            rest=None
        )
        self.app.cookiejar.set_cookie(cookie)
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
        self.assertEqual(entry.user, self.foo)
        # The delay used here is arbitrary
        self.assertTrue(util.utcnow() -
                        entry.datetime <= datetime.timedelta(minutes=1))
        self.assertEqual(entry.session, self.app.session.session_key)
        self.assertEqual(entry.ctype, entry.UPDATE)
        self.assertEqual(entry.csubtype, entry.AUTOMATIC)

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
