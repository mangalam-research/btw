import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from .btwworker import get_defined_workers
from lib.redis import Config

def generate_worker_config(script_dir):

    workers = get_defined_workers()

    template = """
check process {worker_name} pidfile "{proj_path}/var/run/btw/{worker_name}.pid"
      group {group}
      depends on btw-redis
      start program = "{script_dir}/manage btwworker start {worker_name}"
            as uid btw and gid btw
      stop program = "{script_dir}/manage btwworker stop {worker_name}"
            as uid btw and gid btw
      if does not exist then start
"""

    buf = ""
    worker_names = []
    for worker in workers:
        buf += template.format(
            script_dir=script_dir,
            proj_path=settings.TOPDIR,
            worker_name=worker.name,
            group=settings.BTW_SLUGIFIED_SITE_NAME)
        worker_names.append(worker.name)
    return {
        "script": buf,
        "names": worker_names
    }

def subdir(a, b):
    """Returns whether a is a subdir of b."""
    rel = os.path.relpath(os.path.realpath(a), os.path.realpath(b))
    return not (rel == os.curdir or rel == os.pardir or
                rel.startswith(os.pardir + os.sep))

class Command(BaseCommand):
    help = """\
BTW-specific commands.
"""
    args = "command"
    requires_system_checks = False

    def check_max_args(self, command, args, maximum):
        if len(args) > maximum:
            raise CommandError(command + " takes at most " + str(maximum) +
                               " arguments.")

    def handle(self, *args, **options):
        if len(args) == 0:
            raise CommandError("you must specify a command.")

        cmd = args[0]

        proj_path = settings.TOPDIR
        btw_pidfile = "/run/uwsgi/app/btw/pid"

        if cmd == "generate-monit-config":
            if len(args) < 2:
                raise CommandError("generate-monit-config needs the directory "
                                   "that contains BTW's generated scripts.")

            self.check_max_args(cmd, args, 2)

            directory = args[1]

            # Check that the scripts exist
            non_existent = []
            for script in ["manage", "start-uwsgi"]:
                script_path = os.path.join(directory, script)
                if not os.path.exists(script_path):
                    non_existent.append(script_path)

            if len(non_existent):
                raise CommandError("generate-monit-config needs these scripts "
                                   "to exist: " +
                                   ", ".join(non_existent))

            directory = os.path.abspath(directory)

            worker_config = generate_worker_config(directory)

            template = """
check process btw-redis pidfile "{redis_pidfile}"
      group {group}
      start program = "{script_dir}/manage btwredis start"
          as uid btw and gid btw
      stop program = "{script_dir}/manage btwredis stop"
          as uid btw and gid btw
      if does not exist then start

check process btw pidfile "{btw_pidfile}"
      group {group}
      depends on {workers}, btw-redis
      start program = "{script_dir}/start-uwsgi"
      stop program = "/usr/bin/uwsgi --stop {btw_pidfile}
      if does not exist then start
"""
            self.stdout.write(template.format(
                script_dir=directory,
                redis_pidfile=Config().pidfile_path,
                btw_pidfile=btw_pidfile,
                workers=", ".join(worker_config["names"]),
                group=settings.BTW_SLUGIFIED_SITE_NAME) +
                worker_config["script"])

        elif cmd == "generate-scripts":
            if len(args) < 2:
                raise CommandError("generate-scripts needs the directory that "
                                   "contains BTW's generated scripts.")

            self.check_max_args(cmd, args, 2)

            directory = args[1]
            manage_path = os.path.join(directory, "manage")
            start_uwsgi_path = os.path.join(directory, "start-uwsgi")
            env_path = settings.ENVPATH
            python_path = os.path.join(env_path, "bin", "python") \
                if env_path is not None else "python"

            home = "/home/btw"

            with open(manage_path, 'w') as script:
                script.write("""\
#!/bin/sh
export HOME="{home}"
cd "{proj_path}"
"{python_path}" ./manage.py "$@"
""".format(
                    home=home,
                    proj_path=proj_path,
                    python_path=python_path
                ))

            with open(start_uwsgi_path, 'w') as script:
                script.write("""\
#!/bin/sh
run_dir=/run/uwsgi/app/btw
mkdir -p $run_dir
chown btw:btw $run_dir
# We need to export these so that the variable expansion performed in
# /etc/uwsgi/default.ini can happen.
export UWSGI_DEB_CONFNAMESPACE=app
export UWSGI_DEB_CONFNAME=btw
/usr/bin/uwsgi --ini /etc/uwsgi/default.ini --ini \
/etc/uwsgi/apps-enabled/btw.ini --daemonize /var/log/uwsgi/app/btw.log
""")

            for path in [manage_path, start_uwsgi_path]:
                st = os.stat(path)
                os.chmod(path, st.st_mode | 0111)

        elif cmd == "list-local-app-paths":
            from django.apps import apps
            for app in apps.get_app_configs():
                if subdir(app.path, settings.TOPDIR):
                    self.stdout.write(app.path)

        else:
            raise ValueError("unknown command: " + cmd)
