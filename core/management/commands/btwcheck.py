from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = """\
Performs some global site checks to ensure the site configuration is
okay.
"""
    error_count = 0

    def handle(self, *args, **options):
        site = Site.objects.get_current()
        if site.name != settings.BTW_SITE_NAME:
            self.error(("the site name in the database ({0}) "
                        "is different from the BTW_SITE_NAME "
                        "setting {1}")
                       .format(site.name, settings.BTW_SITE_NAME))

        if self.error_count > 0:
            raise CommandError(str(self.error_count) + " error(s)")

    def error(self, msg):
        self.stderr.write(msg)
        self.error_count += 1
