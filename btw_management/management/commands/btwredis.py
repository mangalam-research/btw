import os
import signal
import subprocess
import errno
import time

from django.core.management.base import BaseCommand, CommandError
from lib.redis import Config
from .btwworker import get_running_workers

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as ex:
        if ex.errno != 17:
            raise

class Command(BaseCommand):
    help = """\
Manage the redis server used by BTW.
"""
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument("command")
        parser.add_argument(
            '--delete-dump',
            action='store_true',
            dest='delete_dump',
            default=False,
            help='Delete the dump file before starting redis or '
            'after stopping it.')

    def handle(self, *args, **options):
        config = Config()

        def running():
            cli = subprocess.Popen(
                ["redis-cli", "-s", config.sockfile_path],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            out, _ = cli.communicate("auth " + config.password)

            return out == "OK\n"

        cmd = options["command"]
        if cmd == "start":
            if running():
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

            subprocess.check_call(
                ["redis-server", config.generated_config_path])
            tries = 10
            is_up = False
            while not running():
                tries -= 1
                if tries == 0:
                    break
                time.sleep(0.1)
            else:
                is_up = True

            if is_up:
                self.stdout.write("Started redis.")
            else:
                raise CommandError("cannot talk to redis.")

        elif cmd == "stop":
            # We need to perform this test first because
            # get_running_workers will cause Celery to access
            # Redis. So if it is not running the code there will fail!
            if not running():
                self.stdout.write("Redis is not running.")
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

            self.stdout.write("Stopped redis.")

        elif cmd == "check":
            if not running():
                raise CommandError("cannot contact redis.")

            self.stdout.write("Redis instance is alive.")
