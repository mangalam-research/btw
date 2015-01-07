import os
import mock
from unittest import TestSuite

from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.core.management.base import BaseCommand
from django.test import LiveServerTestCase
from django.test.runner import DiscoverRunner
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.test.client import Client
from south.management.commands import patch_for_test_db_setup
from pebble import process

from bibliography.tests import mock_zotero
from lexicography.models import Entry
from lib import util


mock_records = mock_zotero.Records([
    {
        "data":
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
        "links": {
            "alternate": {
                "href": "https://www.foo.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
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
        "links": {
            "alternate": {
                "href": "https://www.foo2.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "itemKey": "3",
            "title": "Title 3",
            "date": "Date 3",
            "creators": [
                {"name": "Zeno (Name 1 for Title 3)"},
                {"firstName": "FirstName 2 for Title 3",
                 "lastName": "LastName 2 for Title 3"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo3.com",
                "type": "text/html"
            }
        }
    }
])

#
# What we are doing here is running the code that reads and processes
# the data necessary to create a valid document in *parallel* with the
# rest of the code. When a test actually requires the code, it
# probably will not have to wait for the read + process operation
# because it will already have been done.
#

@process.concurrent
def fetch():
    with open("utils/schemas/prasada.xml") as f:
        data = f.read().decode("utf-8")

    # Clean it for raw edit.
    data = util.run_xsltproc("utils/xsl/strip.xsl", data)
    return data

fetch_task = fetch()

def get_valid_document_data():
    if get_valid_document_data.data is not None:
        return get_valid_document_data.data

    data = fetch_task.get()

    get_valid_document_data.data = data
    return data

get_valid_document_data.data = None

# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)

class SeleniumTest(LiveServerTestCase):

    reset_sequences = True

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
        from django.conf import settings
        self.fixtures = \
            [os.path.join(settings.TOPDIR, "lexicography", "fixtures",
                          "initial_data.json"),
             os.path.join(settings.TOPDIR, "core", "tests", "fixtures",
                          "sites.json")] + \
            list(os.path.join(settings.TOPDIR, "lexicography", "tests",
                              "fixtures", x)
                 for x in ("users.json", "views.json", "allauth.json"))
        self.next = None

    def log(self, msg):
        if False:
            print repr(self), hex(id(self)) + ":", msg

    def run(self, result=None):
        super(SeleniumTest, self).run(result)
        if self.next == "restart":
            self.log("restarting...")
        else:
            self.log("stopping...")
            result.stop()

    def runTest(self):
        finished = False
        with open(self.__control_write, 'w') as out:
            out.write('started\n')
        while not finished:
            command = open(self.__control_read, 'r').read()
            self.log("got command: " + command)
            args = command.split()
            if args[0] == "quit":
                finished = True
            elif args[0] == "restart":
                self.next = "restart"
                # Stop reading the control pipe.
                finished = True
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
                add_raw_url = reverse("admin:lexicography_entry_rawnew")
                data = get_valid_document_data()
                User = get_user_model()
                foo = User.objects.get(username='foo')

                now = util.utcnow()

                client = Client()
                assert client.login(username='foo', password='foo')
                response = client.post(add_raw_url, {"data": data})
                assert response.status_code == 302
                entry = Entry.objects.get(latest__datetime__gte=now)
                assert entry.latest.publish(foo)
                with open(self.__control_write, 'w') as out:
                    out.write(entry.lemma.encode('utf-8') + "\n")
            else:
                print "Unknown command: ", command

    def __unicode__(self):
        return hex(id(self))

class Suite(TestSuite):

    def __init__(self, control_read, control_write, *args, **kwargs):
        self.__control_read = control_read
        self.__control_write = control_write

        super(Suite, self).__init__(*args, **kwargs)

    def __iter__(self):
        while True:
            yield SeleniumTest(self.__control_read, self.__control_write)

class Runner(DiscoverRunner):

    def __init__(self, control_read, control_write, *args, **kwargs):
        self.__control_read = control_read
        self.__control_write = control_write
        super(Runner, self).__init__(*args, **kwargs)

    # Override build_suite to just provide what we want.
    def build_suite(self, *args, **kwargs):
        return Suite(self.__control_read, self.__control_write)


class Command(BaseCommand):
    help = 'Starts a live server for testing.'
    args = "address control_read control_write"

    def handle(self, *args, **options):
        server_address, control_read, control_write = args
        patch_for_test_db_setup()

        print "Starting server at:", server_address
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = server_address

        with mock.patch.multiple("bibliography.zotero.Zotero",
                                 get_all=get_all_mock,
                                 get_item=get_item_mock):
            runner = Runner(control_read, control_write, interactive=False)
            runner.run_tests(test_labels=None)
