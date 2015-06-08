from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from optparse import make_option
from django.contrib.sites.models import Site


class Command(BaseCommand):
    help = """\
Management commands for the BTW database. Possible commands:

  mark_all_bibliographical_items_stale: marks all bibliographical
items as stale, which means that they will be refetched from cached or
from the server.
"""
    args = "command"

    def handle(self, *args, **options):
        command = args[0]
        if command == "mark_all_bibliographical_items_stale":
            from bibliography.models import Item
            Item.objects.mark_all_stale()
            print "All items marked stale..."
        elif command == "set_site_name":
            site = Site.objects.get_current()
            site.name = settings.BTW_SITE_NAME
            site.save()
            print "Set the site name..."
        else:
            raise ValueError("unknown command: " + command)