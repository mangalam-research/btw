import os
import subprocess

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from btw.celery import app
from core.tasks import get_btw_env
from lib.util import join_prefix
from bibliography.tasks import periodic_fetch_items
from redis.exceptions import ConnectionError

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


def get_defined_workers():
    if get_defined_workers._cached:
        return get_defined_workers._cached

    prefix = settings.BTW_CELERY_WORKER_PREFIX
    if prefix.find(".") >= 0:
        raise ImproperlyConfigured(
            "BTW_CELERY_WORKER_PREFIX contains a period: " + prefix)

    ret = [
        Worker(join_prefix(prefix, "worker"),
               [settings.CELERY_DEFAULT_QUEUE]),
        Worker(join_prefix(prefix, "bibliography.worker"),
               [settings.BTW_CELERY_BIBLIOGRAPHY_QUEUE]),
    ]

    get_defined_workers._cached = ret

    return ret
get_defined_workers._cached = None

def get_running_workers(error_equals_no_worker=False):
    workers = get_defined_workers()
    i = app.control.inspect()
    try:
        d = i.stats()
        if not d:
            if error_equals_no_worker:
                return []

            raise CommandError("no Celery workers found")
    except ConnectionError as e:
        if error_equals_no_worker:
            return []

        raise CommandError(
            "cannot connect to Celery's backend: " + str(e))

    names = [w.name for w in workers]
    full_names = get_full_names(names)

    ret = []
    for worker in workers:
        full_name = full_names[worker.name]
        if full_name in d:
            ret.append(worker)

    return ret


def get_full_names(names):
    return dict(
        zip(names,
            subprocess.check_output(["celery", "multi", "names"]
                                    + names).strip().split("\n")))


class Command(BaseCommand):
    help = """\
Start the workers we need.
"""
    error_count = 0

    def handle(self, *args, **options):
        workers = get_defined_workers()

        if args[0] == "start":
            for worker in workers:
                subprocess.check_call(worker.start_cmd)

            # Kick off the periodic fetching of Zotero items.
            periodic_fetch_items.delay()
        elif args[0] == "stop":
            for worker in workers:
                subprocess.check_call(worker.stop_cmd)
        elif args[0] == "check":
            if not settings.CELERY_WORKER_DIRECT:
                # We need CELERY_WORKER_DIRECT so that the next test will work.
                raise CommandError("CELERY_WORKER_DIRECT must be True")

            running_workers = get_running_workers()
            full_names = get_full_names([w.name for w in running_workers])

            btw_env = os.environ.get("BTW_ENV")
            for worker in workers:
                full_name = full_names[worker.name]
                self.stdout.write("Checking worker %s... " % worker.name)
                if worker not in running_workers:
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
