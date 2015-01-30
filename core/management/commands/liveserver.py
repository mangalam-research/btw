import os
from unittest import TestSuite

import lxml.etree
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, authenticate
from django.contrib.sessions.backends.db import SessionStore
from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line
from django.test import LiveServerTestCase
from django.test.runner import DiscoverRunner
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.test.client import Client
from django.http import Http404, HttpResponse

from south.management.commands import patch_for_test_db_setup

from core.tests.common_zotero_patch import patch as zotero_patch
from lexicography.tests.data import sf_cases
from lib import util

class LexicographyPatcher(object):

    def __init__(self):
        self.old_changerecord_details = None
        self.reset()

    def reset(self):
        self.fail_on_ajax = False
        self.timeout_on_ajax = False

    def patch(self):
        import lexicography.views
        self.old_changerecord_details = \
            lexicography.views.changerecord_details

        setattr(lexicography.views, 'changerecord_details',
                self.changerecord_details)

    def changerecord_details(self, request, *args, **kwargs):
        if request.is_ajax():
            if self.fail_on_ajax:
                return HttpResponse("failing on ajax", status=400)
            elif self.timeout_on_ajax:
                raise Http404

        return self.old_changerecord_details(request, *args, **kwargs)


class SeleniumTest(LiveServerTestCase):

    reset_sequences = True

    def setUp(self):
        from bibliography.models import Item, PrimarySource
        # Id 1
        item = Item(item_key="3")
        item.uid = Item.objects.zotero.full_uid
        item.save()
        ps = PrimarySource(item=item, reference_title="Foo", genre="SU")
        ps.save()

    def __init__(self, control_read, control_write, patcher, *args, **kwargs):
        self.__control_read = control_read
        self.__control_write = control_write
        self._patcher = patcher
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
            self._patcher.reset()
            self.log("restarting...")
        else:
            self.log("stopping...")
            result.stop()

    def runTest(self):
        finished = False
        with open(self.__control_write, 'w') as out:
            out.write('started\n')
        while not finished:
            command = open(self.__control_read, 'r').read().strip()
            self.log("got command: " + command)
            args = command.split()
            if command == "quit":
                finished = True
            elif command == "restart":
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
            elif args[0] == "create":
                what = " ".join(args[1:])
                self.create_document(what)
            elif args[0] == "clearcache":
                self.clearcache(args[1:])
                with open(self.__control_write, 'w') as out:
                    out.write("\n")
            elif command == "patch changerecord_details to fail on ajax":
                self._patcher.fail_on_ajax = True
                with open(self.__control_write, 'w') as out:
                    out.write("\n")
            elif command == "patch changerecord_details to time out on ajax":
                self._patcher.timeout_on_ajax = True
                with open(self.__control_write, 'w') as out:
                    out.write("\n")
            else:
                print "Unknown command: ", command

    def create_document(self, what):
        add_raw_url = reverse("admin:lexicography_entry_rawnew")
        from lexicography.tests.util import get_valid_document_data
        data = get_valid_document_data()
        publish = True

        if what == "valid article":
            pass
        elif what == "bad semantic fields article":
            publish = False
            tree = lxml.etree.fromstring(data)
            sfs = tree.xpath(
                "//btw:sf",
                namespaces={
                    "btw": "http://mangalamresearch.org/ns/btw-storage"
                })
            ix = 0
            for case in sf_cases:
                sfs[ix].text = case
                ix += 1
            lemmas = tree.xpath(
                "//btw:lemma",
                namespaces={
                    "btw": "http://mangalamresearch.org/ns/btw-storage"
                })
            lemmas[0].text = what
            data = lxml.etree.tostring(
                tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        else:
            print "Unknown document: ", what
        User = get_user_model()
        foo = User.objects.get(username='foo')

        now = util.utcnow()

        client = Client()
        assert client.login(username='foo', password='foo')
        response = client.post(add_raw_url, {"data": data})
        assert response.status_code == 302
        from lexicography.models import Entry
        entry = Entry.objects.get(latest__datetime__gte=now)
        if publish:
            assert entry.latest.publish(foo)
        with open(self.__control_write, 'w') as out:
            out.write(entry.lemma.encode('utf-8') + "\n")

    def clearcache(self, args):
        execute_from_command_line(['liveserver', 'clearcache'] + args)

    def __unicode__(self):
        return hex(id(self))

class Suite(TestSuite):

    def __init__(self, control_read, control_write, *args, **kwargs):
        self.__control_read = control_read
        self.__control_write = control_write
        self._patcher = LexicographyPatcher()
        self._patcher.patch()

        super(Suite, self).__init__(*args, **kwargs)

    def __iter__(self):
        while True:
            yield SeleniumTest(self.__control_read, self.__control_write,
                               self._patcher)

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

        zotero_patch.start()

        # Start getting the valid document data now, in parallel with the
        # rest.
        from lexicography.tests.util import launch_fetch_task
        launch_fetch_task()

        runner = Runner(control_read, control_write, interactive=False)
        runner.run_tests(test_labels=None)
