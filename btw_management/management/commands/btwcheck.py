import os
import sys

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = """\
Performs some global site checks to ensure the site configuration is
okay.
"""
    error_count = 0

    def handle(self, *args, **options):

        self.check_editors()
        self.check_paths()
        self.check_site()
        stdout = options.get('stdout', sys.stdout)
        stderr = options.get('stderr', sys.stderr)
        self.check_redis(stdout, stderr)
        self.check_celery(stdout, stderr)

        if self.error_count > 0:
            raise CommandError(str(self.error_count) + " error(s)")

    def check_editors(self):
        if getattr(settings, "BTW_EDITORS", None) is None:
            self.error('settings.BTW_EDITORS is not set')
            return

        editors = settings.BTW_EDITORS
        if not isinstance(editors, list) or \
           not self.check_each_editor(editors):
            self.error('settings.BTW_EDITORS is not of the right format')

    def check_each_editor(self, editors):
        initial_error_count = self.error_count
        expected_fields = ('forename', 'surname', 'genName')
        for editor in editors:
            if not isinstance(editor, dict):
                self.error('editor is not a dictionary: {0}'.format(editor))
                continue

            for field in expected_fields:
                value = editor.get(field, None)
                if value is None:
                    self.error('missing {0} in {1}'.format(field, editor))
                elif not isinstance(value, unicode):
                    self.error('field {0} is not a unicode value in {1}'
                               .format(field, editor))

            for key in editor.iterkeys():
                if key not in expected_fields:
                    self.error('spurious field {0} in {1}'.format(key, editor))

        return self.error_count == initial_error_count

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
                        "setting ({1})")
                       .format(site.name, settings.BTW_SITE_NAME))

    def check_celery(self, stdout, stderr):
        call_command('btwworker', 'check', stdout=stdout, stderr=stderr)

    def check_redis(self, stdout, stderr):
        call_command('btwredis', 'check', stdout=stdout, stderr=stderr)

    def error(self, msg):
        self.stderr.write(msg)
        self.error_count += 1
