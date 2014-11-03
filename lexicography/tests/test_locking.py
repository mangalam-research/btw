from django.test import TestCase
from django.contrib.auth import get_user_model

import os
import time
import logging
import datetime

from .. import locking
from .. import models
from . import util

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "locking.json"))


class LockingTestCase(TestCase):
    fixtures = ["initial_data.json"] + local_fixtures

    def setUp(self):
        self.logger = logging.getLogger('lexicography.locking')
        self.stream, self.handler = util.setup_logger_for_StringIO(self.logger)

        user_model = get_user_model()
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")
        self.entry_abcd = models.Entry.objects.get(lemma="abcd")
        self.entry_foo = models.Entry.objects.get(lemma="foo")

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def assertLogRegexp(self, regexp):
        self.handler.flush()
        self.assertRegexpMatches(self.stream.getvalue(), regexp)
        self.stream.truncate(0)

    def flush_log(self):
        self.handler.flush()
        self.stream.truncate(0)

    def test_try_acquiring_lock_success(self):
        lock = locking.try_acquiring_lock(self.entry_abcd, self.foo)
        self.assertIsNotNone(lock)
        self.assertLogRegexp(
            r"^foo acquired lock \d+ on entry \d+ \(lemma: abcd\)$")

    def test_try_acquiring_lock_failure(self):
        lock = locking.try_acquiring_lock(self.entry_abcd, self.foo)
        self.assertIsNotNone(lock)
        self.assertLogRegexp(
            r"^foo acquired lock \d+ on entry \d+ \(lemma: abcd\)$")

        # Foo2 tries to acquire a lock on the entry already locked by foo.
        lock = locking.try_acquiring_lock(self.entry_abcd, self.foo2)
        self.assertIsNone(lock)
        self.assertLogRegexp(
            r"^foo2 failed to expire lock \d+ on entry \d+ "
            r"\(lemma: abcd\)$")

    def test_try_acquiring_lock_on_two_entries(self):
        # Same user acquires lock on two different entries.
        lock = locking.try_acquiring_lock(self.entry_abcd, self.foo)
        self.assertIsNotNone(lock)
        lock = locking.try_acquiring_lock(self.entry_foo, self.foo)
        self.assertIsNotNone(lock)

    def test_try_acquiring_lock_two_users_two_entries(self):
        # Two users acquiring locks on two different entries. That's
        # okay.
        lock = locking.try_acquiring_lock(self.entry_abcd, self.foo)
        self.assertIsNotNone(lock)
        self.assertLogRegexp(
            r"^foo acquired lock \d+ on entry \d+ \(lemma: abcd\)$")

        lock = locking.try_acquiring_lock(self.entry_foo, self.foo2)
        self.assertIsNotNone(lock)
        self.assertLogRegexp(
            r"^foo2 acquired lock \d+ on entry \d+ \(lemma: foo\)$")

    def test_try_acquiring_lock_refreshes(self):
        # A user acquires a lock on an entry already locked by this user.
        first = locking.try_acquiring_lock(self.entry_abcd, self.foo)
        self.assertIsNotNone(first)
        self.assertLogRegexp(
            r"^foo acquired lock \d+ on entry \d+ \(lemma: abcd\)$")
        time.sleep(1)
        second = locking.try_acquiring_lock(self.entry_abcd, self.foo)
        self.assertIsNotNone(second)
        self.assertTrue(second.datetime > first.datetime)
        self.assertLogRegexp(
            r"^foo refreshed lock \d+ on entry \d+ \(lemma: abcd\)$")

    def test_release_entry_lock_releases(self):
        # We do this to prevent the lock id and the entry id from
        # being in lockstep.
        first = locking.try_acquiring_lock(self.entry_abcd, self.foo)
        self.assertIsNotNone(first)
        self.flush_log()

        acquired_lock = locking.try_acquiring_lock(self.entry_foo,
                                                   self.foo)
        self.assertIsNotNone(acquired_lock)
        self.assertLogRegexp(
            r"^foo acquired lock \d+ on entry \d+ \(lemma: foo\)$")

        lock = locking.try_acquiring_lock(self.entry_foo, self.foo2)
        self.assertIsNone(lock)
        self.assertLogRegexp(
            r"^foo2 failed to expire lock \d+ on entry \d+ "
            r"\(lemma: foo\)$")

        locking.release_entry_lock(self.entry_foo, self.foo)
        self.assertLogRegexp(
            r"^foo released lock \d+ on entry \d+ \(lemma: foo\)$")
        self.assertEqual(
            models.EntryLock.objects.filter(id=acquired_lock.id).count(),
            0)

        # This will work because the lock was released
        lock = locking.try_acquiring_lock(self.entry_foo, self.foo2)
        self.assertIsNotNone(lock)
        self.assertLogRegexp(
            r"^foo2 acquired lock \d+ on entry \d+ \(lemma: foo\)$")

    def test_try_acquiring_lock_expire_success(self):
        lock = locking.try_acquiring_lock(self.entry_abcd, self.foo)
        self.assertIsNotNone(lock)
        self.assertLogRegexp(
            r"^foo acquired lock \d+ on entry \d+ \(lemma: abcd\)$")
        lock.datetime = lock.datetime - models.LEXICOGRAPHY_LOCK_EXPIRY - \
            datetime.timedelta(seconds=1)
        lock.save()

        # Foo2 tries to acquire a lock on the entry already locked by foo
        # and expires it
        lock = locking.try_acquiring_lock(self.entry_abcd, self.foo2)
        self.assertIsNotNone(lock)
        self.assertLogRegexp(
            r"^foo2 expired lock \d+ on entry \d+ \(lemma: abcd\)\n"
            r"foo2 acquired lock \d+ on entry \d+ \(lemma: abcd\)$")

    def test_release_entry_lock_fails_on_wrong_user(self):
        acquired_lock = locking.try_acquiring_lock(self.entry_abcd,
                                                   self.foo)
        self.assertIsNotNone(acquired_lock)
        self.assertLogRegexp(
            r"^foo acquired lock \d+ on entry \d+ \(lemma: abcd\)$")

        self.assertRaisesRegexp(
            ValueError,
            "the user releasing the lock is not the one who owns it",
            locking.release_entry_lock,
            self.entry_abcd, self.foo2)

    def test_release_entry_lock_fails_if_not_locked(self):
        self.assertRaisesRegexp(
            models.EntryLock.DoesNotExist,
            "EntryLock matching query does not exist.",
            locking.release_entry_lock,
            self.entry_abcd, self.foo2)
