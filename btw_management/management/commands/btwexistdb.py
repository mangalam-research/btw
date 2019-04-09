import subprocess
import time
import os
import signal
import xmlrpc.client

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from lib.existdb import ExistDB
from lib.existdb import get_admin_db, get_collection_path, running
from lib import xquery
from lib.command import SubCommand, SubParser
from lexicography.models import Chunk

def assert_running():
    if not running():
        raise CommandError("eXist is not running.")

class Start(SubCommand):
    """
    Start the existdb server.
    """

    name = "start"

    def add_to_parser(self, subparsers):
        sp = super(Start, self) .add_to_parser(subparsers)
        sp.add_argument('--timeout',
                        default=30,
                        type=int,
                        help='Time to wait before giving up.')

        return sp

    def __call__(self, command, options):
        if running():
            raise CommandError("eXist appears to be running already.")

        server_type = settings.BTW_EXISTDB_SERVER_TYPE

        if server_type not in ("full", "standalone"):
            raise ImproperlyConfigured("BTW_EXISTDB_SERVER_TYPE should have "
                                       "the values 'full' or 'standalone'")

        full = server_type == "full"
        bin_path = os.path.join(command.home_path, "bin")
        executable = os.path.join(bin_path,
                                  "startup.sh" if full else "server.sh")

        log_path = command.log_path
        if os.path.exists(log_path):
            os.rename(log_path, log_path + ".old")

        with open(log_path, 'w') as log:
            child = subprocess.Popen([executable], stdout=log,
                                     stderr=log, preexec_fn=os.setsid)

        with open(command.pidfile_path, 'w') as pidfile:
            pidfile.write(str(child.pid))

        # We now check the output
        maxwait = options["timeout"]
        start = time.time()
        started = False
        while not started and time.time() - start < maxwait:
            with open(log_path, 'r') as readlog:
                log_text = readlog.read()
                # The first case is eXist-db 2.2 and lower
                # The 2nd case is eXist-db 4 and higher.
                if "Server has started on ports" in log_text or \
                   "Server has started, listening on" in log_text:
                    started = True
                    break
            time.sleep(0.2)

        if started:
            command.stdout.write("Started eXist.")
        else:
            raise CommandError("cannot talk to eXist.")

class Stop(SubCommand):
    """
    Stop the existdb server.
    """

    name = "stop"

    def __call__(self, command, _options):
        with open(command.pidfile_path, 'r') as pidfile:
            pid = int(pidfile.read().strip())

        try:
            # SIGTERM does not do it...
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        except OSError as ex:
            if ex.errno != 3:
                raise

        command.stdout.write("Stopped eXist.")

class Createuser(SubCommand):
    """
    Create the user and groups necessary for using the server.
    """

    name = "createuser"

    def __call__(self, command, _options):
        assert_running()
        db = get_admin_db()

        for (group, desc) in command.new_user_groups.items():
            db.server.addGroup(
                group,
                {'http://exist-db.org/security/description': desc})

        db.server.addAccount(
            command.server_user,
            settings.EXISTDB_SERVER_PASSWORD,
            "", list(command.new_user_groups.keys()),
            True, 0o022,
            {
                'http://exist-db.org/security/description':
                'BTW user'
            })

        db.server.setUserPrimaryGroup(command.server_user, command.btw_group)
        db = ExistDB()

class Dropuser(SubCommand):
    """
    Remove the user and groups necessary for using the server.
    """

    name = "dropuser"

    def __call__(self, command, _options):
        assert_running()
        db = get_admin_db()

        server_user = command.server_user
        db.server.removeAccount(server_user)
        try:
            db.server.getAccount(server_user)
            # If there is no exception, the account exists.
            raise CommandError("could not remove account '{}'"
                               .format(server_user))
        except xmlrpc.client.Fault:
            # If there was an exception, the account does not
            # exist, which is what we wanted.
            pass

        for group in command.new_user_groups:
            # The return value is not reliable.
            db.server.removeGroup(group)
            if db.server.getGroup(group) is not None:
                raise CommandError("could not remove group '{}'"
                                   .format(group))

class Createdb(SubCommand):
    """
    Create the database needed by BTW.
    """

    name = "createdb"

    def __call__(self, command, _options):
        command.create_collections([settings.EXISTDB_ROOT_COLLECTION,
                                    get_collection_path("chunks"),
                                    get_collection_path("display")])
        Loadutil()(command, _options)

class Dropdb(SubCommand):
    """
    Remove the database needed by BTW.
    """

    name = "dropdb"

    def __call__(self, command, _options):
        assert_running()
        db = get_admin_db()
        db.removeCollection(settings.EXISTDB_ROOT_COLLECTION, True)

class Load(SubCommand):
    """
    Load initial data into a new database. This is necessary for BTW to run.
    """

    name = "load"

    def __call__(self, command, _options):
        """
        Load initial data into a new database. This is necessary for BTW
        to run.
        """
        assert_running()

        from django.utils import translation
        translation.activate('en-us')

        db = ExistDB()
        chunk_collection_path = get_collection_path("chunks")

        if db.hasCollection(chunk_collection_path):
            db.removeCollection(chunk_collection_path)

        Chunk.objects.sync_with_exist()

        display_path = get_collection_path("display")
        if db.hasCollection(display_path):
            db.removeCollection(display_path)
        Chunk.objects.prepare("xml", True)

class Loadutil(SubCommand):
    """
    Load the utilities into the database. This is necessary for BTW to run.

    (This is needed only for upgrades. The ``createdb`` command loads utilities
    automatically.)
    """

    name = "loadutil"

    def __call__(self, command, _options):
        """
        Load the utilities into the database. This is necessary for BTW to run.
        """
        util_path = get_collection_path("util")
        db = get_admin_db()
        if not db.hasCollection(util_path):
            command.create_collections([util_path])
        db.query(xquery.format(
            "xmldb:store({db}, 'empty.xml', <doc/>)", db=util_path))

class Loadindex(SubCommand):
    """
    Load the indexes used by BTW.
    """

    name = "loadindex"

    def __call__(self, command, _options):
        assert_running()
        db = get_admin_db()
        collection = get_collection_path(None)
        db.loadCollectionIndex(collection, open(command.chunk_index, 'r'))
        db.reindexCollection(collection)

class Dropindex(SubCommand):
    """
    Drop the indexes used by BTW.
    """

    name = "dropindex"

    def __call__(self, command, _options):
        assert_running()
        db = get_admin_db()
        collection = get_collection_path(None)
        db.removeCollectionIndex(collection)

class Checkdb(SubCommand):
    """
    Check that the server is running.
    """

    name = "checkdb"

    def __call__(self, command, _options):
        assert_running()
        command.stdout.write("eXist-db instance is alive.")


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
        self.subcommands = [Start, Stop, Createuser, Dropuser, Createdb,
                            Dropdb, Load, Loadutil, Loadindex, Dropindex,
                            Checkdb]

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand",
                                           parser_class=SubParser(self),
                                           required=True)

        for cmd in self.subcommands:
            cmd().add_to_parser(subparsers)

    def handle(self, *args, **options):
        options["subcommand"](self, options)

    def create_collections(self, collections):
        assert_running()
        db = get_admin_db()
        for collection in collections:
            db.createCollection(collection)
            db.server.setPermissions(collection, self.server_user,
                                     self.btw_group, 0o770)
