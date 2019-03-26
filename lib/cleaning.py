import pyee
from unittest import mock

from django.db import transaction

from . import util
import collections

class Cleaner(object):
    """
    This is the base class for tools that are meant to be cleaning out
    old records created by the lexicographical app.

    This class automagically considers that all attributes that begin
    with ``"check_"`` and resolve to a callable are methods designed
    to determine whether a database object should be cleaned or
    not. All such methods will be called with the parameters ``obj,
    verbose`` where ``obj`` is the object to check and ``verbose`` is
    whether to emit a message indicating why the object is to be
    kept. If and only if the check fails, and the :attr:``verbose``
    attribute on the ``Cleaner`` instance is ``True`` and the
    ``verbose`` parameter passed to the check is also ``True``, then a
    message must be emitted. The checker must return ``True`` if the
    object passes the check and ``False`` if it fails the check.

    This class will automatically call each check before cleaning an
    object. This is a last-resort safety net used for cases where
    algorithms that select the objects to be cleaned may select
    wrongly.

    :param noop: When true, nothing is cleaned from the database.

    :param verbose: When true, explain the actions taken. Specificaly,
                    instances of this class must report what records
                    they clean and when a record is kept, why it is
                    kept.
    """

    def __init__(self, noop=False, verbose=False):
        self.noop = noop
        self.verbose = verbose
        self._now = None
        self._ee = pyee.EventEmitter()
        self._checks = None

    @property
    def now(self):
        """
        This is the date recorded as a UTC value. The first access is
        cached. So all accesses to this property on a given instance
        will provide the same value.

        This is a convenience feature. Often we do not want to clean
        records that are "too young".

        :rtype: :class:`datetime.datetime`
        """
        if self._now is None:
            self._now = util.utcnow()
        return self._now

    @property
    def ee(self):
        """
        The event emitter for this object. Clients that want to know why
        certain records are kept or cleaned should listen to ``"message"``
        events on this emitter.

        :rtype: :class:`pyee.EventEmitter`
        """
        return self._ee

    @property
    def to_clean(self):
        """
        The set of records to clean.

        Accesses to this property are not cached by default but the
        default implementation of this class accesses it only once per
        `run` call.

        :returns: A value that can be iterated.
        """
        return []

    @property
    def no_listeners(self):
        """
        Whether or not there are listeners.

        :rtype: :class:`bool`
        """
        return len(self.ee.listeners("message")) == 0

    @property
    def total_count(self):
        """
        The total number of records from which we are cleaning
        data. Derived classes must implement this.

        :rtype: :class:`int`
        """
        raise NotImplementedError

    @property
    def checks(self):
        """
        The entire set of checks defined for this instance. For every
        attribute of this instance that has a name that begins with
        ``"check_"`` and has a value which is a callable, the value is
        deemed to be a "check".

        :returns: An iterator that iterates over the checks.
        """
        matching = (getattr(self, name) for name in dir(self)
                    if name.startswith("check_"))
        return (method for method in matching if
                isinstance(method, collections.Callable))

    @transaction.atomic
    def run(self):
        """
        Execute the cleanup operation to be performed by this
        instance. This will iterate over the values of
        :meth:`to_clean`, and clean them one by one if :attr:`noop`
        is ``False``.

        :returns: The records that were cleaned.
        """
        to_clean = self.to_clean
        for obj in to_clean:
            if self.verbose:
                self.emit_clean(obj)

            if not self.noop:
                self.clean(obj)

        if self.verbose:
            self.emit_message(("Would have cleaned" if self.noop else
                               "Cleaned") + " {0} of {1} record(s)."
                              .format(len(to_clean), self.total_count))

        return to_clean

    def assert_object_before_cleaning(self, obj):
        """
        Assert that the object passes all the checks defined on this
        instance. This is done just before cleaning the object and is
        a last-resort check to make sure that we are not doing
        something wrong.

        :param obj: The object about to be cleaned.

        :raises ValueError: If no checks have been implemented. If you
                            really want no checks to be performed, you
                            should implement a single check that
                            always returns ``True``.

        :raises AssertionError: If any of the checks fail.
        """
        check = None
        for check in self.checks:
            assert check(obj, False)

        if check is None:
            raise ValueError("no checks have been implemented")

    def perform_checks(self, obj, verbose=True):
        """
        Run all the checks on the object.

        :param obj: The object to check.

        :param verbose: Whether to be verbose about the check. If
                        ``True``, then a check that fails will cause
                        the instance to emit a message on its event
                        emitter. The message explains that the object
                        failed the test and why.

        :returns: ``True`` all checks passed, ``False`` otherwise.

        :rtype: :class:`bool`
        """
        return all(check(obj, verbose) for check in self.checks)

    def clean(self, obj):
        """
        Run on the object all the checks defined by this instance. Any
        failing check causes an exception to be raised. If there is no
        failure, the object is actually cleaned by calling
        :meth:`execute_clean`.
        """
        self.assert_object_before_cleaning(obj)
        self.execute_clean(obj)

    def execute_clean(self, obj):
        """
        Perform the actual clean operation on the object. Whereas
        ``clean`` is the method that should be routinely called, this
        method is called by ``clean`` once the object has been deemed
        fine.

        Descendants must implement this method.
        """
        raise NotImplementedError

    def emit_message(self, message):
        """Emit some message on this instance's event emitter."""
        self.ee.emit("message", message)

    def emit_clean(self, obj):
        """
        Emit a message about the cleaning of an object. The message will
        say either that the object was cleaned or that it would be
        cleaned. The latter is used if the ``noop`` attribute of this
        object is true.

        :param obj: The object concerned.
        """
        if self.no_listeners:
            return

        message = ("Would clean" if self.noop else "Cleaned") + \
            " {0}.".format(obj)
        self.emit_message(message)

    def emit_keep(self, obj, reason):
        """
        Emit a message indicating that an object is to be kept. The
        message will say either that the object was kept or that it
        would be kept. The latter is used if the ``noop`` attribute of
        this object is true.

        :param obj: The object concerned.

        :param reason: The reason why the object is being kept.

        :type reason: A string or anything that ``.format`` can handle.
        """
        if self.no_listeners:
            return

        message = ("Would keep" if self.noop else "Kept") + \
            " {0}, because {1}.".format(obj, reason)
        self.emit_message(message)

class CheckerTestCaseMixin(object):
    """
    A mixin for testing ``check_`` methods on :class:`.Cleaner`
    objects.

    You can mix this mixin into a Django test case to check whether a
    checker is operating according to what ``Cleaner`` expects.
    """

    checker_name = None
    "The name of the checker to test."

    cleaner_class = None
    "This should be set to the actual class to test."

    def make_cleaner(self, *args, **kwargs):
        """
        Makes an :class:`.Cleaner` instance for testing. The arguments
        passed are passed directly to :attr:`cleaner_class`.

        :returns: The cleaner.
        """
        return self.cleaner_class(*args, **kwargs)

    def get_checker(self, cleaner):
        """
        Get the checker method on the instance passed.

        :param cleaner: The cleaner from which to get the checker.

        :returns: The checker.
        """
        return getattr(cleaner, self.checker_name)

    def make_success_obj(self, cleaner):
        """
        Make an object which pass the checker's test. This must be
        overriden in classes that use this mixin.

        :param cleaner: The cleaner that will test this object. We
                        pass this in case the cleaner's state also
                        needs adjusting.

        :returns: The object.
        """
        raise NotImplementedError

    def make_failure_obj(self, cleaner):
        """
        Make an object which fails the checker's test. This must be
        overriden in classes that use this mixin.

        :param cleaner: The cleaner that will test this object. We
                        pass this in case the cleaner's state also
                        needs adjusting.

        :returns: The object.
        """
        raise NotImplementedError

    def test_does_not_emit_on_success(self):
        """
        Test that the checker does not emit when the test is successful.
        """
        cleaner = self.make_cleaner(verbose=True)

        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        checker = self.get_checker(cleaner)
        self.assertTrue(checker(self.make_success_obj(cleaner), True))
        self.assertEqual(mocked.call_count, 0)

    def test_emits_on_failure(self):
        """
        Test that the checker emits when the test is successful (and the
        other parameters are set for emitting.)
        """
        cleaner = self.make_cleaner(verbose=True)

        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        checker = self.get_checker(cleaner)
        self.assertFalse(checker(self.make_failure_obj(cleaner), True))
        self.assertEqual(mocked.call_count, 1)

    def test_does_not_emit_on_failure_if_cleaner_not_verbose(self):
        """
        Test that the checker does not emit on a failure if the cleaner is
        not verbose.
        """
        cleaner = self.make_cleaner(verbose=False)

        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        checker = self.get_checker(cleaner)
        self.assertFalse(checker(self.make_failure_obj(cleaner), True))
        self.assertEqual(mocked.call_count, 0)

    def test_does_not_emit_on_failure_if_called_with_verbose_False(self):
        """
        Test that the checker does not emit on a failure if it was called
        with ``verbose`` set to ``False.
        """
        cleaner = self.make_cleaner(verbose=True)

        mocked = mock.MagicMock()
        cleaner.ee.on("message", mocked)
        checker = self.get_checker(cleaner)
        self.assertFalse(checker(self.make_failure_obj(cleaner), False))
        self.assertEqual(mocked.call_count, 0)
