

from django.core.management.base import BaseCommand, CommandError
from pyexistdb.db import ExistDB

from lexicography.models import Entry
from lexicography.xml import XMLTree, default_namespace_mapping
from lib import existdb
from lib import xquery

class Command(BaseCommand):
    help = """\
Extracts information from the articles in the database. A subcommand must
indicate that is to be extracted.

sfs: extracts all the semantic field numbers found in the database
"""
    args = "command"

    def add_arguments(self, parser):
        parser.add_argument("command")
        parser.add_argument('--only',
                            action='store',
                            dest='only',
                            default=False,
                            choices=('published', 'latest-published'),
                            help='Narrow the set of changerecord processed.')
        parser.add_argument('--lemmas',
                            action='store_true',
                            dest='lemmas',
                            default=False,
                            help='Output the lemma with the semantic field.')

    def handle(self, *args, **options):
        cmd = options["command"]

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

        hashes = set()

        use_lxml = True

        for entry in entries.prefetch_related('changerecord_set__c_hash',
                                              'latest_published__c_hash'):
            if not only:
                crs = entry.changerecord_set.all()
            elif only == "published":
                crs = entry.changerecord_set.filter(published=True)
            elif only == "latest-published":
                crs = [entry.latest_published]
            else:
                raise ValueError("cannot handle --only with value: " + only)

            if use_lxml:
                for cr in crs:
                    # It is in theory possible to get the same hash twice.
                    if cr.c_hash.c_hash in hashes_done:
                        continue

                    if not cr.c_hash.is_normal or not cr.c_hash.valid:
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

            else:
                hashes.update(
                    cr.c_hash.c_hash for cr in crs
                    if cr.c_hash.is_normal and cr.c_hash.valid)

        if use_lxml:
            for sf in extracted:
                if output_lemmas:
                    lemmas = extracted[sf]
                    print("{0}: {1}"
                          .format(sf.encode('utf8'),
                                  [l.encode('utf8') for l in lemmas]))
                else:
                    print(sf.encode('utf8'))
        else:
            db = ExistDB()

            for query in existdb.query_iterator(db, xquery.make(
                    ("for $x in distinct-values(({0})//btw:sf/text()) "
                     "return $x")
                    .format(",".join(["doc('/btw/{0}')".format(hash)
                                      for hash in hashes])))):
                for result in query.values:
                    print(result)
