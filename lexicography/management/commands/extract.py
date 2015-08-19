from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from lexicography.models import Entry
from lexicography.xml import XMLTree, default_namespace_mapping

class Command(BaseCommand):
    help = """\
Extracts information from the articles in the database. A subcommand must
indicate that is to be extracted.

sfs: extracts all the semantic field numbers found in the database
"""
    args = "command"

    option_list = BaseCommand.option_list + (
        make_option('--only',
                    action='store',
                    dest='only',
                    default=False,
                    choices=('published', 'latest-published'),
                    help='Narrow the set of changerecord processed.'),
        make_option('--lemmas',
                    action='store_true',
                    dest='lemmas',
                    default=False,
                    help='Output the lemma with the semantic field.'),
    )

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("you must specify a command.")

        cmd = args[0]

        if cmd == "sfs":
            self.extract_sfs(args, options)
        else:
            raise ValueError("unknown command: " + cmd)

    def extract_sfs(self, args, options):
        only = options["only"]
        output_lemmas = options["lemmas"]

        hashes_done = set()
        extracted = {}
        entries = Entry.objects.active_entries()
        if not only:
            pass
        elif only in ("published", "latest-published"):
            entries = entries.filter(latest_published__isnull=False)
        else:
            raise ValueError("cannot handle --only with value: " + only)

        for entry in entries.prefetch_related('changerecord_set') \
                            .prefetch_related('changerecord_set__c_hash'):
            if not only:
                crs = entry.changerecord_set.all()
            elif only == "published":
                crs = entry.changerecord_set.filter(published=True)
            elif only == "latest-published":
                crs = [entry.latest_published]
            else:
                raise ValueError("cannot handle --only with value: " + only)

            for cr in crs:
                # It is in theory possible to get the same hash twice.
                if cr.c_hash.c_hash in hashes_done:
                    continue

                if not cr.c_hash.is_normal:
                    continue

                tree = XMLTree(cr.c_hash.data.encode("utf8"))
                sfs = tree.tree.xpath("//btw:sf",
                                      namespaces=default_namespace_mapping)
                for sf in sfs:
                    if sf.text:
                        sf = ' '.join(sf.text.strip().split())
                        if sf:
                            extracted.setdefault(sf, []).append(cr.lemma)
                hashes_done.add(cr.c_hash.c_hash)

        for sf in extracted:
            lemmas = extracted[sf]
            if output_lemmas:
                print "{0}: {1}" \
                    .format(sf.encode('utf8'),
                            [l.encode('utf8') for l in lemmas])
            else:
                print sf.encode('utf8')
