import subprocess
import time
import os
import signal
import xmlrpclib
import argparse

from django.core.management.base import BaseCommand, CommandError, \
    CommandParser
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from eulexistdb.db import ExistDB
from lib.existdb import get_admin_db, get_chunk_collection_path, running
from lib import xquery
from lexicography.xml import wrap_btw_document

from lexicography.models import Chunk

def assert_running():
    if not running():
        raise CommandError("eXist is not running.")


class Command(BaseCommand):
    help = """\
Manage the eXist server used by BTW.
"""
    requires_system_checks = False

    btw_group = "btw"

    chunk_index = os.path.join(os.path.dirname(__file__), "chunk_index.xml")

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.topdir = topdir = settings.TOPDIR
        self.home_path = settings.EXISTDB_HOME_PATH
        self.log_path = os.path.join(topdir, "var/log/eXist.log")
        self.pidfile_path = os.path.join(topdir, "var/run/eXist.pid")

        self.server_user = settings.EXISTDB_SERVER_USER

        self.new_user_groups = {
            self.server_user: 'Group for the BTW user',
            self.btw_group: 'Group for BTW resources'
        }

        root_collection = os.path.normpath(
            settings.EXISTDB_ROOT_COLLECTION)

        # Normalize
        if root_collection[-1] == "/":
            root_collection = root_collection[:-1]

        # Prevent stupid mistakes...
        if root_collection in ("/", "/apps", "/system"):
            raise ImproperlyConfigured(
                "'{}' is not a valid value for EXISTDB_ROOT_COLLECTION"
                # Use the original value...
                .format(settings.EXISTDB_ROOT_COLLECTION))

        self.root_collection = root_collection
        self.subcommands = {}

        for cmd in ["start", "stop", "createuser", "dropuser", "createdb",
                    "dropdb", "load", "loadindex", "checkdb"]:
            self.register_subcommand(cmd, getattr(self, cmd))

    def register_subcommand(self, name, method):
        self.subcommands[name] = method

    def add_arguments(self, parser):
        cmd = self

        class SubParser(CommandParser):

            def __init__(self, **kwargs):
                super(SubParser, self).__init__(cmd, **kwargs)

        subparsers = parser.add_subparsers(title="subcommands",
                                           parser_class=SubParser)

        start_sp = subparsers.add_parser(
            "start",
            description="Start the existdb server",
            help="Start the existdb server",
            formatter_class=argparse.RawTextHelpFormatter)

        start_sp.set_defaults(method=self.start)
        start_sp.add_argument("--full",
                              action='store_true',
                              default=False,
                              help='Start a full server.')

        commands = set(self.subcommands.keys())
        commands.remove("start")

        for cmd in commands:
            method = self.subcommands[cmd]
            sp = subparsers.add_parser(
                cmd,
                description=method.__doc__,
                help=method.__doc__,
                formatter_class=argparse.RawTextHelpFormatter)
            sp.set_defaults(method=method)

    def handle(self, *args, **options):
        options['method'](options)

    def start(self, options):
        """
        Start the existdb server.
        """
        if running():
            raise CommandError("eXist appears to be running already.")

        full = options["full"]
        bin_path = os.path.join(self.home_path, "bin")
        executable = os.path.join(bin_path,
                                  "startup.sh" if full else "server.sh")

        log_path = self.log_path
        if os.path.exists(log_path):
            os.rename(log_path, log_path + ".old")

        with open(log_path, 'w') as log:
            child = subprocess.Popen([executable], stdout=log,
                                     stderr=log, preexec_fn=os.setsid)

        with open(self.pidfile_path, 'w') as pidfile:
            pidfile.write(str(child.pid))

        # We now check the output
        maxwait = 10  # Wait a maximum of 10 seconds for it to start.
        start = time.time()
        started = False
        while not started and time.time() - start < maxwait:
            with open(log_path, 'r') as readlog:
                if "Server has started on ports" in readlog.read():
                    started = True
                    break
            time.sleep(0.2)

        if started:
            self.stdout.write("Started eXist.")
        else:
            raise CommandError("cannot talk to eXist.")

    def stop(self, _options):
        """
        Stop the existdb server.
        """
        with open(self.pidfile_path, 'r') as pidfile:
            pid = int(pidfile.read().strip())

        try:
            # SIGTERM does not do it...
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except OSError as ex:
            if ex.errno != 3:
                raise

        self.stdout.write("Stopped eXist.")

    def createuser(self, _options):
        """
        Create the user and groups necessary for using the server.
        """
        assert_running()
        db = get_admin_db()

        for (group, desc) in self.new_user_groups.iteritems():
            db.server.addGroup(
                group,
                {'http://exist-db.org/security/description': desc})

        db.server.addAccount(
            self.server_user,
            settings.EXISTDB_SERVER_PASSWORD,
            "", self.new_user_groups.keys(),
            True, 0022,
            {
                'http://exist-db.org/security/description':
                'BTW user'
            })

        db.server.setUserPrimaryGroup(self.server_user, self.btw_group)
        db = ExistDB()

    def dropuser(self, _options):
        """
        Remove the user and groups necessary for using the server.
        """
        assert_running()
        db = get_admin_db()

        server_user = self.server_user
        db.server.removeAccount(server_user)
        try:
            db.server.getAccount(server_user)
            # If there is no exception, the account exists.
            raise CommandError("could not remove account '{}'"
                               .format(server_user))
        except xmlrpclib.Fault:
            # If there was an exception, the account does not
            # exist, which is what we wanted.
            pass

        for group in self.new_user_groups:
            # The return value is not reliable.
            db.server.removeGroup(group)
            if db.server.getGroup(group) is not None:
                raise CommandError("could not remove group '{}'"
                                   .format(group))

    def createdb(self, _options):
        """
        Create the database needed by BTW.
        """
        assert_running()

        db = get_admin_db()
        db.createCollection(settings.EXISTDB_ROOT_COLLECTION)
        db.server.setPermissions(settings.EXISTDB_ROOT_COLLECTION,
                                 self.server_user, self.btw_group, 0770)

    def dropdb(self, _options):  # pylint: disable=no-self-use
        """
        Remove the database needed by BTW.
        """
        assert_running()
        db = get_admin_db()
        db.removeCollection(settings.EXISTDB_ROOT_COLLECTION)

    def load(self, _options):  # pylint: disable=no-self-use
        """
        Load initial data into a new database. This is necessary for BTW
        to run.
        """
        assert_running()

        db = ExistDB()
        # We first garbage collect unreachable chunks...
        Chunk.objects.collect()

        chunk_collection_path = get_chunk_collection_path()
        if db.hasCollection(chunk_collection_path):
            db.removeCollection(chunk_collection_path)
        for chunk in Chunk.objects.filter(is_normal=True):
            published = chunk.changerecord_set.filter(published=True).count()
            path = os.path.join(chunk_collection_path, chunk.c_hash)
            data = wrap_btw_document(chunk.data.encode("utf-8"),
                                     published)
            db.load(data, path)

    def loadindex(self, _options):
        """
        Load the indexes used by BTW.
        """
        assert_running()
        db = get_admin_db()
        chunk_collection = get_chunk_collection_path()
        db.loadCollectionIndex(chunk_collection, open(self.chunk_index, 'r'))
        db.reindexCollection(chunk_collection)

    def checkdb(self, _options):
        """
        Checks that the server is running.
        """
        assert_running()
        self.stdout.write("BaseX instance is alive.")
