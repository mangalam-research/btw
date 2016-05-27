import os
from unittest import TestSuite

import lxml.etree
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, \
    HASH_SESSION_KEY, authenticate
from django.contrib.sites.models import Site
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth.models import Group, Permission, ContentType
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management import execute_from_command_line, call_command
from django.test import LiveServerTestCase
from django.test.runner import DiscoverRunner
from django.core.urlresolvers import reverse, resolve
from django.contrib.auth import get_user_model
from django.test.client import Client
from django.http import Http404, HttpResponse
from django.utils import translation
from django.db import transaction
from cms.test_utils.testcases import BaseCMSTestCase
from allauth.account.models import EmailAddress

from core.tests.common_zotero_patch import patch as zotero_patch
from lexicography.tests.data import invalid_sf_cases, valid_sf_cases
from lexicography.xml import tei_namespace, btw_namespace, \
    default_namespace_mapping, XMLTree
from lib import util
from lib.testutil import unmonkeypatch_databases
from bibliography.models import Item, PrimarySource
from bibliography.tasks import fetch_items
from semantic_fields.models import SemanticField
from btw_management.management.commands.btwdb import create_perms


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

User = get_user_model()

class SeleniumTest(BaseCMSTestCase, LiveServerTestCase):

    reset_sequences = True

    def setUp(self):
        super(SeleniumTest, self).setUp()
        translation.activate('en-us')

        # We have to perform the job of btwdb set_site_name here
        # because the cleanup mangles the site name.
        with transaction.atomic():
            from django.conf import settings
            if settings.BTW_DISABLE_MIGRATIONS:
                create_perms()

            site = Site.objects.get_current()
            site.name = settings.BTW_SITE_NAME
            site.save()

            # We must delete the one user created by create_perms or we'll
            # have a sequence problem.  Note that this replicates the
            # behavior of loaddata: the user created by create_perms would
            # be overwritten by the user with the same pk in the loaddata
            # file.
            User.objects.all().delete()

            admin = User.objects.create_superuser(
                username='admin', email="admin@foo.foo", password="admin")

            foo = User.objects.create_user(username="foo",
                                           first_name="Foo",
                                           last_name="Bwip",
                                           email="foo@foo.foo",
                                           password="foo")
            scribe = Group.objects.get(name='scribe')
            foo.groups.add(scribe)

            resolver = util.PermissionResolver(Permission, ContentType)
            perms = [resolver.resolve(x) for x in [
                ["add_primarysource", "bibliography", "primarysource"],
                ["change_primarysource", "bibliography", "primarysource"],
                ["add_semanticfield", "semantic_fields", "semanticfield"]
            ]]
            foo.user_permissions.add(*perms)

            foo2 = User.objects.create_user(username="foo2",
                                            first_name="Foo",
                                            last_name="Glerbl",
                                            email="foo2@foo.foo",
                                            password="foo")
            foo2.groups.add(scribe)

            for user in (admin, foo, foo2):
                EmailAddress.objects.create(user=user, verified=True,
                                            primary=True, email=user.email)

            # Bleh... by the time we get here the workers are running so
            # one fetch_items has already run. We need to flush the table
            # and repopulate it as we want.
            Item.objects.all().delete()

            fixtures = \
                [os.path.join(settings.TOPDIR, "semantic_fields", "tests",
                              "fixtures", "hte.json"),
                 os.path.join(settings.TOPDIR, "lexicography", "tests",
                              "fixtures", "views.json")]

            call_command('loaddata', *fixtures, **{'verbosity': 0})

            # Id 1
            item = Item(item_key="3")
            item.uid = Item.objects.zotero.full_uid
            item.save()
            ps = PrimarySource(item=item, reference_title="Foo", genre="SU")
            ps.save()
            fetch_items()

            # Make a custom field so that we can test searches for it
            first = SemanticField.objects.first()
            first.make_child("CUSTOM", "n")

            from lib import cmsutil
            cmsutil.refresh_cms_apps()
            from cms.api import create_page, add_plugin
            self.home_page = create_page("Home", "generic_page.html",
                                         "en-us")
            self.home_page.toggle_in_navigation()
            self.home_page.publish('en-us')
            self.lexicography_page = \
                create_page("Lexicography", "generic_page.html",
                            "en-us", apphook='LexicographyApp')
            self.lexicography_page.toggle_in_navigation()
            self.lexicography_page.publish('en-us')
            self.bibliography_page = \
                create_page("Bibliography", "generic_page.html",
                            "en-us", apphook='BibliographyApp')
            self.bibliography_page.toggle_in_navigation()
            self.bibliography_page.publish('en-us')
            self.cite_page = create_page("Cite", "generic_page.html", "en-us")
            self.cite_page.toggle_in_navigation()
            content = self.cite_page.placeholders.get(slot='content')
            add_plugin(content, "CitePlugin", "en-us")
            self.cite_page.publish('en-us')
            self.semantic_fields_page = \
                create_page("Semantic Fields", "generic_page.html",
                            "en-us", apphook='SemanticFieldsApp')
            self.semantic_fields_page.toggle_in_navigation()
            self.semantic_fields_page.publish('en-us')

    def __init__(self, control_read, control_write, patcher, *args, **kwargs):
        self.__control_read = control_read
        self.__control_write = control_write
        self._patcher = patcher
        super(SeleniumTest, self).__init__(*args, **kwargs)
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
                # This is needed if SessionAuthenticationMiddleware is used
                # or if we are in Django 1.10 or over where it becomes
                # default.
                s[HASH_SESSION_KEY] = user.get_session_auth_hash() \
                    if hasattr(user, 'get_session_auth_hash') else ''

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
            elif command.startswith("changerecord link to entry link "):
                cr_link = args[5]
                resolved = resolve(cr_link)
                from lexicography.models import ChangeRecord
                cr = ChangeRecord.objects.get(
                    id=resolved.kwargs['changerecord_id'])
                with open(self.__control_write, 'w') as out:
                    out.write(reverse("lexicography_entry_details",
                                      args=(cr.entry.id, )) + "\n")
            else:
                print "Unknown command: ", command

    def create_document(self, what):
        add_raw_url = reverse("full-admin:lexicography_entry_rawnew")
        from lexicography.tests.util import get_valid_document_data
        data = get_valid_document_data()
        publish = True

        if what == "valid article":
            xmltree = XMLTree(data)
        elif what in ("valid article, with one author",
                      "valid article, with two authors",
                      "valid article, with three authors",
                      "valid article, with four authors"):
            total_authors = {
                "valid article, with one author": 1,
                "valid article, with two authors": 2,
                "valid article, with three authors": 3,
                "valid article, with four authors": 4
            }[what]

            publish = True
            xmltree = XMLTree(data)
            authors = xmltree.tree.xpath("//btw:credit",
                                         namespaces=default_namespace_mapping)

            assert len(authors) == 2
            if total_authors == 1:
                authors[1].getparent().remove(authors[1])
            elif total_authors == 2:
                pass
            else:
                btw_credits = authors[0].getparent()
                for number in xrange(len(authors) + 1, total_authors + 1):
                    btw_credits.append(lxml.etree.XML("""
<btw:credit xmlns="{0}" xmlns:btw="{1}">
  <resp>Resp</resp>
    <persName><forename>Forename {2}</forename><surname>Surname {2}</surname>\
    <genName>GenName {2}</genName></persName>
</btw:credit>""".format(tei_namespace, btw_namespace, number)))

            xmltree.alter_lemma(what)
            data = xmltree.serialize()
        elif what in ("valid article, with one editor",
                      "valid article, with two editors",
                      "valid article, with three editors",
                      "valid article, with four editors"):
            total_editors = {
                "valid article, with one editor": 1,
                "valid article, with two editors": 2,
                "valid article, with three editors": 3,
                "valid article, with four editors": 4
            }[what]

            publish = True
            xmltree = XMLTree(data)
            editors = xmltree.tree.xpath("//tei:editor",
                                         namespaces=default_namespace_mapping)

            assert len(editors) == 1
            if total_editors == 1:
                pass
            else:
                btw_credits = editors[0].getparent()
                for number in xrange(len(editors) + 1, total_editors + 1):
                    btw_credits.append(lxml.etree.XML("""
<editor xmlns="{0}">
  <persName><forename>Forename {1}</forename><surname>Surname {1}</surname>\
  <genName>GenName {1}</genName></persName>
</editor>""".format(tei_namespace, number)))

            xmltree.alter_lemma(what)
            data = xmltree.serialize()
        elif what in ("valid article, with bad semantic fields",
                      "valid article, with good semantic fields"):
            publish = False
            xmltree = XMLTree(data)
            sfs = xmltree.tree.xpath("//btw:sf",
                                     namespaces=default_namespace_mapping)
            ix = 0
            cases = invalid_sf_cases if what.endswith("bad semantic fields") \
                else valid_sf_cases
            for case in cases:
                sfs[ix].text = case
                ix += 1

            xmltree.alter_lemma(what)
            data = xmltree.serialize()
        else:
            print "Unknown document: ", what

        from lexicography.models import Entry
        try:
            entry = Entry.objects.get(lemma=xmltree.extract_lemma())
        except Entry.DoesNotExist:
            entry = None

        if entry is None:
            User = get_user_model()
            foo = User.objects.get(username='foo')

            now = util.utcnow()

            client = Client()
            assert client.login(username='foo', password='foo')
            response = client.post(add_raw_url, {"data": data})
            assert response.status_code == 302
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

    def setup_databases(self, *args, **kwargs):
        unmonkeypatch_databases()
        return super(Runner, self).setup_databases(*args, **kwargs)

class Command(BaseCommand):
    help = 'Starts a live server for testing.'
    args = "address control_read control_write"

    def handle(self, *args, **options):
        server_address, control_read, control_write = args

        print "Starting server at:", server_address
        os.environ['DJANGO_LIVE_TEST_SERVER_ADDRESS'] = server_address

        zotero_patch.start()

        # We do this to remove an error message about reloading the
        # app. The way we use Django CMS in this test setup, we do not
        # need to reload.
        from cms.signals.apphook import debug_server_restart
        from cms.signals import urls_need_reloading

        urls_need_reloading.disconnect(debug_server_restart)

        # Start getting the valid document data now, in parallel with the
        # rest.
        from lexicography.tests.util import launch_fetch_task
        launch_fetch_task()

        runner = Runner(control_read, control_write, interactive=False)
        runner.run_tests(test_labels=None)
