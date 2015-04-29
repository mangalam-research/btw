import os
import signal
import subprocess
import errno
import time

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from lib.util import join_prefix
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
    args = "command"

    def handle(self, *args, **options):
        if len(args) == 0:
            raise CommandError("you must specify a command.")

        prefix = settings.BTW_REDIS_SITE_PREFIX

        run_path = os.path.join(settings.BTW_RUN_PATH, "redis")
        pidfile_path = os.path.join(run_path, join_prefix(prefix,
                                                          "redis.pid"))
        sockfile_path = os.path.join(settings.BTW_REDIS_SOCKET_DIR_PATH,
                                     join_prefix(prefix, "redis.sock"))
        dumpfile_name = join_prefix(prefix, "dump.rdb")

        def running():
            cli = subprocess.Popen(
                ["redis-cli", "-s", sockfile_path],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            out, _ = cli.communicate("auth " + settings.BTW_REDIS_PASSWORD)

            return out == "OK\n"

        cmd = args[0]
        if cmd == "start":
            if running():
                raise CommandError("redis appears to be running already.")

            template = open(
                os.path.join("core", "management", "templates",
                             "redis.conf")).read()

            makedirs(run_path)
            makedirs(settings.BTW_REDIS_SOCKET_DIR_PATH)

            generated_name = os.path.join(run_path,
                                          join_prefix(prefix, "redis.conf"))
            try:
                old_template = open(generated_name).read()
            except IOError:
                old_template = None

            logging_path = os.path.join(settings.BTW_LOGGING_PATH, "redis")
            makedirs(logging_path)

            logfile_path = os.path.join(logging_path,
                                        join_prefix(prefix,
                                                    "redis-server.log"))
            dir_path = os.path.join(settings.TOPDIR, "var", "lib", "redis")
            makedirs(dir_path)

            generated_template = template.format(
                pidfile_path=pidfile_path,
                sockfile_path=sockfile_path,
                logfile_path=logfile_path,
                dir_path=dir_path,
                dumpfile_name=dumpfile_name,
                redis_pass=settings.BTW_REDIS_PASSWORD)

            if generated_template != old_template:
                open(generated_name, 'w').write(generated_template)

            subprocess.check_call(["redis-server", generated_name])
            if running():
                self.stdout.write("Started redis.")
            else:
                raise CommandError("cannot talk to redis.")

        elif cmd == "stop":
            if len(get_running_workers(error_equals_no_worker=True)):
                raise CommandError(
                    "cannot stop redis while BTW workers are running.")

            try:
                pid = open(pidfile_path).read().strip()
            except IOError:
                raise CommandError("cannot read pid from " + pidfile_path)

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

            self.stdout.write("Stopped redis.")

        elif cmd == "check":
            if not running():
                raise CommandError("cannot contact redis.")

            self.stdout.write("Redis instance is alive.")
