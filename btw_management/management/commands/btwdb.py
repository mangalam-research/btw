import datetime
import itertools

from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models import Count

from lexicography.perms import create_perms as lex_create_perms
from lexicography.models import Chunk, ChangeRecord
from lexicography.cleaning import ChangeRecordCollapser, OldVersionCleaner
from core.perms import create_perms as core_create_perms
from lib.command import SubCommand, SubParser
from lib import util

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
        command.stdout.write("All items marked stale...")


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
        command.stdout.write("Set the site name...")


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
        command.stdout.write("Collected %d chunks." % len(chunks))

class CollapseChangeRecords(SubCommand):
    """
    This command collapses ChangeRecords that appear to be
    redundant. ChangeRecords are possibly redundant if they point to
    the same version of an article. ChangeRecords that are published
    or that are too recent are not collapsed.

    Note that this operation hides information. For instance, if Bob
    saved an entry on March 30th, 2016 and then saved *the same data*
    again on March 31st, 2016, then the earlier save will be hidden
    from the entry's ChangeRecords. It will then look like Bob saved
    only on March 31st.
    """

    name = "collapse_change_records"

    def add_to_parser(self, subparsers):
        sp = super(CollapseChangeRecords, self).add_to_parser(subparsers)
        sp.add_argument(
            "--noop",
            action="store_true",
            help="Do not modify the database but print out what would be "
            "done instead.")
        return sp

    def __call__(self, command, options):
        noop = options["noop"]
        verbosity = int(options["verbosity"])
        cleaner = ChangeRecordCollapser(noop=noop, verbose=verbosity > 1)

        @cleaner.ee.on("message")
        def handler(message):
            command.stdout.write(message)

        cleaner.run()

class CleanOldEntryVersions(SubCommand):
    """
    This command goes over old versions of entries and hides
    versions that are deemed cleanable. Only versions that were
    created due to auto-save or crash recovery are hidden
    and only if they have not been published.

    THIS MAKES VERSIONS OF ARTICLES HIDDEN TO USERS. Those versions
    that are hidden won't participate any longer in searches, edits,
    etc. For all intents and purposes, it is as if they did not exist.
    """

    name = "clean_old_versions"

    def add_to_parser(self, subparsers):
        sp = super(CleanOldEntryVersions, self).add_to_parser(subparsers)
        sp.add_argument(
            "--noop",
            action="store_true",
            help="Do not modify the database but print out what would be "
            "done instead.")
        return sp

    def __call__(self, command, options):
        noop = options["noop"]
        verbosity = int(options["verbosity"])
        cleaner = OldVersionCleaner(noop=noop, verbose=verbosity > 1)

        @cleaner.ee.on("message")
        def handler(message):
            command.stdout.write(message)

        cleaner.run()

class Command(BaseCommand):
    help = "Management commands for the BTW database."
    args = "command"

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.subcommands = [MarkAllBibliographicalItemsStale, SetSiteName,
                            CreatePerms, Collect, CollapseChangeRecords,
                            CleanOldEntryVersions]

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(title="subcommands",
                                           dest="subcommand",
                                           parser_class=SubParser(self),
                                           required=True)

        for cmd in self.subcommands:
            cmd_instance = cmd()
            cmd_instance.add_to_parser(subparsers)

    def handle(self, *args, **options):
        options['subcommand'](self, options)
