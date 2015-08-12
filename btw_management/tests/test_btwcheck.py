import os
import mock
from contextlib import contextmanager

from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.contrib.sites.models import Site
from django.core.management.base import CommandError

from .util import Caller
from btw_management.management.commands import btwworker, btwredis

@contextmanager
def make_btwworker_pass():
    from btw.settings._env import env
    try:
        with mock.patch(
                "core.tasks.get_btw_env.apply_async",
                **{'return_value.get.return_value': env}), \
            mock.patch(
                "btw_management.management.commands.btwworker"
                ".get_running_workers",
                side_effect=lambda *_, **__: btwworker.get_defined_workers()), \
            mock.patch(
                "btw_management.management.commands.btwredis"
                ".get_running_workers",
                side_effect=lambda *_, **__: btwworker.get_defined_workers()), \
            mock.patch("btw_management.management.commands.btwworker"
                       ".get_full_names",
                       side_effect=lambda names:
                       {n: n + "@foo" for n in names}):

            yield
    finally:
        btwworker.flush_caches()

fake = object()

@contextmanager
def fake_pidfiles():

    class FakeWorker(btwworker.Worker):

        def __init__(self, *args, **kwargs):
            super(FakeWorker, self).__init__(*args, **kwargs)
            self.pidfile = fake

    FakeFile = mock.MagicMock(spec=file, **{'read.return_value': ["1"]})

    try:
        real_exists = os.path.exists
        with mock.patch("btw_management.management.commands.btwworker"
                        ".Worker", FakeWorker), \
            mock.patch("btw_management.management.commands.btwworker"
                       ".os.path.exists", side_effect=lambda *args, **kwargs:
                       args[0] is fake or real_exists(*args, **kwargs)), \
            mock.patch("__builtin__.open",
                       side_effect=lambda *args, **kwargs: FakeFile() if
                       args[0] is fake else open(*args, **kwargs)):
            yield
    finally:
        btwworker.flush_caches()


@override_settings(BTW_SITE_NAME="testing")
class BTWCheckTestCase(SimpleTestCase):
    maxDiff = None

    def setUp(self):
        self.site = site = Site.objects.get_current()
        site.name = "testing"
        site.save()

    def tearDown(self):
        btwworker.flush_caches()

    def test_all_ok(self):
        """
        When there is no error, everything passes.
        """
        c = Caller()
        with fake_pidfiles(), make_btwworker_pass():
            try:
                c.call_command("btwcheck")
            finally:
                self.assertEqual(c.stdout, """\
Redis instance is alive.
Checking worker testing.worker... passed
Checking worker testing.bibliography.worker... passed
""")
                self.assertEqual(c.stderr, "")

    def test_workers_fail(self):
        """
        Fails when the worker do not exist.
        """
        c = Caller()
        try:
            c.call_command("btwcheck")
        finally:
            self.assertEqual(c.stdout, """\
Redis instance is alive.
Checking worker testing.worker... failed: no pidfile
Checking worker testing.bibliography.worker... failed: no pidfile
""")
            self.assertEqual(c.stderr, "")

    def test_editors_not_set_fail(self):
        """
        Fails when BTW_EDITORS is not set.
        """
        c = Caller()
        with override_settings(BTW_EDITORS=None), fake_pidfiles(), \
                make_btwworker_pass():
            try:
                with self.assertRaisesRegexp(CommandError, r"^1 error\(s\)$"):
                    c.call_command("btwcheck")
            finally:
                self.assertEqual(c.stdout, """\
Redis instance is alive.
Checking worker testing.worker... passed
Checking worker testing.bibliography.worker... passed
""")
                self.assertEqual(
                    c.stderr, "settings.BTW_EDITORS is not set\n")

    def test_editors_not_list_fail(self):
        """
        Fails when BTW_EDITORS is not set to a list.
        """
        c = Caller()
        with override_settings(BTW_EDITORS="foo"), fake_pidfiles(), \
                make_btwworker_pass():
            try:
                with self.assertRaisesRegexp(CommandError, r"^1 error\(s\)$"):
                    c.call_command("btwcheck")
            finally:
                self.assertEqual(c.stdout, """\
Redis instance is alive.
Checking worker testing.worker... passed
Checking worker testing.bibliography.worker... passed
""")
                self.assertEqual(
                    c.stderr,
                    "settings.BTW_EDITORS is not of the right format\n")

    def test_editors_incorrect_elements(self):
        """
        Fails when BTW_EDITORS is a list that does not contain the right
        elements.
        """
        c = Caller()
        with override_settings(BTW_EDITORS=[
                "foo",
                {},
                {
                    "forename": u"foo",
                    "surname": 1,
                    "genName": u"baz",
                    "foo": "foo"
                }
        ]), fake_pidfiles(), \
                make_btwworker_pass():
            try:
                with self.assertRaisesRegexp(CommandError, r"^7 error\(s\)$"):
                    c.call_command("btwcheck")
            finally:
                self.assertEqual(c.stdout, """\
Redis instance is alive.
Checking worker testing.worker... passed
Checking worker testing.bibliography.worker... passed
""")
                self.assertEqual(
                    c.stderr,
                    """\
editor is not a dictionary: foo
missing forename in {}
missing surname in {}
missing genName in {}
field surname is not a unicode value in {'genName': u'baz', 'foo': 'foo', \
'surname': 1, 'forename': u'foo'}
spurious field foo in {'genName': u'baz', 'foo': 'foo', 'surname': 1, \
'forename': u'foo'}
settings.BTW_EDITORS is not of the right format
""")

    def test_path_does_not_exist(self):
        """
        Fails when paths are nonexistent.
        """
        c = Caller()
        with override_settings(BTW_LOGGING_PATH_FOR_BTW="@@foo@@",
                               BTW_WED_LOGGING_PATH="@@foo@@",
                               BTW_RUN_PATH_FOR_BTW="@@foo@@"), \
                fake_pidfiles(), \
                make_btwworker_pass():
            with self.assertRaisesRegexp(CommandError, r"^3 error\(s\)$"):
                c.call_command("btwcheck")
            self.assertEqual(c.stdout,
                             """\
Redis instance is alive.
Checking worker testing.worker... passed
Checking worker testing.bibliography.worker... passed
""")
            self.assertEqual(
                c.stderr,
                """\
settings.BTW_LOGGING_PATH_FOR_BTW ("@@foo@@") does not exist
settings.BTW_WED_LOGGING_PATH ("@@foo@@") does not exist
settings.BTW_RUN_PATH_FOR_BTW ("@@foo@@") does not exist
""")

    def test_bad_site(self):
        """
        Fails when the site names are not consistent
        """
        c = Caller()
        with override_settings(BTW_SITE_NAME="foo"), \
                fake_pidfiles(), \
                make_btwworker_pass():
            with self.assertRaisesRegexp(CommandError, r"^1 error\(s\)$"):
                c.call_command("btwcheck")
            self.assertEqual(c.stdout,
                             """\
Redis instance is alive.
Checking worker testing.worker... passed
Checking worker testing.bibliography.worker... passed
""")
            self.assertEqual(
                c.stderr,
                "the site name in the database (testing) is different from "
                "the BTW_SITE_NAME setting (foo)\n")
