import os

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.sites.models import Site
from btw.celery import app
from core.tasks import get_btw_env

class Command(BaseCommand):
    help = """\
Performs some global site checks to ensure the site configuration is
okay.
"""
    error_count = 0

    def handle(self, *args, **options):

        self.check_site()
        self.check_celery()

        if self.error_count > 0:
            raise CommandError(str(self.error_count) + " error(s)")

    def check_site(self):
        site = Site.objects.get_current()
        if site.name != settings.BTW_SITE_NAME:
            self.error(("the site name in the database ({0}) "
                        "is different from the BTW_SITE_NAME "
                        "setting {1}")
                       .format(site.name, settings.BTW_SITE_NAME))

    def check_celery(self):
        i = app.control.inspect()
        try:
            d = i.stats()
            if not d:
                self.error("no Celery workers found")
        except IOError as e:
            self.error("cannot connect to Celery's backend: " + str(e))

        if not settings.CELERY_WORKER_DIRECT:
            # We need CELERY_WORKER_DIRECT so that the next test will work.
            self.error("CELERY_WORKER_DIRECT must be True")
        else:
            btw_env = os.environ.get("BTW_ENV")
            for worker, result in [
                    (worker,
                     # We send the task directly to the worker so that we
                     # are sure *that* worker handles the request.
                     get_btw_env.apply_async((), queue=worker + ".dq").get())
                    for worker in d]:
                if result != btw_env:
                    self.error(
                        "{0} is not using BTW_ENV={1} (uses BTW_ENV={2})"
                        .format(worker, btw_env, result))

    def error(self, msg):
        self.stderr.write(msg)
        self.error_count += 1
