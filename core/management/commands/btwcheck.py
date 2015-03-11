import os

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
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

        self.check_paths()
        self.check_site()
        self.check_celery()

        if self.error_count > 0:
            raise CommandError(str(self.error_count) + " error(s)")

    def check_paths(self):
        for path in ["BTW_LOGGING_PATH_FOR_BTW", "BTW_WED_LOGGING_PATH",
                     "BTW_RUN_PATH_FOR_BTW"]:
            self.check_path_exists(path)

    def check_path_exists(self, path):
        value = getattr(settings, path)
        if not os.path.exists(value):
            self.error('settings.{0} ("{1}") does not exist'.format(path,
                                                                    value))

    def check_site(self):
        site = Site.objects.get_current()
        if site.name != settings.BTW_SITE_NAME:
            self.error(("the site name in the database ({0}) "
                        "is different from the BTW_SITE_NAME "
                        "setting {1}")
                       .format(site.name, settings.BTW_SITE_NAME))

    def check_celery(self):
        call_command('btwworker', 'check')

    def error(self, msg):
        self.stderr.write(msg)
        self.error_count += 1
