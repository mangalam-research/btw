from django.test import TransactionTestCase
from django.contrib.auth import get_user_model

from ..models import Entry
from .. import locking

import os

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


class EntryLockTestCase(TransactionTestCase):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")

    def test_is_expirable_expired(self):
        entry = Entry.objects.get(id=1)
        lock = locking.try_acquiring_lock(entry, self.foo)
        lock._force_expiry()
        self.assertTrue(lock.is_expirable())
