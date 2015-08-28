import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from .btwworker import generate_monit_config
from lib.redis import Config

def check_no_arguments(args, cmd):
    if len(args) > 1:
        raise CommandError("{0} does not take arguments.".format(cmd))

class Command(BaseCommand):
    help = """\
BTW-specific commands.
"""
    args = "command"
    requires_system_checks = False

    def handle(self, *args, **options):
        if len(args) == 0:
            raise CommandError("you must specify a command.")

        cmd = args[0]

        if cmd == "generate-monit-config":
            check_no_arguments(args, cmd)

            worker_config = generate_monit_config()

            template = """
check process btw-redis pidfile {redis_pidfile}
      group {group}
      start program = "{python_path} {proj_path}/manage.py btwredis start"
          as uid btw and gid btw
      stop program = "{python_path} {proj_path}/manage.py btwredis stop"
          as uid btw and gid btw
      if does not exist then start

check process btw pidfile "{btw_pidfile}"
      group {group}
      depends on {workers}, btw-redis
      start program = "/usr/bin/uwsgi --ini /etc/uwsgi/default.ini \
--ini /etc/uwsgi/apps-enabled/btw.ini --daemonize /var/log/uwsgi/app/btw.log"
      stop program = "/usr/bin/uwsgi --stop {btw_pidfile}"
      if does not exist then start
"""
            env_path = settings.ENVPATH
            python_path = os.path.join(env_path, "bin", "python") \
                if env_path is not None else "python"

            self.stdout.write(template.format(
                redis_pidfile=Config().pidfile_path,
                python_path=python_path,
                proj_path=settings.TOPDIR,
                workers=", ".join(worker_config["names"]),
                group=settings.BTW_SLUGIFIED_SITE_NAME,
                btw_pidfile="/run/uwsgi/app/btw/pid") +
                worker_config["script"])

        else:
            raise ValueError("unknown command: " + cmd)
