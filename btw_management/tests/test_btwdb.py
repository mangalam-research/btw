import tempfile
import os

from django.test import TestCase

from .util import Caller, call_command

tmpdir = None
old_btw_env_suppress_message = None

def setUpModule():
    # pylint: disable=global-statement
    global tmpdir
    global old_btw_env_suppress_message

    tmpdir = tempfile.mkdtemp(prefix="btw-test-btwdb")
    old_btw_env_suppress_message = os.environ.get("BTW_ENV_SUPPRESS_MESSAGE")
    os.environ["BTW_ENV_SUPPRESS_MESSAGE"] = "1"

def tearDownModule():
    if old_btw_env_suppress_message:
        os.environ["BTW_ENV_SUPPRESS_MESSAGE"] = old_btw_env_suppress_message

class BTWDBTestCase(TestCase):

    def assertNoOutput(self, c):
        self.assertTrue(c.called)
        self.assertEqual(c.stdout, "")
        self.assertEqual(c.stderr, "")

class CollapseChangeRecordsTestCase(BTWDBTestCase):

    def test_no_output_if_not_verbose(self):
        c = Caller()
        c.call_command("btwdb", "collapse_change_records")
        self.assertNoOutput(c)

    def test_output_if_verbose(self):
        c = Caller()
        c.call_command("btwdb", "collapse_change_records", verbosity=2)
        self.assertEqual(c.stdout, "Cleaned 0 of 0 record(s).\n")

    def test_noop_is_passed(self):
        c = Caller()
        c.call_command("btwdb", "collapse_change_records",
                       "--noop", verbosity=2)
        self.assertEqual(c.stdout, "Would have cleaned 0 of 0 record(s).\n")

class CleanOldVersionsTestCase(BTWDBTestCase):

    def test_no_output_if_not_verbose(self):
        c = Caller()
        c.call_command("btwdb", "clean_old_versions")
        self.assertNoOutput(c)

    def test_output_if_verbose(self):
        c = Caller()
        c.call_command("btwdb", "clean_old_versions", verbosity=2)
        self.assertEqual(c.stdout, "Cleaned 0 of 0 record(s).\n")

    def test_noop_is_passed(self):
        c = Caller()
        c.call_command("btwdb", "clean_old_versions", "--noop", verbosity=2)
        self.assertEqual(c.stdout, "Would have cleaned 0 of 0 record(s).\n")
