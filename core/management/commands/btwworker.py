import os
import subprocess

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

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

        logfile = os.path.join(settings.TOPDIR, "%n.log")
        pidfile = os.path.join(settings.TOPDIR, "%n.pid")
        if args[0] == "start":
            subprocess.check_call(['celery', '-A', 'btw', 'multi', 'start',
                                   prefix + "worker", "-Q",
                                   settings.CELERY_DEFAULT_QUEUE,
                                   "--logfile=" + logfile,
                                   "--pidfile=" + pidfile])
        elif args[0] == "stop":
            subprocess.check_call(['celery', '-A', 'btw', 'multi', 'stop',
                                   prefix + "worker"])
