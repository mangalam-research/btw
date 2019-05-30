import os
import signal
import subprocess
import errno
import time

from django.core.management.base import BaseCommand, CommandError
from lib.redis import Config
from lib.command import SubCommand
from .btwworker import get_running_workers

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as ex:
        if ex.errno != 17:
            raise

def running(config):
    cli = subprocess.Popen(
        ["redis-cli", "-s", config.sockfile_path],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, _ = cli.communicate(b"auth " + config.password.encode("utf-8"))

    return out == b"OK\n"


class Start(SubCommand):
    """
    Start the redis server for BTW.
    """
    name = "start"

    def add_to_parser(self, subparsers):
        sp = super(Start, self).add_to_parser(subparsers)
        sp.add_argument('--delete-dump',
                        action='store_true',
                        dest='delete_dump',
                        default=False,
                        help='Delete the dump file before starting redis.')
        sp.add_argument('--monitor',
                        action='store_true',
                        default=False,
                        help='Start a monitor after starting redis.')
        return sp

    def __call__(self, command, options):
        config = Config()

        if running(config):
            raise CommandError("redis appears to be running already.")

        makedirs(config.run_path)
        makedirs(config.socket_dir_path)

        try:
            old_config = open(config.generated_config_path).read()
        except IOError:
            old_config = None

        makedirs(config.logging_path)
        makedirs(config.dir_path)

        if config.generated_config != old_config:
            open(config.generated_config_path, 'w').write(
                config.generated_config)

        if options["delete_dump"] and os.path.exists(config.dumpfile_path):
            os.unlink(config.dumpfile_path)

        subprocess.check_call(["redis-server", config.generated_config_path])
        tries = 10
        is_up = False
        while not running(config):
            tries -= 1
            if tries == 0:
                break
            time.sleep(0.1)
        else:
            is_up = True

        if is_up:
            command.stdout.write("Started redis.")

            # We use this for some debugging scenarios. The redis-cli
            # instance will shutdown as soon as the redis it is
            # attached to shuts down too.
            if options["monitor"] or \
               os.environ.get("BTW_MONITOR_REDIS", False):
                pid = open(config.pidfile_path).read().strip()
                logfile_path = os.path.join("/tmp",
                                            "redis.monitor." + pid + ".log")
                with open(logfile_path, 'w') as logfile, \
                        open("/dev/null", 'r') as devnull:
                    subprocess.Popen(["redis-cli", "-s", config.sockfile_path,
                                      "-a", config.password, "monitor"],
                                     stdout=logfile,
                                     stderr=logfile,
                                     stdin=devnull)
        else:
            raise CommandError("cannot talk to redis.")


class Stop(SubCommand):
    """
    Stop the redis server for BTW.
    """
    name = "stop"

    def add_to_parser(self, subparsers):
        sp = super(Stop, self).add_to_parser(subparsers)
        sp.add_argument('--delete-dump',
                        action='store_true',
                        dest='delete_dump',
                        default=False,
                        help='Delete the dump file after stopping it.')
        return sp

    def __call__(self, command, options):
        config = Config()

        # We need to perform this test first because
        # get_running_workers will cause Celery to access
        # Redis. So if it is not running the code there will fail!
        if not running(config):
            command.stdout.write("Redis is not running.")
            return

        # We call get_running_workers without accessing Celery
        # because that causes significant complications in
        # testing, and the gain of accessing Celery for the test
        # is not great, given that stopping redis is done **very**
        # infrequently.
        if len(get_running_workers(no_celery_access=True)):
            raise CommandError(
                "cannot stop redis while BTW workers are running.")

        try:
            pid = open(config.pidfile_path).read().strip()
        except IOError:
            raise CommandError(
                "cannot read pid from " + config.pidfile_path)

        try:
            pid = int(pid)
        except ValueError:
            raise CommandError("the pid file contains something that " +
                               "cannot be converted to an integer: " + pid)

        os.kill(pid, signal.SIGTERM)

        # Wait until it is dead. When dead, os.kill(pid, 0) will
        # raise OSError with an errno of ESRCH.
        try:
            while True:
                os.kill(pid, 0)
                time.sleep(0.25)
        except OSError as ex:
            if ex.errno != errno.ESRCH:
                raise

        if options["delete_dump"] and os.path.exists(config.dumpfile_path):
            os.unlink(config.dumpfile_path)

        command.stdout.write("Stopped redis.")

class Check(SubCommand):
    """
    Check the redis server for BTW.
    """
    name = "check"

    def __call__(self, command, options):
        config = Config()

        if not running(config):
            raise CommandError("cannot contact redis.")

        command.stdout.write("Redis instance is alive.")

class Command(BaseCommand):
    help = """\
Manage the redis server used by BTW.
"""
    requires_system_checks = False

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.subcommands = []

        for cmd in [Start, Stop, Check]:
            self.register_subcommand(cmd)

    def register_subcommand(self, cmd):
        self.subcommands.append(cmd)

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand",
                                           required=True)

        for cmd in self.subcommands:
            cmd_instance = cmd()
            cmd_instance.add_to_parser(subparsers)

    def handle(self, *args, **options):
        options['subcommand'](self, options)
