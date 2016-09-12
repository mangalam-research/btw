from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site

from lexicography.perms import create_perms as lex_create_perms
from lexicography.models import Chunk
from core.perms import create_perms as core_create_perms
from lib.command import SubCommand, SubParser

def create_perms():
    lex_create_perms()
    core_create_perms()


class MarkAllBibliographicalItemsStale(SubCommand):
    """
    Mark all the bibliographical items as being stale. This will cause
    a refresh of all the items.
    """

    name = "mark_all_bibliographical_items_stale"

    def __call__(self, command, options):
        from bibliography.models import Item
        Item.objects.mark_all_stale()
        print "All items marked stale..."


class SetSiteName(SubCommand):
    """
    Set the site of the name in the database to match the
    BTW_SITE_NAME setting.
    """

    name = "set_site_name"

    def __call__(self, command, options):
        site = Site.objects.get_current()
        site.name = settings.BTW_SITE_NAME
        site.save()
        print "Set the site name..."


class CreatePerms(SubCommand):
    """
    Create the minimal set of permissions and groups that BTW needs.
    """

    name = "create_perms"

    def __call__(self, command, options):
        create_perms()


class Collect(SubCommand):
    """
    Collect unreachable Chunks.
    """

    name = "collect"

    def __call__(self, command, options):
        chunks = Chunk.objects.collect()
        # We don't use count because the chunks are gone.
        print "Collected %d chunks." % len(chunks)

class Command(BaseCommand):
    help = "Management commands for the BTW database."
    args = "command"

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.subcommands = [MarkAllBibliographicalItemsStale, SetSiteName,
                            CreatePerms, Collect]

        for cmd in []:
            self.register_subcommand(cmd)

    def register_subcommand(self, cmd):
        self.subcommands.append(cmd)

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="subcommands",
                                           parser_class=SubParser(self))

        for cmd in self.subcommands:
            cmd_instance = cmd()
            cmd_instance.add_to_parser(subparsers)

    def handle(self, *args, **options):
        options['subcommand'](self, options)
