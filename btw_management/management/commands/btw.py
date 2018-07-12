import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from .btwworker import get_defined_workers
from lib.redis import Config
from lib.command import SubCommand, SubParser

def subdir(a, b):
    """Returns whether a is a subdir of b."""
    rel = os.path.relpath(os.path.realpath(a), os.path.realpath(b))
    return not (rel == os.curdir or rel == os.pardir or
                rel.startswith(os.pardir + os.sep))

def generate_worker_systemd_config(common):

    workers = get_defined_workers()

    template = """\
[Unit]
Description=BTW Worker {worker_name} for site {site}
BindsTo={redis_service}
BindsTo={existdb_service}
After={redis_service}
After={existdb_service}
PartOf={main_service}
OnFailure={notification_service_invocation}

[Service]
Type=forking
PIDFile={proj_path}/var/run/btw/{worker_name}.pid
ExecStart={script_dir}/manage btwworker start {worker_name}
ExecStop={script_dir}/manage btwworker stop {worker_name}
Restart=on-failure
User=btw
Group=btw

[Install]
RequiredBy={main_service}
"""

    service_names = []
    for worker in workers:
        buf = template.format(worker_name=worker.name, **common)
        # Worker names already contain the site name so we don't
        # prefix it.
        service_name = "{}.service".format(worker.name)
        with open(os.path.join(common["service_dir"], service_name), "w") \
                as service_file:
            service_file.write(buf)

        service_names.append(service_name)
    return service_names

class GenerateSystemdServices(SubCommand):
    """
    Generate service files for systemd.
    """

    name = "generate-systemd-services"

    def add_to_parser(self, subparsers):
        sp = super(GenerateSystemdServices, self) .add_to_parser(subparsers)
        sp.add_argument(
            "scripts",
            help="The directory that contains BTW's generated scripts.")

        sp.add_argument(
            "services",
            help="The directory that will contain the service filesx.")

        return sp

    def __call__(self, command, options):
        script_dir = options["scripts"]
        service_dir = options["services"]

        # Check that the scripts exist
        non_existent = []
        for script in ["manage", "start-uwsgi", "notify"]:
            script_path = os.path.join(script_dir, script)
            if not os.path.exists(script_path):
                non_existent.append(script_path)

        if len(non_existent):
            raise CommandError("we need these scripts to exist: " +
                               ", ".join(non_existent))

        site = settings.BTW_SLUGIFIED_SITE_NAME.replace("_", "-")
        main_service = site + ".service"
        redis_service = site + "-redis.service"
        uwsgi_service = site + "-uwsgi.service"
        existdb_service = site + "-existdb.service"
        notification_service = site + "-notification@.service"
        notification_service_invocation = \
            notification_service.replace("@", "@%n")

        topdir = settings.TOPDIR
        common = {
            "proj_path": topdir,
            "site": site,
            "main_service": main_service,
            "redis_service": redis_service,
            "uwsgi_service": uwsgi_service,
            "existdb_service": existdb_service,
            "notification_service": notification_service,
            "notification_service_invocation": notification_service_invocation,
            "redis_pidfile": Config().pidfile_path,
            "existdb_pidfile": os.path.join(topdir, "var/run/eXist.pid"),
            "script_dir": os.path.abspath(script_dir),
            "service_dir": service_dir,
            "btw_pidfile": "/run/uwsgi/app/btw/pid",
        }

        worker_services = generate_worker_systemd_config(common)

        components = [redis_service, uwsgi_service, existdb_service] + \
            worker_services

        with open(os.path.join(service_dir, main_service), "w") as btw:
            btw.write("""\
[Unit]
Description=BTW Application for site {site}
OnFailure={notification_service_invocation}

[Service]
Type=oneshot
ExecStart=/bin/true
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
{also}
"""
                      .format(also="\n".join(("Also=" + c) for c
                                             in components),
                              **common))

        with open(os.path.join(service_dir, redis_service), "w") \
                as out:
            out.write("""\
[Unit]
Description=BTW Redis Instance for site {site}
PartOf={main_service}
OnFailure={notification_service_invocation}

[Service]
Type=forking
PIDFile={redis_pidfile}
ExecStart={script_dir}/manage btwredis start
ExecStop={script_dir}/manage btwredis stop
Restart=on-failure
# Restarting too fast causes issues.
RestartSec=1
User=btw
Group=btw

[Install]
RequiredBy={main_service}
""".format(**common))

        with open(os.path.join(service_dir, existdb_service), "w") \
                as out:
            out.write("""\
[Unit]
Description=BTW eXist-db instance for site {site}
PartOf={main_service}
OnFailure={notification_service_invocation}

[Service]
Type=forking
PIDFile={existdb_pidfile}
ExecStart={script_dir}/manage btwexistdb start --timeout=40
ExecStop={script_dir}/manage btwexistdb stop
Restart=on-failure
User=btw
Group=btw

[Install]
RequiredBy={main_service}
""".format(**common))

        with open(os.path.join(service_dir, uwsgi_service), "w") \
                as out:
            out.write("""\
[Unit]
Description=BTW UWSGI Instance for site {site}
BindsTo={redis_service}
BindsTo={existdb_service}
{binds_to_workers}
After={redis_service}
After={existdb_service}
{after_workers}
PartOf={main_service}
OnFailure={notification_service_invocation}

[Service]
Type=forking
PIDFile={btw_pidfile}
ExecStart={script_dir}/start-uwsgi
ExecStop=/usr/bin/uwsgi --stop {btw_pidfile}
Restart=on-failure

[Install]
RequiredBy={main_service}
"""
                      .format(binds_to_workers="\n"
                              .join(("BindsTo=" + name)
                                    for name in worker_services),
                              after_workers="\n"
                              .join(("After=" + name)
                                    for name in worker_services),
                              **common))

        with open(os.path.join(service_dir, notification_service), "w") \
                as out:
            out.write("""\
[Unit]
Description=BTW Notification Email

[Service]
Type=oneshot
ExecStart={script_dir}/notify root %i
User=nobody
Group=systemd-journal

[Install]
RequiredBy={main_service}
""".format(**common))


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
        notify_path = os.path.join(directory, "notify")
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

        with open(notify_path, 'w') as script:
            script.write("""\
#!/bin/sh

/usr/sbin/sendmail -bm $1<<TXT
Subject: [BTW SERVICE FAILURE] $2 failed

$(systemctl status --full "$2")
TXT
""")
        for path in [manage_path, start_uwsgi_path, notify_path]:
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
        self.subcommands = [GenerateScripts, GenerateSystemdServices,
                            ListLocalAppPaths, DumpUrls]

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="subcommands",
                                           parser_class=SubParser(self))

        for cmd in self.subcommands:
            cmd_instance = cmd()
            cmd_instance.add_to_parser(subparsers)

    def handle(self, *args, **options):
        options["subcommand"](self, options)
