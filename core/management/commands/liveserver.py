import threading
import os
import sys
from unittest import TestSuite

from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.core.management.base import BaseCommand
from django.test import LiveServerTestCase
from django.test.simple import DjangoTestSuiteRunner
from south.management.commands import patch_for_test_db_setup
import mock

from bibliography.tests import mock_zotero
from lib import util


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
    },
    {
        "itemKey": "3",
        "title": "Title 3",
        "date": "Date 3",
        "creators": [
            {"name": "Zeno (Name 1 for Title 3)"},
            {"firstName": "FirstName 2 for Title 3",
             "lastName": "LastName 2 for Title 3"},
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
             for x in ("users.json", "views.json", "allauth.json")) + \
        [os.path.join("core", "tests", "fixtures", "sites.json")]

    def setUp(self):
        from bibliography.models import Item, PrimarySource
        item = Item(item_key="3")
        item.uid = Item.objects.zotero.full_uid
        item.save()
        ps = PrimarySource(item=item, reference_title="Foo", genre="SU")
        ps.save()

    def __init__(self, control_read, control_write, *args, **kwargs):
        self.__control_read = control_read
        self.__control_write = control_write
        super(SeleniumTest, self).__init__(*args, **kwargs)
        self.__control_thread = threading.Thread(target=self.control)

    def runTest(self):
        # This effectively causes the test to stop and wait for the
        # server to die.

        # Yep we call it this way to avoid the idiotic redefinition of
        # join present in django/test/testcases.py (present in version
        # 1.5, maybe 1.6)
        self.__control_thread.start()
        threading.Thread.join(self.server_thread)

    def control(self):
        while True:
            command = open(self.__control_read, 'r').read()
            args = command.split()
            if args[0] == "restart":
                self.server_thread.join()
                self.server_thread.httpd.socket.close()
                print "Restarting..."
                os.execl(sys.executable, sys.executable, *sys.argv)
            elif args[0] == "login":
                username = args[1]
                password = args[2]
                user = authenticate(username=username, password=password)
                s = SessionStore()
                s[SESSION_KEY] = user.pk
                s[BACKEND_SESSION_KEY] = user.backend
                s.save()
                with open(self.__control_write, 'w') as out:
                    out.write(s.session_key + "\n")
            elif command == "create valid article\n":
                from django.core.urlresolvers import reverse
                add_raw_url = reverse("admin:lexicography_entry_rawnew")
                data = open("utils/schemas/prasada.xml").read().decode("utf-8")
                # Clean it for raw edit.
                data = util.run_xsltproc("utils/xsl/strip.xsl",
                                         data)

                from django.contrib.auth import get_user_model
                User = get_user_model()
                admin = User.objects.get(username='admin')
                admin.set_password('foo')
                admin.save()

                now = util.utcnow()

                from django.test.client import Client
                client = Client()
                assert client.login(username='admin', password='foo')
                response = client.post(add_raw_url,
                                       {"data": data})
                assert response.status_code == 302
                from lexicography.models import Entry
                entry = Entry.objects.get(latest__datetime__gte=now)
                assert entry.latest.publish(admin)
                with open(self.__control_write, 'w') as out:
                    out.write(entry.lemma.encode('utf-8') + "\n")
            else:
                print "Unknown command: ", command


class Runner(DjangoTestSuiteRunner):

    def __init__(self, control_read, control_write, *args, **kwargs):
        self.__control_read = control_read
        self.__control_write = control_write
        super(Runner, self).__init__(*args, **kwargs)

    # Override build_suite to just provide what we want.
    def build_suite(self, *args, **kwargs):
        return TestSuite([SeleniumTest(self.__control_read,
                                       self.__control_write)])


class Command(BaseCommand):
    help = 'Starts a live server for testing.'
    args = "address control_read control_write"

    def handle(self, *args, **options):
        server_address, control_read, control_write = args
        patch_for_test_db_setup()

        print "Starting server at:", server_address
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = server_address
        os.environ["DJANGO_SETTINGS_MODULE"] = "btw.test_settings"

        with mock.patch.multiple("bibliography.zotero.Zotero",
                                 get_all=get_all_mock,
                                 get_item=get_item_mock):
            runner = Runner(control_read, control_write, interactive=False)
            runner.run_tests(test_labels=None)
