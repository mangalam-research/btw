import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from .btwworker import get_defined_workers
from lib.redis import Config
from lib.command import SubCommand, SubParser

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
        buf += template.format(script_dir=script_dir,
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

class GenerateMonitConfig(SubCommand):
    """
    Generate a configuration for Monit to monitor and control this BTW
installation.
    """

    name = "generate-monit-config"

    def add_to_parser(self, subparsers):
        sp = super(GenerateMonitConfig, self).add_to_parser(subparsers)
        sp.add_argument(
            "dir",
            help="The directory that contains BTW's generated scripts.")
        return sp

    def __call__(self, command, options):
        btw_pidfile = "/run/uwsgi/app/btw/pid"
        directory = options["dir"]

        # Check that the scripts exist
        non_existent = []
        for script in ["manage", "start-uwsgi"]:
            script_path = os.path.join(directory, script)
            if not os.path.exists(script_path):
                non_existent.append(script_path)

        if len(non_existent):
            raise CommandError("generate-monit-config needs these scripts "
                               "to exist: " + ", ".join(non_existent))

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
        command.stdout.write(template.format(
            script_dir=directory,
            redis_pidfile=Config().pidfile_path,
            btw_pidfile=btw_pidfile,
            workers=", ".join(worker_config["names"]),
            group=settings.BTW_SLUGIFIED_SITE_NAME) + worker_config["script"])

class GenerateScripts(SubCommand):
    """
    Generate scripts to control this BTW installation.
    """

    name = "generate-scripts"

    def add_to_parser(self, subparsers):
        sp = super(GenerateScripts, self).add_to_parser(subparsers)
        sp.add_argument(
            "dir",
            help="The directory that contains BTW's generated scripts.")
        return sp

    def __call__(self, command, options):
        proj_path = settings.TOPDIR
        directory = options["dir"]
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
""".format(home=home, proj_path=proj_path, python_path=python_path))

        with open(start_uwsgi_path, 'w') as script:
            script.write("""\
#!/bin/sh
run_dir=/run/uwsgi/app/{site}
mkdir -p $run_dir
chown btw:btw $run_dir
# We need to export these so that the variable expansion performed in
# /etc/uwsgi/default.ini can happen.
export UWSGI_DEB_CONFNAMESPACE=app
export UWSGI_DEB_CONFNAME={site}
/usr/bin/uwsgi --ini /etc/uwsgi/default.ini --ini \
/etc/uwsgi/apps-enabled/{site}.ini --daemonize /var/log/uwsgi/app/{site}.log
""".format(site=settings.BTW_SLUGIFIED_SITE_NAME))

        for path in [manage_path, start_uwsgi_path]:
            st = os.stat(path)
            os.chmod(path, st.st_mode | 0111)

class ListLocalAppPaths(SubCommand):
    """
    List all the paths pertaining to the applications that are local
    to this project.
    """

    name = "list-local-app-paths"

    def __call__(self, command, options):
        from django.apps import apps
        venv = os.environ.get("VIRTUAL_ENV")
        for app in apps.get_app_configs():
            # We need to check venv for cases where our virtual env
            # is a subdir of settings.TOPDIR.
            if subdir(app.path, settings.TOPDIR) and \
               not subdir(app.path, venv):
                command.stdout.write(app.path)

class DumpUrls(SubCommand):
    """
    Dump the URL configuration.
    """

    name = "dump-urls"

    def __call__(self, command, options):
        from lib.util import dump_urls
        dump_urls()

class Command(BaseCommand):
    help = """\
BTW-specific commands.
"""
    requires_system_checks = False

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.subcommands = [GenerateMonitConfig, GenerateScripts,
                            ListLocalAppPaths, DumpUrls]

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="subcommands",
                                           parser_class=SubParser(self))

        for cmd in self.subcommands:
            cmd_instance = cmd()
            cmd_instance.add_to_parser(subparsers)

    def handle(self, *args, **options):
        options["subcommand"](self, options)
