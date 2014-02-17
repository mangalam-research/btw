import threading
import os
from unittest import TestSuite

from django.core.management.base import BaseCommand
from django.test import LiveServerTestCase
from django.test.simple import DjangoTestSuiteRunner
from south.management.commands import patch_for_test_db_setup
import mock

from bibliography.tests import mock_zotero


mock_records = mock_zotero.Records([
    {
        "itemKey": "1",
        "title": "Title 1",
        "date": "Date 1",
        "creators": [
            {"name": "Abelard (Name 1 for Title 1)"},
            {"firstName": "FirstName 2 for Title 1",
             "lastName": "LastName 2 for Title 1"},
        ]
    },
    {
        "itemKey": "2",
        "title": "Title 2",
        "date": "Date 2",
        "creators": [
            {"name": "Beth (Name 1 for Title 2)"},
            {"firstName": "FirstName 2 for Title 2",
             "lastName": "LastName 2 for Title 2"},
        ]
    }
])

# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: (mock_records.values, {}))
get_item_mock = mock.Mock(side_effect=mock_records.get_item)


class SeleniumTest(LiveServerTestCase):

    fixtures = [os.path.join("lexicography", "fixtures",
                             "initial_data.json")] + \
        list(os.path.join("lexicography", "tests", "fixtures", x)
             for x in ("users.json", "views.json"))

    def __init__(self, control, *args, **kwargs):
        self.__control = control
        super(SeleniumTest, self).__init__(*args, **kwargs)
        self.__control_thread = threading.Thread(target=self.control)
        self.__control_thread.start()

    def runTest(self):
        # This effectively causes the test to stop and wait for the
        # server to die.

        # Yep we call it this way to avoid the idiotic redefinition of
        # join present in django/test/testcases.py (present in version
        # 1.5, maybe 1.6)
        print "Starting thread!"
        threading.Thread.join(self.server_thread)

    def control(self):
        open(self.__control, 'r').read(1)
        self.server_thread.join()

    def tearDown(self):
        # The regular runner does not drop caches, so we have to do it
        # ourselves.
        from django.conf import settings
        from django.db import connection
        for setup in settings.CACHES.values():
            if setup["BACKEND"] == \
               'django.core.cache.backends.db.DatabaseCache':
                cursor = connection.cursor()
                cursor.execute("DROP TABLE " + setup["LOCATION"])
                cursor.fetchone()


class Runner(DjangoTestSuiteRunner):

    def __init__(self, control, *args, **kwargs):
        self.__control = control
        super(Runner, self).__init__(*args, **kwargs)

    # Override build_suite to just provide what we want.
    def build_suite(self, *args, **kwargs):
        return TestSuite([SeleniumTest(self.__control)])


class Command(BaseCommand):
    help = 'Starts a live server for testing.'
    args = "address control"

    def handle(self, *args, **options):
        server_address, control = args
        patch_for_test_db_setup()

        print "Server at:", server_address
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = server_address
        os.environ["DJANGO_SETTINGS_MODULE"] = "btw.test_settings"

        with mock.patch.multiple("bibliography.zotero.Zotero",
                                 get_all=get_all_mock,
                                 get_item=get_item_mock):
            while True:
                print "Starting new server."
                runner = Runner(control)
                runner.run_tests(test_labels=None)
                get_item_mock.reset_mock()
                get_all_mock.reset_mock()
                mock_records.reset()
