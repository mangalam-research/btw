import os
import datetime

from django.test import TransactionTestCase
from django.contrib.auth import get_user_model


from ..models import Entry, ChangeRecord, PublicationChange
from .. import locking
import lib.util as util

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json"))

user_model = get_user_model()

# Disable warnings about accessing protected members.
# pylint: disable=W0212


class EntryTestCase(TransactionTestCase):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")
        self.entry = Entry.objects.get(id=1)

    def test_is_locked_returns_none(self):
        """
        Tests that Entry.is_locked returns None when the entry is not
        locked.
        """
        self.assertIsNone(self.entry.is_locked())

    def test_is_locked_returns_user(self):
        """
        Tests that Entry.is_locked returns the user who owns the lock.
        """
        locking.try_acquiring_lock(self.entry, self.foo)
        user = self.entry.is_locked()
        self.assertEqual(user.id, self.foo.id)

    def test_is_locked_expired(self):
        """
        Tests that Entry.is_locked returns None on an expired lock.
        """
        lock = locking.try_acquiring_lock(self.entry, self.foo)
        lock._force_expiry()
        self.assertIsNone(self.entry.is_locked())

    def test_is_editable_by_no_lock(self):
        """
        Tests that Entry.is_editable_by(X) returns True when there is no lock.
        """
        self.assertTrue(self.entry.is_editable_by(self.foo))

    def test_is_editable_by_superuser(self):
        """
        Tests that Entry.is_editable_by(X) returns True when X is a superuser.
        """
        newuser = user_model()
        newuser.username = "super"
        newuser.is_superuser = True
        newuser.save()
        self.assertTrue(self.entry.is_editable_by(newuser))

    def test_is_editable_non_author(self):
        """
        Tests that Entry.is_editable_by(X) returns False when the user
        does not have the right permissions.
        """
        newuser = user_model()
        newuser.username = "new"
        newuser.save()
        self.assertFalse(self.entry.is_editable_by(newuser))

    def test_is_editable_by_locked_by_same(self):
        """
        Tests that Entry.is_editable_by(X) returns True when locked by X.
        """
        locking.try_acquiring_lock(self.entry, self.foo)
        self.assertTrue(self.entry.is_editable_by(self.foo))

    def test_is_editable_by_locked_by_other_but_expired(self):
        """
        Tests that Entry.is_editable_by(X) returns True when locked by Y
        but the lock is expired.
        """
        lock = locking.try_acquiring_lock(self.entry, self.foo)
        lock._force_expiry()
        self.assertTrue(self.entry.is_editable_by(self.foo2))

    def test_is_editable_by_locked_by_other(self):
        """
        Tests that Entry.is_editable_by(X) returns False when locked by Y.
        """
        locking.try_acquiring_lock(self.entry, self.foo)
        self.assertFalse(self.entry.is_editable_by(self.foo2))

    def test_active_entries(self):
        """
        """
        original_count = Entry.objects.active_entries().count()
        # We change one record to be deleted. This is not how it
        # happens in the real application but for our purpose here
        # this is fine.
        self.entry.latest.ctype = ChangeRecord.DELETE
        self.entry.latest.save()
        self.assertEqual(Entry.objects.active_entries().count(),
                         original_count - 1)

    def test_update(self):
        """
        The update method creates a new ChangeRecord.
        """
        entry = self.entry
        original_change_record_count = entry.changerecord_set.count()
        old_latest = entry.latest
        entry.update(
            self.foo,
            "q",
            old_latest.c_hash,
            entry.headword,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        self.assertEqual(entry.changerecord_set.count(),
                         original_change_record_count + 1,
                         "There should be one additional change record.")
        latest = entry.latest
        self.assertEqual(latest.entry, entry)
        self.assertEqual(latest.user, self.foo)
        self.assertEqual(latest.session, "q")
        self.assertEqual(latest.c_hash, old_latest.c_hash)
        self.assertEqual(latest.headword, old_latest.headword)
        self.assertEqual(latest.ctype, ChangeRecord.UPDATE)
        self.assertEqual(latest.csubtype, ChangeRecord.MANUAL)
        self.assertFalse(latest.published)
        self.assertNotEqual(latest, old_latest)

    def test_update_on_new_entry(self):
        entry = Entry()
        self.assertEqual(entry.changerecord_set.count(), 0,
                         "There should not be any change records yet.")
        entry.update(
            self.foo,
            "q",
            self.entry.latest.c_hash,
            self.entry.headword + " copy",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        self.assertEqual(entry.changerecord_set.count(), 1,
                         "There should be one additional change record.")
        latest = entry.latest
        self.assertEqual(latest.entry, entry)
        self.assertEqual(latest.user, self.foo)
        self.assertEqual(latest.session, "q")
        self.assertEqual(latest.c_hash, self.entry.latest.c_hash)
        self.assertEqual(latest.headword, entry.headword)
        self.assertEqual(latest.ctype, ChangeRecord.CREATE)
        self.assertEqual(latest.csubtype, ChangeRecord.MANUAL)
        self.assertFalse(latest.published)


class ChangeRecordTestCase(TransactionTestCase):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")
        self.entry = Entry.objects.get(id=1)

    def test_publish_new(self):
        """
        Publishing the latest change record updates the latest_published
        field.
        """
        entry = self.entry
        old_latest = entry.latest
        entry.update(
            self.foo,
            "q",
            old_latest.c_hash,
            entry.headword,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        latest = entry.latest
        latest.publish(self.foo)
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         latest)

    def test_publish_old(self):
        """
        Publishing an old change record updates the latest_published
        field.
        """
        entry = self.entry
        old_latest = entry.latest
        entry.update(
            self.foo,
            "q",
            old_latest.c_hash,
            entry.headword,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        old_latest.publish(self.foo)
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         old_latest)

    def test_unpublish_nothing_left(self):
        """
        Unpublishing the only change that was published sets
        latest_published to None.
        """
        entry = self.entry
        latest = entry.latest
        latest.publish(self.foo)
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         latest)
        latest.unpublish(self.foo)
        self.assertIsNone(Entry.objects.get(id=entry.id).latest_published)

    def test_unpublish_newest(self):
        """
        Unpublishing the newest published version updates latest_published to
        the previous published version.
        """
        entry = self.entry
        old_latest = entry.latest
        entry.update(
            self.foo,
            "q",
            old_latest.c_hash,
            entry.headword,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        latest = entry.latest
        old_latest.publish(self.foo)
        latest.publish(self.foo)
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         latest)
        latest.unpublish(self.foo)
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         old_latest)

    def test_publish_creates_publication_change(self):
        """
        Publishing a change record creates a new PublicationChange.
        """
        entry = self.entry
        latest = entry.latest
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        self.assertFalse(latest.published,
                         "The change record we are about to use must not be "
                         "published yet.")
        latest.publish(self.foo)
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count + 1)
        latest_pc = PublicationChange.objects.latest('datetime')
        self.assertEqual(latest_pc.changerecord, latest)
        self.assertEqual(latest_pc.ctype, PublicationChange.PUBLISH)
        self.assertEqual(latest_pc.user, self.foo)
        # The timedelta is arbitrary.
        self.assertTrue(util.utcnow() -
                        latest_pc.datetime <= datetime.timedelta(seconds=5))

    def test_unpublish_creates_publication_change(self):
        """
        Unpublishing a change record creates a new PublicationChange.
        """
        entry = self.entry
        latest = entry.latest
        latest.publish(self.foo)
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        latest.unpublish(self.foo)
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count + 1)
        latest_pc = PublicationChange.objects.latest('datetime')
        self.assertEqual(latest_pc.changerecord, latest)
        self.assertEqual(latest_pc.ctype, PublicationChange.UNPUBLISH)
        self.assertEqual(latest_pc.user, self.foo)
        # The timedelta is arbitrary.
        self.assertTrue(util.utcnow() -
                        latest_pc.datetime <= datetime.timedelta(seconds=5))


class EntryLockTestCase(TransactionTestCase):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")

    def test_expirable_expired(self):
        entry = Entry.objects.get(id=1)
        lock = locking.try_acquiring_lock(entry, self.foo)
        lock._force_expiry()
        self.assertTrue(lock.expirable)
