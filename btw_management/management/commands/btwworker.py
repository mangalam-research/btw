from __future__ import absolute_import
import os
import errno
import time
from itertools import chain

from functools32 import lru_cache
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from celery.bin.multi import MultiParser, NamespacedOptionParser, MultiTool
from celery.exceptions import TimeoutError
from celery.utils import worker_direct

from btw.celery import app
from core.tasks import get_btw_env
from lib.util import join_prefix
from bibliography.tasks import periodic_fetch_items

class Worker(object):

    def __init__(self, name, queues, start_task=None):
        self.name = name
        self.queues = queues
        # We do not use %n because it's value is resolved by Celery
        # but we need it in our code here. So we use self.name
        # instead, which is good enough for us.
        self.logfile = os.path.join(settings.BTW_LOGGING_PATH_FOR_BTW,
                                    self.name + ".log")
        self.pidfile = os.path.join(settings.BTW_RUN_PATH_FOR_BTW,
                                    self.name + ".pid")
        logfile_arg = "--logfile=" + self.logfile
        pidfile_arg = "--pidfile=" + self.pidfile
        self.start_cmd = ['multi', 'start', '-A', 'btw',
                          name, "-Q", ",".join(self.queues),
                          logfile_arg,
                          pidfile_arg]
        self.stop_cmd = ['multi', 'stopwait', '-A', 'btw',
                         name, logfile_arg, pidfile_arg]
        self.start_task = start_task

_cached_defined_workers = None

def get_defined_workers():
    # pylint: disable=global-statement
    global _cached_defined_workers
    if _cached_defined_workers:
        return _cached_defined_workers

    prefix = settings.BTW_CELERY_WORKER_PREFIX
    if prefix.find(".") >= 0:
        raise ImproperlyConfigured(
            "BTW_CELERY_WORKER_PREFIX contains a period: " + prefix)

    ret = [
        Worker(join_prefix(prefix, "worker"),
               [settings.CELERY_TASK_DEFAULT_QUEUE]),
        Worker(join_prefix(prefix, "bibliography.worker"),
               [settings.BTW_CELERY_BIBLIOGRAPHY_QUEUE],
               periodic_fetch_items.delay),
    ]

    _cached_defined_workers = ret

    return ret
_cached_defined_workers = None

def get_running_workers(error_equals_no_worker=False):
    workers = get_defined_workers()
    ret = []
    for worker in workers:
        if not worker_does_not_exist(worker):
            ret.append(worker)
    return ret


def get_full_names(names):
    return _get_full_names(tuple(names))

@lru_cache()
def _get_full_names(names):
    options = NamespacedOptionParser(names)
    options.parse()
    return dict(zip(names, (w.name for w in MultiParser().parse(options))))

def flush_caches():
    _get_full_names.cache_clear()
    global _cached_defined_workers
    _cached_defined_workers = None

def check_no_all(options, cmd):
    if options["all"]:
        raise CommandError("{0} does not take the --all option.".format(cmd))

def check_no_names(options, cmd):
    if len(options["worker_names"]):
        raise CommandError("{0} does not take arguments.".format(cmd))


def worker_does_not_exist(worker):
    if not os.path.exists(worker.pidfile):
        return "no pidfile"

    with open(worker.pidfile, 'r') as pidfile:
        try:
            pid = int(pidfile.read())
        except ValueError:
            return "cannot read pid"

    try:
        os.kill(pid, 0)
    except OSError as ex:
        if ex.errno == errno.ESRCH:
            return "process does not exist"
        elif ex.errno == errno.EPERM:
            # Process exists, we just cannot send a signal
            # to it.
            pass
        else:
            raise

    return False

class Command(BaseCommand):
    help = """\
Manage workers.
"""
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument("command")
        parser.add_argument("worker_names", nargs="*")
        parser.add_argument('--all',
                            action='store_true',
                            dest='all',
                            default=False,
                            help='Operate on all workers.')

    error_count = 0

    def handle(self, *args, **options):

        from btw.settings._env import env

        workers = get_defined_workers()

        workers_by_name = {w.name: w for w in workers}

        def get_worker_names(force_all=False):
            get_all = force_all or options["all"]
            worker_names = options["worker_names"]
            if len(worker_names):
                for name in worker_names:
                    if name not in workers_by_name:
                        raise CommandError("{0} is not a worker name"
                                           .format(name))
            elif get_all:
                worker_names = [w.name for w in workers]
            else:
                raise CommandError("must specify a worker name or use --all")
            return worker_names

        cmd = options["command"]

        if cmd == "start":
            worker_names = get_worker_names()

            running_workers = get_running_workers(error_equals_no_worker=True)
            full_names = get_full_names(worker_names)
            requests = []
            for name in worker_names:
                worker = workers_by_name[name]

                if worker in running_workers:
                    self.error("{0} is already running.".format(name))
                    continue

                full_name = full_names[name]
                retcode = MultiTool().execute_from_commandline(
                    worker.start_cmd)
                if retcode:
                    self.error("there was an error starting {0}"
                               .format(name))
                # What we are doing here has more to do with waiting
                # for the worker to start rather than actually
                # checking the return value. It would be quite
                # difficult to get into a situation where the
                # environments do not coincide.

                # We send the task directly to the worker so that we
                # are sure *that* worker handles the request.
                requests.append((worker,
                                 get_btw_env.apply_async(
                                     (),
                                     queue=worker_direct(full_name))))

            for worker, request in requests:
                name = worker.name
                result = request.get()
                if result != env:
                    self.error(
                        ("{0}: not using environment {1} "
                         "(uses environment {2})")
                        .format(name, env, result))

                # We have to do this to unschedule the tasks that may
                # have been scheduled by a previous worker. If we do
                # not do this, we can end up with having gobs of tasks
                # scheduled for future execution. However, we cannot
                # do this when we stop the tasks. Why? Because the
                # list of revoked tasks is held only in memory and
                # will vanish when the workers are stopped.
                self.revoke_scheduled(full_names[name])

                if worker.start_task:
                    worker.start_task()

                self.stdout.write("{0} has started.".format(name))

        elif cmd == "names":
            check_no_names(options, cmd)
            check_no_all(options, cmd)

            for name in get_worker_names(force_all=True):
                self.stdout.write(name)

        elif cmd == "lognames":
            check_no_names(options, cmd)
            check_no_all(options, cmd)

            for w in workers:
                self.stdout.write(w.logfile)

        elif cmd == "stop":
            worker_names = get_worker_names()
            running_workers = get_running_workers(error_equals_no_worker=True)

            for name in worker_names:
                worker = workers_by_name[name]
                if worker in running_workers:
                    retcode = MultiTool().execute_from_commandline(
                        worker.stop_cmd)
                    if retcode:
                        self.error("there was an error stopping {0}"
                                   .format(name))
                    self.stdout.write("{0} has stopped.".format(name))
                else:
                    self.stdout.write("{0} was not running.".format(name))

        elif cmd == "ping":
            check_no_names(options, cmd)
            check_no_all(options, cmd)

            full_names = get_full_names([w.name for w in workers])

            for worker in workers:
                self.stdout.write("Pinging worker %s... " %
                                  worker.name, ending='')

                status = worker_does_not_exist(worker)
                if status:
                    self.stdout.write("failed: " + status)
                    continue

                full_name = full_names[worker.name]
                result = app.control.ping([full_name], timeout=0.5)
                if result[0][full_name] == {u'ok': u'pong'}:
                    self.stdout.write("passed")
                else:
                    self.stdout.write("failed with response: " +
                                      (repr(result[0].get(full_name)) or ""))

        elif cmd == "check":
            check_no_names(options, cmd)
            check_no_all(options, cmd)

            if not settings.CELERY_WORKER_DIRECT:
                # We need CELERY_WORKER_DIRECT so that the next test will work.
                raise CommandError("CELERY_WORKER_DIRECT must be True")

            full_names = get_full_names([w.name for w in workers])

            for worker in workers:
                self.stdout.write("Checking worker %s... " %
                                  worker.name, ending='')

                status = worker_does_not_exist(worker)
                if status:
                    self.stdout.write("failed: " + status)
                    continue

                full_name = full_names[worker.name]

                # We send the task directly to the worker so that we
                # are sure *that* worker handles the request.
                try:
                    result = get_btw_env.apply_async(
                        (),
                        queue=worker_direct(full_name)).get(timeout=60)
                except TimeoutError:
                    self.stdout.write("failed: timed out")
                    continue

                if result != env:
                    self.stdout.write(
                        ("failed: not using environment {0} "
                         "(uses environment {1})")
                        .format(env, result))
                    continue

                self.stdout.write("passed")
        elif cmd == "revoke-scheduled":
            self.revoke_scheduled()
        else:
            raise CommandError("bad command: " + cmd)

    def revoke_scheduled(self, name=None):
        while True:
            # When we run this function just after having started a
            # worker, it is possible to get None as a value. So we
            # loop until the worker returns something sensible.
            scheduled = app.control.inspect().scheduled()
            if scheduled is not None:
                schedule_info = chain.from_iterable(scheduled.itervalues()) \
                    if name is None else scheduled.get(name, None)
                if schedule_info is not None:
                    break
            time.sleep(0.2)

        to_revoke = [scheduled["request"]["id"] for scheduled in
                     schedule_info]
        to_revoke_set = set(to_revoke)
        app.control.revoke(to_revoke, reply=True)
        # Wait until the tasks appear in the set.
        while True:
            if to_revoke_set.issubset(
                    set(chain.from_iterable(
                        app.control.inspect().revoked().itervalues()))):
                break
            time.sleep(0.2)

    def error(self, msg):
        self.stderr.write(msg)
        self.error_count += 1
