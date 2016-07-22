from __future__ import absolute_import

import os

from django.core.management.base import BaseCommand, CommandError
from django.utils.termcolors import colorize

from optparse import make_option

from lexicography.models import Entry, Chunk, ChangeRecord
from lexicography import xml
from lib import util


class Command(BaseCommand):
    args = 'dir'
    help = """\
Perform an XSLT transformation on all entries.

dir The directory that contains the files that drive the
       transformation, and the resulting logs. The XSLT transformation
       must be in a file named ``transform.xsl``. The schema to
       validate after must be in a file named ``after.rng``. The
       transformations are logged into the ``log`` subdirectory.
"""

    option_list = BaseCommand.option_list + (
        make_option('--noop',
                    action='store_true',
                    dest='noop',
                    default=False,
                    help='Do everything except performing the transformation'),
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
        xsl_path = os.path.join(mydir, "transform.xsl")
        after_rng = os.path.join(mydir, "after.rng")
        log_dir = os.path.join(mydir, "log")

        if not os.path.exists(xsl_path):
            raise CommandError(xsl_path + " does not exist.")

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
        for data in ChangeRecord.objects.all():
            initially_invalid = False

            chunk = data.c_hash
            if chunk.pk not in chunk_mapping:
                os.makedirs(os.path.join(log_dir, chunk.pk))
                with open(os.path.join(log_dir, chunk.pk, "before.xml"), 'w') \
                        as before:
                    before.write(chunk.data.encode('utf-8'))

                if chunk.is_normal:
                    if chunk.schema_version == "":
                        self.stdout.write("Correcting lack of version")
                        chunk.schema_version = \
                            xml.XMLTree(chunk.data.encode('utf-8')) \
                               .extract_version()

                    if not chunk.valid:
                        initially_invalid = True

                    # We do not use lxml for this because lxml only
                    # supports xslt 1.0 and we want to be able to run
                    # 2.0 transforms.
                    converted = util.run_saxon(xsl_path, chunk.data)
                    new_chunk = Chunk()
                    new_chunk.data = converted
                    new_chunk.schema_version = \
                        xml.XMLTree(
                            converted.encode('utf-8')).extract_version()
                    new_chunk._valid = util.validate_with_rng(after_rng,
                                                              converted)
                else:
                    # Abnormal chunk. We won't try to validate and convert.
                    initially_invalid = True
                    converted = chunk.data
                    new_chunk = chunk

                with open(os.path.join(log_dir, chunk.pk, "after.xml"), 'w') \
                        as after:
                    after.write(converted.encode('utf-8'))

                new_chunk.clean()  # Generate the pk
                chunk_mapping[chunk.pk] = new_chunk.pk

                if not initially_invalid and not new_chunk.valid:
                    with open(os.path.join(log_dir, chunk.pk,
                                           "BECAME_INVALID"), 'w'):
                        pass

                if not options['noop']:
                    new_chunk.save()

            if not options['noop']:
                data.c_hash = Chunk.objects.get(pk=chunk_mapping[chunk.pk])
                data.save()

        self.stdout.write("Garbage-collecting chunks.")
        Chunk.objects.collect()
