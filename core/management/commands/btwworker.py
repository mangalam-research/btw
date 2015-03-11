import os
import subprocess

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from btw.celery import app
from core.tasks import get_btw_env
from bibliography.tasks import periodic_fetch_items

class Worker(object):

    def __init__(self, name, queues):
        self.name = name
        self.queues = queues
        self.logfile = os.path.join(settings.BTW_LOGGING_PATH_FOR_BTW,
                                    "%n.log")
        self.pidfile = os.path.join(settings.BTW_RUN_PATH_FOR_BTW,
                                    "%n.pid")
        logfile_arg = "--logfile=" + self.logfile
        pidfile_arg = "--pidfile=" + self.pidfile
        self.start_cmd = ['celery', '-A', 'btw', 'multi', 'start',
                          name, "-Q", ",".join(self.queues),
                          logfile_arg,
                          pidfile_arg]
        self.stop_cmd = ['celery', '-A', 'btw', 'multi', 'stopwait', name,
                         logfile_arg, pidfile_arg]

class Command(BaseCommand):
    help = """\
Start the workers we need.
"""
    error_count = 0

    def handle(self, *args, **options):
        prefix = settings.BTW_CELERY_WORKER_PREFIX
        if prefix.find(".") >= 0:
            raise CommandError(
                "BTW_CELERY_WORKER_PREFIX contains a period: " + prefix)
        prefix += "." if prefix else ""

        workers = [
            Worker(prefix + "worker", [settings.CELERY_DEFAULT_QUEUE]),
            Worker(prefix + "bibliography.worker",
                   [settings.BTW_CELERY_BIBLIOGRAPHY_QUEUE]),
        ]

        if args[0] == "start":
            for worker in workers:
                subprocess.check_call(worker.start_cmd)

            # Kick off the periodic fetching of Zotero items.
            periodic_fetch_items.delay()
        elif args[0] == "stop":
            for worker in workers:
                subprocess.check_call(worker.stop_cmd)
        elif args[0] == "check":
            i = app.control.inspect()
            try:
                d = i.stats()
                if not d:
                    raise CommandError("no Celery workers found")
            except IOError as e:
                raise CommandError(
                    "cannot connect to Celery's backend: " + str(e))

            if not settings.CELERY_WORKER_DIRECT:
                # We need CELERY_WORKER_DIRECT so that the next test will work.
                raise CommandError("CELERY_WORKER_DIRECT must be True")

            names = [w.name for w in workers]
            full_names = dict(
                zip(names,
                    subprocess.check_output(["celery", "multi", "names"]
                                            + names).strip().split("\n")))

            btw_env = os.environ.get("BTW_ENV")
            for worker in workers:
                self.stdout.write("Checking worker %s... " % worker.name)
                full_name = full_names[worker.name]
                if full_name not in d:
                    self.error("{0} is not started".format(worker.name))
                    continue

                # We send the task directly to the worker so that we
                # are sure *that* worker handles the request.
                result = get_btw_env.apply_async((), queue=full_name +
                                                 ".dq").get()
                if result != btw_env:
                    print result
                    self.error(
                        "{0} is not using BTW_ENV={1} (uses BTW_ENV={2})"
                        .format(worker.name, btw_env, result))
                self.stdout.write("passed")

    def error(self, msg):
        self.stderr.write(msg)
        self.error_count += 1
