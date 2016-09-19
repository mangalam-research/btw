import itertools
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings

from lib.util import utcnow
from lib.cleaning import CheckerTestCaseMixin
from ..cleaning import ChangeRecordCollapser, OldVersionCleaner
from ..models import Chunk, Entry, ChangeRecord

user_model = get_user_model()

class _BaseCleanerTestCase(TestCase):
    # The total number of ChangeRecords.
    total_records = 12
    cleaner_class = None

    @classmethod
    def setUpTestData(cls):
        super(_BaseCleanerTestCase, cls).setUpTestData()
        cls.foo = user_model.objects.create_superuser(
            username="foo", email="foo@example.com", password="foo")

    def setUp(self):
        self.chunk = Chunk(data="<div/>", is_normal=True, _valid=True)
        self.chunk.save()

    def test_to_clean(self):
        """
        ``to_clean`` returns what should be cleaned.
        """
        to_clean, _to_keep = self.make_records()

        cleaner = self.cleaner_class()
        self.assertItemsEqual(cleaner.to_clean, to_clean)

    def test_run(self):
        """
        ``run`` actually cleans what needs cleaning.
        """
        to_clean, _to_keep = self.make_records()

        already_hidden_ids = set(
            obj.id for obj in ChangeRecord.objects.filter(hidden=True))

        messages = []
        cleaner = self.cleaner_class(verbose=True)

        def record(message):
            messages.append(message)
        cleaner.ee.on("message", record)
        cleaned = cleaner.run()

        # Everything that was to_clean should be hidden, and
        # everything else should not be.

        self.assertEqual(len(cleaned), len(to_clean))

        to_clean_ids = set(obj.id for obj in to_clean)

        for cr in ChangeRecord.objects.all():
            hidden = cr.hidden
            cr_id = cr.id
            if cr_id in to_clean_ids:
                self.assertTrue(hidden,
                                "ChangeRecord with id {0} should be hidden."
                                .format(cr_id))
                try:
                    messages.remove("Cleaned {0}.".format(cr))
                except ValueError:
                    raise AssertionError(
                        "the cleaning message for {0} is missing".format(cr))
            elif cr_id not in already_hidden_ids:
                # If it was not to be cleaned, then it was to be kept.
                self.assertFalse(
                    hidden,
                    "ChangeRecord with id {0} should not be hidden."
                    .format(cr_id))

                try:
                    found = next(m for m in messages
                                 if m.startswith("Kept {0}, because"
                                                 .format(cr)))
                except StopIteration:
                    raise AssertionError(
                        "the keeping message for {0} is missing".format(cr))
                else:
                    messages.remove(found)

        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], "Cleaned {0} of {1} record(s)."
                         .format(len(cleaned), self.total_records))

    def test_run_idempotent(self):
        """
        Running ``run`` twice in a row does not clean more records. It is
        "idempotent" in the sense that a 2nd run does not further
        modify the database.
        """
        to_clean, _to_keep = self.make_records()

        cleaner = self.cleaner_class(verbose=True)
        cleaned = cleaner.run()

        self.assertEqual(len(cleaned), len(to_clean))

        cleaner = ChangeRecordCollapser(verbose=True)

        messages = []

        def record(message):
            messages.append(message)
        cleaner.ee.on("message", record)
        cleaned = cleaner.run()
        self.assertEqual(len(cleaned), 0)

        self.assertEqual(messages[-1], "Cleaned 0 of {0} record(s)."
                         .format(self.total_records))


@override_settings(BTW_COLLAPSE_CRS_OLDER_THAN=1)
class ChangeRecordCollapserTestCase(_BaseCleanerTestCase):
    cleaner_class = ChangeRecordCollapser

    def make_records(self):
        to_clean = []
        to_keep = []

        #
        # entry1: Generic cases...
        #
        entry1 = Entry()

        # Old and unpublished...
        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        entry1.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry1.latest.save()
        # ... but not right type.
        to_keep.append(entry1.latest)

        # Old, unpublished, not of a proscribed type: will be cleaned
        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        entry1.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry1.latest.save()
        to_clean.append(entry1.latest)

        # Old, unpublished, not of a proscribed type: will be cleaned
        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry1.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry1.latest.save()
        to_clean.append(entry1.latest)

        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry1.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry1.latest.save()
        self.assertTrue(entry1.latest.publish(self.foo))

        # Published
        to_keep.append(entry1.latest)

        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        # Too recent.
        to_keep.append(entry1.latest)

        entry1 = None  # Make sure we cannot access it again.

        #
        # entry2: Make sure that we favor keeping CREATE records.
        #
        entry2 = Entry()

        # Old and unpublished...
        entry2.update(
            self.foo,
            "q",
            self.chunk,
            "foo2",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        entry2.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry2.latest.save()
        # ... but not right type.
        to_keep.append(entry2.latest)

        entry2.update(
            self.foo,
            "q",
            self.chunk,
            "foo2",
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        entry2.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry2.latest.save()
        # The CREATE record is favored.
        to_clean.append(entry2.latest)

        entry2 = None

        #
        # entry3: everything is eligible for collpasing. We elect the
        # newest record to keep. See the comments in the code of the
        # class. This should be an unusual case, but we test it here.
        #

        entry3 = Entry()
        entry3.update(
            self.foo,
            "q",
            self.chunk,
            "foo3",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        # We cannot call .update above with a type of UPDATE. The
        # system is *designed* to prevent doing so. (It prevents
        # creating a new record with ctype UPDATE! So we munge it.
        entry3.latest.ctype = ChangeRecord.UPDATE
        entry3.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry3.latest.save()
        # We clean the oldest record.
        to_clean.append(entry3.latest)

        entry3.update(
            self.foo,
            "q",
            self.chunk,
            "foo3",
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        entry3.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry3.latest.save()
        # Keep the newest.
        to_keep.append(entry3.latest)

        entry3 = None

        #
        # entry4: Already partially hidden.
        #

        entry4 = Entry()
        entry4.update(
            self.foo,
            "q",
            self.chunk,
            "foo4",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        to_keep.append(entry4.latest)

        entry4.update(
            self.foo,
            "q",
            self.chunk,
            "foo4",
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        entry4.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry4.latest.hidden = True
        entry4.latest.save()
        # This is neither to_keep nor to_clean.

        entry4.update(
            self.foo,
            "q",
            self.chunk,
            "foo4",
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        entry4.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry4.latest.save()
        to_clean.append(entry4.latest)

        return to_clean, to_keep


@override_settings(BTW_CLEAN_CRS_OLDER_THAN=1)
class OldVersionCleanerTestCase(_BaseCleanerTestCase):
    cleaner_class = OldVersionCleaner

    def make_records(self):
        to_clean = []
        to_keep = []

        #
        # entry1: Generic cases...
        #
        entry1 = Entry()

        # Old and unpublished...
        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        entry1.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry1.latest.save()
        # ... but not right type.
        to_keep.append(entry1.latest)

        # Old, unpublished, not of a proscribed type: will be cleaned
        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.UPDATE,
            ChangeRecord.RECOVERY)
        entry1.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry1.latest.save()
        to_clean.append(entry1.latest)

        # Old, unpublished, not of a proscribed type: will be cleaned
        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry1.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry1.latest.save()
        to_clean.append(entry1.latest)

        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry1.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry1.latest.save()
        self.assertTrue(entry1.latest.publish(self.foo))

        # Published, won't be cleaned
        to_keep.append(entry1.latest)

        entry1.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        # Too recent.
        to_keep.append(entry1.latest)

        entry1 = None  # Make sure we cannot access it again.

        #
        # entry3: We keep the latest record.

        entry3 = Entry()
        entry3.update(
            self.foo,
            "q",
            self.chunk,
            "foo3",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        # Keep, not right type, and too young.
        to_keep.append(entry3.latest)

        entry3.update(
            self.foo,
            "q",
            self.chunk,
            "foo3",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry3.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry3.latest.save()
        # Clean: meets all requirements and is not latest.
        to_clean.append(entry3.latest)

        entry3.update(
            self.foo,
            "q",
            self.chunk,
            "foo3",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry3.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry3.latest.save()
        # Keep the latest.
        to_keep.append(entry3.latest)

        entry3 = None

        #
        # entry4: Already partially hidden.
        #

        entry4 = Entry()
        entry4.update(
            self.foo,
            "q",
            self.chunk,
            "foo4",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        to_keep.append(entry4.latest)

        entry4.update(
            self.foo,
            "q",
            self.chunk,
            "foo4",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry4.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry4.latest.hidden = True
        entry4.latest.save()
        # This is neither to_keep nor to_clean.

        entry4.update(
            self.foo,
            "q",
            self.chunk,
            "foo4",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry4.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry4.latest.save()
        to_clean.append(entry4.latest)

        entry4.update(
            self.foo,
            "q",
            self.chunk,
            "foo4",
            ChangeRecord.UPDATE,
            ChangeRecord.AUTOMATIC)
        entry4.latest.datetime = utcnow() - datetime.timedelta(days=2)
        entry4.latest.save()
        to_keep.append(entry4.latest)

        return to_clean, to_keep

class _BaseCheckerTestCase(CheckerTestCaseMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super(_BaseCheckerTestCase, cls).setUpTestData()
        cls.foo = user_model.objects.create_superuser(
            username="foo", email="foo@example.com", password="foo")
        cls.chunk = Chunk(data="<div/>", is_normal=True, _valid=True)

    def setUp(self):
        self.entry = Entry()
        self.entry.update(
            self.foo,
            "q",
            self.chunk,
            "foo",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)

class CollapserCheckUnpublishedTestCase(_BaseCheckerTestCase):
    checker_name = "check_unpublished"
    cleaner_class = ChangeRecordCollapser

    def make_success_obj(self, cleaner):
        return self.entry.latest

    def make_failure_obj(self, cleaner):
        e = self.entry
        self.assertTrue(e.latest.publish(self.foo))
        return e.latest

@override_settings(BTW_COLLAPSE_CRS_OLDER_THAN=1)
class CollapserCheckOldEnoughTestCase(_BaseCheckerTestCase):
    checker_name = "check_old_enough"
    cleaner_class = ChangeRecordCollapser

    def make_failure_obj(self, cleaner):
        return self.entry.latest

    def make_success_obj(self, cleaner):
        e = self.entry
        e.latest.datetime = utcnow() - datetime.timedelta(days=2)
        return e.latest

class CollapserCheckCanBeCleanedTestCase(_BaseCheckerTestCase):
    checker_name = "check_can_be_cleaned"
    cleaner_class = ChangeRecordCollapser

    def make_success_obj(self, cleaner):
        return self.entry.latest

    def make_failure_obj(self, cleaner):
        e = self.entry
        cleaner._to_keep.add(e.latest.id)
        return e.latest

class CollapserCheckRightTypeTestCase(_BaseCheckerTestCase):
    checker_name = "check_right_type"
    cleaner_class = ChangeRecordCollapser

    def make_failure_obj(self, cleaner):
        return self.entry.latest

    def make_success_obj(self, cleaner):
        e = self.entry
        e.latest.ctype = ChangeRecord.UPDATE
        return e.latest

    def test_systematic_success_check(self):
        """
        Test that we get the check results we expect for all types and
        subtypes.
        """

        cleaner = self.make_cleaner()
        checker = self.get_checker(cleaner)
        for ctype, csubtype in itertools.product(ChangeRecord.TYPE_CHOICES,
                                                 ChangeRecord.SUBTYPE_CHOICES):
            expect = ctype != ChangeRecord.CREATE
            cr = self.entry.latest
            cr.ctype = ctype
            cr.csubtype = csubtype
            self.assertEqual(checker(cr), expect)

class CleanerCheckUnpublishedTestCase(_BaseCheckerTestCase):
    checker_name = "check_unpublished"
    cleaner_class = OldVersionCleaner

    def make_success_obj(self, cleaner):
        return self.entry.latest

    def make_failure_obj(self, cleaner):
        e = self.entry
        self.assertTrue(e.latest.publish(self.foo))
        return e.latest

@override_settings(BTW_CLEAN_CRS_OLDER_THAN=1)
class CleanerCheckOldEnoughTestCase(_BaseCheckerTestCase):
    checker_name = "check_old_enough"
    cleaner_class = OldVersionCleaner

    def make_failure_obj(self, cleaner):
        return self.entry.latest

    def make_success_obj(self, cleaner):
        e = self.entry
        e.latest.datetime = utcnow() - datetime.timedelta(days=2)
        return e.latest

class CleanerCheckNotLatestTestCase(_BaseCheckerTestCase):
    checker_name = "check_not_latest"
    cleaner_class = OldVersionCleaner

    def make_failure_obj(self, cleaner):
        return self.entry.latest

    def make_success_obj(self, cleaner):
        e = self.entry
        ret = e.latest
        # The record we obtained is no longer the "latest".
        e.update(self.foo,
                 "q",
                 self.chunk,
                 "foo",
                 ChangeRecord.UPDATE,
                 ChangeRecord.MANUAL)
        return ret

class CleanerCheckRightTypeTestCase(_BaseCheckerTestCase):
    checker_name = "check_right_type"
    cleaner_class = OldVersionCleaner

    def make_failure_obj(self, cleaner):
        return self.entry.latest

    def make_success_obj(self, cleaner):
        e = self.entry
        e.latest.ctype = ChangeRecord.UPDATE
        e.latest.csubtype = ChangeRecord.AUTOMATIC
        return e.latest

    def test_systematic_success_check(self):
        """
        Test that we get the check results we expect for all types and
        subtypes.
        """

        cleaner = self.make_cleaner()
        checker = self.get_checker(cleaner)
        for ctype, csubtype in itertools.product(ChangeRecord.TYPE_CHOICES,
                                                 ChangeRecord.SUBTYPE_CHOICES):
            expect = csubtype == ChangeRecord.RECOVERY or \
                (csubtype == ChangeRecord.AUTOMATIC and
                 ctype == ChangeRecord.UPDATE)
            cr = self.entry.latest
            cr.ctype = ctype
            cr.csubtype = csubtype
            self.assertEqual(checker(cr), expect)
