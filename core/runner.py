from django.core.management import call_command
from django.test.testcases import TransactionTestCase, TestCase
from django_nose import NoseTestSuiteRunner
from cms.utils.permissions import set_current_user
from cms.test_utils.testcases import BaseCMSTestCase

from lib.testutil import unmonkeypatch_databases

#
# When upgrading to Django 1.10 it turned out that the problem with
# Django CMS's "current user" spread everywhere. We basically need to
# reset it between each test. Doing so where the tests are would
# require widespread changes. Instead, we monkeypatch
# TransactionTestCase so that Django CMS set_current_user(None) is
# issued before each test.
#
old_setUp = getattr(TransactionTestCase, "setUp", None)
def setUp(self):
    set_current_user(None)
    if old_setUp:
        old_setUp(self)

TransactionTestCase.setUp = setUp

# We also need to patch setUpTestData because it can be called before
# "setUp".
old_setUpTestData = getattr(TestCase, "setUpTestData", None)

@classmethod
def setUpTestData(cls):
    set_current_user(None)
    if old_setUpTestData:
        old_setUpTestData()

TestCase.setUpTestData = setUpTestData

#
# From Django CMS 3.4 or so BaseCMSTestCase acquired this method,
# which looks to nose like a test. Mark it as a non-test.
#
BaseCMSTestCase.get_permissions_test_page.__func__.__test__ = False

class Runner(NoseTestSuiteRunner):

    created_exist_db = False
    loaded_index = False

    def setup_databases(self, *args, **kwargs):
        unmonkeypatch_databases()
        ret = super(Runner, self).setup_databases(*args, **kwargs)
        # Createdb will fail if the database already exists. So we run
        # a dropdb first in case the previous run was dirty.
        call_command("btwexistdb", "dropdb")
        call_command("btwexistdb", "createdb")
        self.created_exist_db = True
        call_command("btwexistdb", "loadindex")
        self.loaded_index = True
        return ret

    def teardown_databases(self, *args, **kwargs):
        ret = super(Runner, self).teardown_databases(*args, **kwargs)

        if self.created_exist_db:
            try:
                call_command("btwexistdb", "dropdb")
            except Exception as ex:  # pylint: disable=broad-except
                print ex

        if self.loaded_index:
            try:
                call_command("btwexistdb", "dropindex")
            except Exception as ex:  # pylint: disable=broad-except
                print ex

        return ret
