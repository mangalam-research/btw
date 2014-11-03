import itertools
import os

from django.core.management.base import BaseCommand, CommandError
from django.utils.termcolors import colorize

from optparse import make_option

from lexicography.models import Entry, Chunk, ChangeRecord
from lexicography import xml

# This command is meant to be used for a one-shot move from HTML to
# XML as the "editable" format for articles. It should eventually be
# removed from the code base.


class Command(BaseCommand):
    args = 'dir'
    help = """\
Transforms all entries from the HTML format of earlier wed to XML.

dir The directory that contains the resulting logs, and the ``after.rng``
    file that validates files after conversion."""

    option_list = BaseCommand.option_list + (
        make_option('--noop',
                    action='store_true',
                    dest='noop',
                    default=False,
                    help='Do everything except perform the transformation'),
    )

    def handle(self, *args, **options):
        self.stdout.write(colorize("""
*****************************************************************************
WARNING: this operation is dangerous. Make sure that:

1. All users you are logged off and cannot log in.
2. You have backed up the database.

WARNING: this operation rewrites history.

WARNING: in general, this operation cannot be reliably undone without
    restoring from a backup.
*****************************************************************************

        """, fg='red'))

        if len(args) != 1:
            raise CommandError("One argument required.")

        mydir = args[0]
        log_dir = os.path.join(mydir, "log")
        after_rng = os.path.join(mydir, "after.rng")

        if not os.path.exists(after_rng):
            raise CommandError(after_rng + " does not exist.")

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        if os.listdir(log_dir):
            raise CommandError(log_dir + " is not empty.")

        # Make sure there are no active entry locks in the system.
        locked = Entry.objects.locked()
        if locked:
            self.stderr.write("These entries are locked:")
            self.stderr.write("\n".join([e.lemma for e in locked]))
            raise CommandError("Some entries are locked; aborting.")

        expected = 'Yes, I want to do this.'
        confirm = raw_input("Type '" + expected +
                            "' if you want to perform this operation.\n")

        if confirm != expected:
            self.stdout.write("Aborted operation.")
            return

        self.stdout.write("Garbage-collecting chunks.")
        Chunk.objects.collect()

        self.stdout.write("Transforming all entries.")
        chunk_mapping = {}
        count = Entry.objects.all().count() + \
            ChangeRecord.objects.all().count()
        item = 1
        for data in itertools.chain(Entry.objects.all(),
                                    ChangeRecord.objects.all()):
            print "Item {0} of {1}".format(item, count)
            chunk = data.c_hash
            if chunk.pk not in chunk_mapping:
                storage = xml.editable_to_storage(chunk.data)
                os.makedirs(os.path.join(log_dir, chunk.pk))
                with open(os.path.join(log_dir, chunk.pk, "before.html"), 'w') \
                        as before:
                    before.write(chunk.data.encode('utf-8'))

                new_chunk = Chunk()
                new_chunk.data = storage

                with open(os.path.join(log_dir, chunk.pk, "after.xml"), 'w') \
                        as after:
                    after.write(storage.encode('utf-8'))

                new_chunk.clean()  # Generate the pk
                chunk_mapping[chunk.pk] = new_chunk.pk

                if not options['noop']:
                    new_chunk.save()

            item += 1
            if not options['noop']:
                data.c_hash = Chunk.objects.get(pk=chunk_mapping[chunk.pk])
                data.save()

        self.stdout.write("Garbage-collecting chunks.")
        Chunk.objects.collect()
