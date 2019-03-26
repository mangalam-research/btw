import time
import datetime
from unittest import mock

from django.test import SimpleTestCase
from django.db import models

from lib.cleaning import Cleaner
from lib.util import utcnow

class FakeModel(models.Model):

    class Meta(object):
        app_label = "testing"

    val = models.IntegerField()

    def __init__(self, *args, **kwargs):
        super(FakeModel, self).__init__(*args, **kwargs)
        self._cleaned = False

class Minimal(Cleaner):

    @property
    def to_clean(self):
        return self._to_clean

    def check_foo(self, obj, verbose_):
        return True

    def execute_clean(self, obj):
        obj._cleaned = True

    @property
    def total_count(self):
        return 10

class CleanerTestCase(SimpleTestCase):

    def setUp(self):
        self.fakes = [FakeModel(val=1), FakeModel(val=2)]

    def test_now_works(self):
        """
        ``now`` evaluates to something useful and does not change once
        evaluated.
        """
        cleaner = Cleaner()
        then = cleaner.now
        time.sleep(1)

        # We can perform date arithmetics with it.
        self.assertTrue(then - utcnow() < datetime.timedelta(minutes=1))

        # It does not change.
        self.assertEqual(then, cleaner.now)

    def test_no_listeners(self):
        """
        ``no_listeners`` is ``True`` when there are no listeners, ``False``
        otherwise.
        """
        cleaner = Cleaner()
        self.assertTrue(cleaner.no_listeners)
        cleaner.ee.on("message", lambda *_: 1)
        self.assertFalse(cleaner.no_listeners)

    def test_checks_empty(self):
        """
        ``checks`` is empty by default.
        """
        cleaner = Cleaner()
        with self.assertRaises(StopIteration):
            next(cleaner.checks)

    def test_checks_returns_iterator(self):
        """
        ``checks`` returns an iterator of checks.
        """
        cleaner = Cleaner()
        cleaner.check_foo = lambda *_: 1
        cleaner.check_bar = lambda *_: 1
        checks = list(cleaner.checks)
        self.assertCountEqual(checks, [cleaner.check_bar, cleaner.check_foo])

    def test_assert_object_before_cleaning_raises_when_no_checks(self):
        """
        ``assert_object_before_cleaning`` raises when there are no checks.
        """
        cleaner = Cleaner()
        with self.assertRaisesRegex(ValueError,
                                    "no checks have been implemented"):
            cleaner.assert_object_before_cleaning({})

    def test_assert_object_before_cleaning_raises_on_failure(self):
        """
        ``assert_object_before_cleaning`` raises ``AssertionError`` when
        there is a check failure.
        """
        cleaner = Cleaner()
        cleaner.check_foo = lambda *_: False
        with self.assertRaises(AssertionError):
            cleaner.assert_object_before_cleaning({})

    def test_assert_object_before_cleaning_calls_checks(self):
        """
        ``assert_object_before_cleaning`` calls the checks
        """
        cleaner = Cleaner()
        cleaner.check_foo = mock.MagicMock()
        cleaner.check_foo.return_value = False
        obj = {}
        with self.assertRaises(AssertionError):
            cleaner.assert_object_before_cleaning(obj)
        self.assertEqual(cleaner.check_foo.call_count, 1)
        self.assertEqual(cleaner.check_foo.call_args[0], (obj, False))

    def test_run_raises_when_no_checks(self):
        """
        ``run`` raises when there are no checks.
        """
        with mock.patch('lexicography.cleaning.Cleaner.to_clean',
                        new_callable=mock.PropertyMock) as clean_mock:
            clean_mock.return_value = self.fakes
            cleaner = Cleaner()
            with self.assertRaisesRegex(ValueError,
                                        "no checks have been implemented"):
                cleaner.run()

    def test_run_calls_clean_on_objects(self):
        """
        ``run`` calls clean on objects.
        """
        cleaner = Minimal()
        cleaner._to_clean = self.fakes
        cleaner.run()
        for fake in self.fakes:
            self.assertTrue(fake._cleaned)

    def test_run_does_not_call_clean_on_objects_when_noop(self):
        """
        ``run`` does not call clean on objects when noop is ``True``.
        """
        cleaner = Minimal(noop=True)
        cleaner._to_clean = self.fakes
        cleaner.run()
        for fake in self.fakes:
            self.assertFalse(fake._cleaned)

    def test_clean_raises_when_no_checks(self):
        """
        ``clean`` raises when there are no checks.
        """
        cleaner = Cleaner()
        with self.assertRaisesRegex(ValueError,
                                    "no checks have been implemented"):
            cleaner.clean({})

    def test_clean_calls_checks(self):
        """
        ``clean`` calls the checks.
        """
        cleaner = Cleaner()
        cleaner.check_foo = mock.MagicMock()
        cleaner.check_foo.return_value = False
        obj = {}
        with self.assertRaises(AssertionError):
            cleaner.clean(obj)
        self.assertEqual(cleaner.check_foo.call_count, 1)
        self.assertEqual(cleaner.check_foo.call_args[0], (obj, False))

    def test_clean_calls_clean_on_objects(self):
        """
        ``clean`` calls clean on objects.
        """
        cleaner = Minimal()
        cleaner.clean(self.fakes[0])
        self.assertTrue(self.fakes[0]._cleaned)

    def test_perform_checks_does_not_fails_if_there_are_no_checks(self):
        """
        ``perform_checks`` does not fail if there are no checks.
        """
        cleaner = Cleaner()
        self.assertEqual(len(list(cleaner.checks)), 0)
        cleaner.perform_checks({}, True)

    def test_perform_checks_calls_the_checks(self):
        """
        ``perform_checks`` calls the checks.
        """
        cleaner = Cleaner()
        check_foo = cleaner.check_foo = mock.MagicMock()
        check_foo.return_value = True
        obj = {}
        cleaner.perform_checks(obj, True)
        self.assertEqual(check_foo.call_count, 1)
        self.assertEqual(check_foo.call_args[0], (obj, True))

        cleaner.perform_checks(obj, False)
        self.assertEqual(check_foo.call_count, 2)
        self.assertEqual(check_foo.call_args[0], (obj, False))

    def test_emit_message_emits(self):
        """
        ``emit_message`` emits a ``message`` event.
        """
        cleaner = Cleaner()
        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        cleaner.emit_message("Foo")
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(mocked.call_args[0], ("Foo", ))

    def test_emit_clean_emits(self):
        """
        ``emit_message`` emits a ``message`` event.
        """
        cleaner = Cleaner()
        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        cleaner.emit_clean("Foo")
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(mocked.call_args[0], ("Cleaned Foo.", ))

    def test_emit_keep_emits(self):
        """
        ``emit_keep`` emits a ``message`` event.
        """
        cleaner = Cleaner()
        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        cleaner.emit_keep("Foo", "reason")
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(mocked.call_args[0], ("Kept Foo, because reason.", ))

    def test_emit_clean_emits_a_different_message_when_noop_True(self):
        """
        ``emit_message`` emits a different ``message`` event when ``noop``
        is ``True``.
        """
        cleaner = Cleaner(noop=True)
        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        cleaner.emit_clean("Foo")
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(mocked.call_args[0], ("Would clean Foo.", ))

    def test_emit_keep_emits_a_different_message_when_noop_True(self):
        """
        ``emit_keep`` emits a ``message`` event when ``noop`` is ``True``.
        """
        cleaner = Cleaner(noop=True)
        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        cleaner.emit_keep("Foo", "reason")
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(mocked.call_args[0],
                         ("Would keep Foo, because reason.", ))

    def test_emit_clean_does_not_call_emit_message_if_no_listeners(self):
        """
        ``emit_clean`` does not call ``emit_message`` when there are
        no listeners.
        """
        cleaner = Cleaner()
        with mock.patch('lexicography.cleaning.Cleaner.emit_message') \
                as emit_message_mock:
            cleaner.emit_clean("Foo")
            self.assertEqual(emit_message_mock.call_count, 0)

            # Check that it is going to be called once listeners are added.
            cleaner.ee.on("message", mock.MagicMock())
            cleaner.emit_clean("Foo")
            self.assertEqual(emit_message_mock.call_count, 1)

    def test_emit_keep_does_not_call_emit_message_if_no_listeners(self):
        """
        ``emit_keep`` does not call ``emit_message`` when there are
        no listeners.
        """
        cleaner = Cleaner()
        with mock.patch('lexicography.cleaning.Cleaner.emit_message') \
                as emit_message_mock:
            cleaner.emit_keep("Foo", "reason")
            self.assertEqual(emit_message_mock.call_count, 0)

            # Check that it is going to be called once listeners are added.
            cleaner.ee.on("message", mock.MagicMock())
            cleaner.emit_keep("Foo", "reason")
            self.assertEqual(emit_message_mock.call_count, 1)

    def test_run_does_not_emit_anything_if_not_verbose(self):
        """
        If ``verbose`` is false, no messages are emitted during ``run``.
        """
        cleaner = Minimal(verbose=False)
        cleaner._to_clean = self.fakes
        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        cleaner.run()
        # Check that we actually did clean something.
        self.assertTrue(self.fakes[0]._cleaned)
        self.assertEqual(mocked.call_count, 0)

    def test_run_emits_if_verbose(self):
        """
        If ``verbose`` is true, messages are emitted during ``run``.
        """
        cleaner = Minimal(verbose=True)
        cleaner._to_clean = self.fakes
        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        cleaner.run()
        # Check that we actually did clean something.
        self.assertTrue(self.fakes[0]._cleaned)
        self.assertTrue(mocked.call_count > 0)

    def test_run_emit_a_final_summary(self):
        """
        If ``verbose`` is true, ``run`` emits a final summary that has
        correct counts.
        """
        cleaner = Minimal(verbose=True)
        cleaner._to_clean = self.fakes
        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)

        cleaner.run()
        # Check that we actually did clean something.
        self.assertTrue(self.fakes[0]._cleaned)
        self.assertTrue(mocked.call_count > 0)
        self.assertTrue(mocked.call_args[0], ("Clean 2 of 10 records(s).", ))

    def test_run_returns_cleaned_objects(self):
        """
        ``run`` returns the objects that were cleaned.
        """
        cleaner = Minimal(verbose=True)
        cleaner._to_clean = self.fakes
        self.assertCountEqual(cleaner.run(), self.fakes)
