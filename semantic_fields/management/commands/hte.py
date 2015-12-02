from __future__ import absolute_import

import os
import csv
import hashlib
import itertools
import random
import time
import datetime
import re
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from django.db import models, reset_queries, connection
from django.core import serializers
from django.conf import settings

from semantic_fields.models import SemanticField, Lexeme, SearchWord
from semantic_fields.util import ParsedExpression, _make_from_hte, \
    parse_local_reference, POS_CHOICES

def get_csv_reader(csv_file, expected_headers):
    reader = csv.reader(csv_file,
                        doublequote=False,
                        escapechar="\\",
                        strict=True)
    headers = next(reader)  # Skip headers.
    if headers != expected_headers:
        raise ValueError("headers differ from expected values")
    return reader

# md5sum is not used for security purposes. We're not worried about
# people trying to craft collisions.
def md5sum(path, blocksize=65536):
    hasher = hashlib.md5()

    with open(path, 'rb') as f:
        buf = f.read(blocksize)

        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(blocksize)

    return hasher.hexdigest()

def drop_duplicated_categories(row, header_to_csv_index):
    catid = int(row[header_to_csv_index["catid"]])

    # Arbitrarily remove records that have a duplicated set of
    # (t1...t7, subcat, pos). These were identified manually.
    return not ((catid >= 27190 and catid <= 27199) or
                catid in (54446, 54447))

categories_filters_by_md5 = {
    "91014f61180912f5c9319ebd21eb7002": [
        drop_duplicated_categories
    ]
}

#
# This is left here as a "here be dragons" warning. We've tried
# designing the loading code so that indexes would be turned off
# before the load and turned on afterwards. This should provide a
# speed improvement. Two attempts were made:
#
# 1. The code below reads the system tables and tries to turn off the
# indexes temporarily. It does not work because it would require
# `allow_system_table_mods = on`, which the PostgreSQL documentation
# says should not be turned on on production databases.
#
# 2. Use the sql_create_index, sql_destroy_indexes_for_model and
# associated methods from django.db.backends.creation. It looks like
# the problem here is that the index names created there do not seem
# to be the same as the index names created through a migration. In
# other words, when we try to destroy the indexes, we cannot find them
# because the indexes created have a different name.
#
#
# @contextlib.contextmanager
# @transaction.atomic
# def dropped_indexes(model):
#     from django.db import connections
#     from django.core.management.color import no_style

#     db = connections[model.objects.db]
#     c = db.create_cursor()
#     c.execute("""
# select
#     ix.indexrelid, ix.indisready, i.relname
# from
#     pg_class t,
#     pg_class i,
#     pg_index ix
# where
#     t.oid = ix.indrelid
#     and i.oid = ix.indexrelid
#     and t.relkind = 'r'
#     and t.relname = %s;
#     """, (model._meta.db_table, ))
#     rows = c.fetchall()
#     indexes = []
#     for r in rows:
# We cannot handle a case where indisready is false before we
# start toggling it. So fail immediately if we find it is the
# case.
#         if not r[1]:
#             raise ValueError("indisready is unexpectedly false for index {0}"
#                              .format(r[2]))
#         indexes.append(r[0])
#     try:
#         c = db.create_cursor()
#         try:
#             c.execute(
#                 "update pg_index set indisready = false where "
#                 "indexrelid = ANY(%s);",
#                 (indexes, ))
#         except Exception as ex:
#             print ex
#             raise
#         yield
#     finally:
#         c = db.create_cursor()
#         c.execute(
#             "update pg_index set indisready = true "
#             "where indexrelid = ANY(%s);",
#             (indexes, ))

class FieldConverter(object):
    frm = None
    to = None

    def __init__(self):
        self.to_idx = None
        self.frm_idx = None
        self.header_to_csv_index = None

    def setup(self, header_to_csv_index):
        # What we are doing here is finding the maximum index used and
        # setting the field we are converting to as an additional
        # field in the row. This modifies header_to_csv_index so that
        # we can then find the new field by field name.
        if self.to in header_to_csv_index:
            raise ValueError(("the field we are converting to ({0}) "
                              "already exists").format(self.to))

        if self.frm not in header_to_csv_index:
            raise ValueError(("the field we are converting from ({0})"
                              " is unknown").format(self.frm))

        max_idx = max(header_to_csv_index.values())
        self.to_idx = max_idx + 1
        self.frm_idx = header_to_csv_index[self.frm]
        self.header_to_csv_index = header_to_csv_index
        header_to_csv_index[self.to] = self.to_idx

    def convert(self, row):
        raise NotImplementedError("subclasses must implement this")


class SemanticFieldFieldConverter(FieldConverter):
    frm = "catid"
    to = "semantic_field"

    def __init__(self, catids):
        super(SemanticFieldFieldConverter, self).__init__()
        self.catids = catids

    def convert(self, row):
        # Extend the row if needed.
        diff = self.to_idx - (len(row) - 1)
        if diff > 0:
            row += [None] * diff

        row[self.to_idx] = self.catids[int(row[self.frm_idx])]


expected_category_headers = [
    "catid",
    "t1",
    "t2",
    "t3",
    "t4",
    "t5",
    "t6",
    "t7",
    "subcat",
    "pos",
    "heading",
    "tiering",
    "v1maincat",
    "mmcat",
    "themid"
]

def headers_to_map(headers):
    return {header: index for (index, header) in enumerate(headers)}

# This allows 2 digits numbers, zero-padded. Or 3-digit numbers but
# only if the 1st digit is not 0. 00 is disallowed.
step_re = re.compile("^0[1-9]|[1-9][0-9]|[1-9][0-9]{2}$")

# This allows 2 digit numbers, zero-padded. 00 is disallowed.
subcat_re = re.compile("^0[1-9]|[1-9][0-9]$")

POS_VALS = set(val for (val, _) in POS_CHOICES)

def using(point=""):
    with open("/proc/self/status") as f:
        for line in f:
            if line.startswith("VmSize:"):
                return line.strip()

class Command(BaseCommand):
    help = """\
Performs HTE commands on the database.

load: loads the HTE csv files into the database. This command is destructive.

extract-sfs: extracts all the semantic field numbers found in the database
"""
    args = "command"

    option_list = BaseCommand.option_list + (
        make_option('--skip-to',
                    default='category',
                    choices=('category', 'lexeme', 'lexeme_search_words'),
                    help='Skip to loading that csv file rather '
                         'than load all of them.'),
        make_option('--checks-only',
                    action="store_true",
                    default=False,
                    help='Only perform the checks. Does not load any data.'),
        make_option('--force-overwrite',
                    action="store_true",
                    default=False,
                    help='Force overwriting the database if the tables '
                    'already exist. Otherwise, the command will fail.'),
    )

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError("you must specify a command.")

        cmd = args[0]

        if cmd == "load":
            self.loadcmd(args, options)
        elif cmd == "fix":
            self.fix(args, options)
        elif cmd == "dump-subset":
            self.dump_subset(args, options)
        elif cmd == "timing-test":
            self.timing_test(args, options)
        elif cmd == "analyze":
            self.analyze()
        else:
            raise ValueError("unknown command: " + cmd)

    def loadcmd(self, args, options):
        directory = args[1]

        categories_path = os.path.join(directory, "category.csv")
        lexemes_path = os.path.join(directory, "lexeme.csv")
        search_path = os.path.join(directory, "lexeme_search_words.csv")

        categories_sum = md5sum(categories_path)
        categories_filters = categories_filters_by_md5.get(
            categories_sum, [])

        skip_to = options["skip_to"]
        checks_only = options["checks_only"]
        force_overwrite = options["force_overwrite"]

        self.stdout.write(using("before categories"))
        if any(model.objects.exists() for model in (
                SemanticField, Lexeme, SearchWord)) and not force_overwrite:
            raise CommandError("would overwrite tables; "
                               "use --force-overwrite to override")

        for model in SemanticField, Lexeme, SearchWord:
            model.objects.all().delete()

        skipped = False
        if not checks_only and skip_to == 'category':
            skipped = True

            truncations = \
                self.load_categories(categories_path, categories_filters)

            # What we are doing here is making sure that in all truncation
            # cases we will have something to truncate to. When we prepare
            # an article, we truncate some semantic fields to 3 levels
            # (t1, t2, t3) and give the truncation the "n" value for
            # "pos".
            for x in truncations:
                try:
                    SemanticField.objects.get(path=x)
                except SemanticField.DoesNotExist:
                    raise ValueError(("record {0} is missing; this will "
                                      "prevent truncation").format(x))

        using("before lexemes")
        if not checks_only and (skipped or skip_to == 'lexeme'):

            # We prefetch the catid values from the database instead of
            # checking them one by one.
            catids = {x["catid"]: x["id"] for x in
                      SemanticField.objects.filter(catid__isnull=False)
                      .values("id", "catid")}

            self.load(lexemes_path, Lexeme, [
                "htid",
                "catid",
                "word",
                "wordoe",
                "wordoed",
                "fulldate",
                "apps",
                "appe",
                "oe",
                "oefircon",
                "firstdac",
                "firstd",
                "firstdb",
                "firstdbr",
                "firmidcon",
                "firlastcon",
                "middac",
                "midd",
                "middb",
                "middbr",
                "midlascon",
                "lastdac",
                "lastd",
                "lastdb",
                "lastdbr",
                "current",
                "label",
                "roget",
                "catorder"
            ], [lambda row, header_to_csv_index:
                # We want only those rows for which we have a
                # catid. Filtering at the previous step could have
                # removed some catids from the database.
                (int(row[header_to_csv_index["catid"]]) in catids) and
                # And which are for "current" words.
                row[header_to_csv_index["current"]] == "_"],
                None,
                [SemanticFieldFieldConverter(catids)])
            skipped = True

        using("before searchwords")
        if not checks_only and (skipped or skip_to == 'lexeme_search_words'):

            # We prefetch the htid values from the database instead of
            # checking them one by one.
            htids = set(Lexeme.objects.all().values_list("htid", flat=True))

            self.load(search_path, SearchWord, [
                "sid",
                "htid",
                "searchword",
                "type"
            ], [lambda row, header_to_csv_index:
                # We want only those records that have a
                # corresponding Lexeme.
                (int(row[header_to_csv_index["htid"]]) in htids) and
                # Also some searchword fields are blank, which
                # does not seem meaningful to us.
                row[header_to_csv_index["searchword"]] != ""])
            skipped = True

    def fix(self, args, options):
        self.fix_parents()

    def dump_subset(self, args, options):
        with open(args[1]) as f:
            to_serialize = {}
            total_count = 0
            for sf in f:
                parsed = parse_local_reference(sf)
                total_count += 1
                cat = None
                try:
                    cat = SemanticField.objects.get(path=unicode(parsed))
                except SemanticField.DoesNotExist:
                    self.stderr.write("{0} did not exist".format(parsed))

                if cat:
                    to_serialize[cat.id] = cat

        if len(to_serialize) < total_count:
            self.stderr.write("found {0}% of the semantic fields"
                              .format(len(to_serialize) * 100 / total_count))
        parents = {}
        for cat in to_serialize.itervalues():
            parent = cat.parent
            while parent is not None:
                parents[parent.id] = parent
                parent = parent.parent

        to_serialize.update(parents)

        lexemes = Lexeme.objects.filter(
            semantic_field__in=to_serialize.keys())
        searchword = SearchWord.objects.filter(htid__in=lexemes)

        self.stdout.write(serializers.serialize("json",
                                                itertools.chain(
                                                    to_serialize.itervalues(),
                                                    lexemes,
                                                    searchword),
                                                use_natural_foreign_keys=True,
                                                use_natural_primary_keys=True,
                                                indent=2))

    def timing_test(self, args, options):
        # Generate random requests
        what = args[1]
        directory = args[2]

        categories_path = os.path.join(directory, "category.csv")
        categories_sum = md5sum(categories_path)
        categories_filters = categories_filters_by_md5.get(
            categories_sum, [])

        requests = []
        with open(categories_path) as csv_file:
            reader = get_csv_reader(csv_file, expected_category_headers)
            rows = list(reader)

            header_to_csv_index = headers_to_map(expected_category_headers)

            # This allows getting a set number of **different** random
            # rows. If randint produces the same row index more than
            # once, adding to the set does not increase the set's
            # length.
            row_indexes = set()
            while len(row_indexes) < 10000:

                candidate = random.randint(0, len(rows) - 1)
                row = rows[candidate]

                # Make sure we do not land on a row that was excluded
                # from the import.
                if any(not include(row, header_to_csv_index)
                       for include in categories_filters):
                    continue

                row_indexes.add(candidate)

            for index in row_indexes:
                row = rows[index]
                requests.append(str(_make_from_hte(
                    **{key: row[header_to_csv_index[key]]
                       for key in
                       ("t1", "t2", "t3", "t4", "t5", "t6", "t7",
                        "subcat", "pos")})))

        start = time.time()
        found = 0
        if what == "get":
            for request in requests:
                try:
                    SemanticField.objects.get(path=request)
                    found += 1
                except SemanticField.DoesNotExist:
                    self.stdout.write("cannot find: " + request)
                    pass
        elif what == "children":
            found = 0
            for request in requests:
                try:
                    node = SemanticField.objects.get(path=request)
                    found += 1
                except SemanticField.DoesNotExist:
                    self.stdout.write("cannot find: " + request)
                    node = None
                if node:
                    list(node.children.all())
        self.stdout.write("elapsed time: {0}"
                          .format(str(datetime.timedelta(
                              seconds=time.time() - start))))
        self.stdout.write("{0} hits out of {1} requests"
                          .format(found, len(requests)))

    def load_categories(self, path, include_filters):
        header_to_csv_index = headers_to_map(expected_category_headers)

        truncations = set()
        with open(path) as csv_file:
            reader = get_csv_reader(csv_file, expected_category_headers)

            count = 0
            records = []
            failures = []

            def insert():
                if not failures:
                    SemanticField.objects.bulk_create(records)
                # In DEBUG mode Django will record all queries made to
                # the database, which can easily use all memory. Don't
                # prevent DEBUG=True but flush the queries periodically.
                if settings.DEBUG:
                    reset_queries()
                del records[:]

            for row in reader:
                count += 1
                # Check whether we include this row.
                if any(not include(row, header_to_csv_index)
                       for include in include_filters):
                    continue

                self.process_category_row(row, header_to_csv_index,
                                          records, truncations, failures)

                if len(records) >= 1000:
                    insert()

                if len(failures) > 20:
                    # Stop after that many failures. If we get so
                    # many failures, the problem is probably
                    # systematic. We may run out of memory trying
                    # to record all of them.
                    break

                if count % 1000 == 0:
                    self.stdout.write(
                        "processed {0} rows".format(count))
                    self.stdout.write(using())

            # Don't forget the remnants.
            if records:
                insert()

            if not failures:
                self.fix_parents()

            if failures:
                for failure in failures:
                    self.stderr.write(
                        "failed to validate row: {0}".format(failure[0]))
                    self.stderr.write("{0}".format(failure[1]))

                self.stderr.write("validation failed: deleting table")
                SemanticField.objects.all().delete()
                raise CommandError(
                    "loading {0} failed: stopping".format(path))

        return truncations

    def fix_parents(self):
        values = SemanticField.objects.values("path", "id")
        path_to_id_cache = {d["path"]: d["id"] for d in values}

        def find_parent(path):
            parsed = ParsedExpression(path)

            ret = None
            while True:
                parent_path = parsed.parent()

                if parent_path is None:
                    break  # No parent.

                parent_path_str = unicode(parent_path)
                parent = path_to_id_cache.get(parent_path_str, None)
                if parent is not None:
                    ret = parent
                    break  # Found the parent.

                # Move up to check the parent.
                parsed = parent_path

            return ret

        id_to_parent = {id: find_parent(path)
                        for (path, id) in path_to_id_cache.iteritems()}

        count = 0
        # We now need to link up the records to their parent nodes.
        with connection.cursor() as cursor:
            for (id, parent) in id_to_parent.iteritems():
                count += 1
                if parent is not None:
                    cursor.execute("UPDATE semantic_fields_semanticfield "
                                   "SET parent_id = %s WHERE id = %s",
                                   [parent, id])

                if count % 1000 == 0:
                    # In DEBUG mode Django will record all queries made to
                    # the database, which can easily use all memory. Don't
                    # prevent DEBUG=True but flush the queries periodically.
                    if settings.DEBUG:
                        reset_queries()
                    self.stdout.write("set parents of {0} records"
                                      .format(count))
                    self.stdout.write(using())

    def process_category_row(self, row, header_to_csv_index, records,
                             truncations, failures):
        steps = ("t1", "t2", "t3", "t4", "t5", "t6", "t7")
        values = [row[header_to_csv_index[step]] for step in steps]

        try:
            first_blank = values.index('')
        except ValueError:
            first_blank = len(values)

        if any(x != '' for x in values[first_blank:]):
            raise ValueError("row contains a sequence of t1-t7 which "
                             "has a non-empty value after an empty "
                             "one: {0}".format(row))
        try:
            last = None
            for value in values[0:first_blank]:
                if not step_re.match(value):
                    raise ValueError("unexpected step value in {0}"
                                     .format(row))

            path = ".".join(values[0:first_blank])

            if first_blank > 3:
                # Pos is always "n" on truncations.
                truncations.add(".".join(values[0:3]) + "n")

            subcat = row[header_to_csv_index["subcat"]]
            subcat = subcat.strip()
            if subcat != '':
                parts = subcat.split(".")
                for part in parts:
                    if not subcat_re.match(part):
                        raise ValueError(
                            "unexpected subcat part value in {0}"
                            .format(row))
                path += "|" + subcat

            pos = row[header_to_csv_index["pos"]]
            if pos not in POS_VALS:
                raise ValueError("pos not among expected values: {0}"
                                 .format(row))
            path += pos
            last = SemanticField(
                path=path,
                heading=row[header_to_csv_index["heading"]],
                catid=row[header_to_csv_index["catid"]])
            last.full_clean()

            records.append(last)
        except ValidationError as ex:
            failures.append((row, ex))

    def load(self, path, model, expected_headers, include_filters=None,
             supplied_model_fields=None, convert_fields=None):
        """
        Loads a CSV file and stores the result in the database.

        :param path: The path to the file.
        :param model: The Django model into which to store the data.
        :param expected_headers: A list of headers we expect to find
        in the CSV file.
        :param include_filters: A list of functions called with each
        row read from the CSV file. The functions will be called with
        the row data as the first argument, and a map of CSV header
        names to indexes in the row data. A function returning
        ``True`` means that the row should be included into the
        database. If any function in the list returns ``False``, the
        row won't be included.
        :param supplied_model_fields: A dictionary of fields names for
        which to supply default values. Keys are the field names,
        values are the values to assign. These are fields that do not
        have an equivalent in the CSV file.
        :param convert_fields: A list of FieldConverter instances.

        """
        field_name_to_csv_index = {}
        used_fields = []
        foreign_key_fields = set()
        if include_filters is not None or convert_fields is not None:
            header_to_csv_index = headers_to_map(expected_headers)
        else:
            header_to_csv_index = {}

        if convert_fields:
            for converter in convert_fields:
                converter.setup(header_to_csv_index)

        for field in model._meta.local_fields:
            # An autofield is not filled by us.
            if isinstance(field, models.AutoField):
                continue

            field_name = field.name

            if supplied_model_fields and \
               field_name in supplied_model_fields:
                continue

            index = header_to_csv_index.get(field_name, None)

            if index is None:
                raise ValueError(
                    "{0} is not a known field".format(field_name))

            # If the field is a foreign key, then we need to use the
            # "_id" version of the field name when constructing the
            # instance.
            if isinstance(field, models.ForeignKey):
                field_name += "_id"
                foreign_key_fields.add(field_name)

            field_name_to_csv_index[field_name] = index
            used_fields.append(field_name)

        with open(path) as csv_file:
            reader = get_csv_reader(csv_file, expected_headers)

            count = 0
            records = []
            failures = []

            def insert():
                if not failures:
                    model.objects.bulk_create(records)
                # In DEBUG mode Django will record all queries made to
                # the database, which can easily use all memory. Don't
                # prevent DEBUG=True but flush the queries periodically.
                if settings.DEBUG:
                    reset_queries()
                del records[:]
                self.stdout.write("processed: {0}".format(count))

            def convert(row, field):
                value = row[field_name_to_csv_index[field]]
                if field not in foreign_key_fields:
                    return unicode(value, 'utf8')
                else:
                    return int(value)

            for row in reader:
                # Check whether we include this row.
                if include_filters is not None and \
                   any(not include(row, header_to_csv_index)
                       for include in include_filters):
                    continue

                # Apply all the converters to the row.
                if convert_fields:
                    for converter in convert_fields:
                        converter.convert(row)

                model_dict = {field: convert(row, field) for field in
                              used_fields}
                if supplied_model_fields:
                    model_dict.update(supplied_model_fields)
                record = model(**model_dict)
                try:
                    record.full_clean()
                except ValidationError as ex:
                    failures.append((row, ex))
                    if len(failures) > 20:
                        # Stop after that many failures. If we get so
                        # many failures, the problem is probably
                        # systematic. We may run out of memory trying
                        # to record all of them.
                        break
                else:
                    records.append(record)

                count += 1
                if count % 1000 == 0:
                    insert()

            # Don't forget to insert the leftovers...
            if records:
                insert()

            if failures:
                for failure in failures:
                    self.stderr.write(
                        "failed to validate row: {0}".format(failure[0]))
                    self.stderr.write("{0}".format(failure[1]))

                self.stderr.write("validation failed: deleting table")
                model.objects.all().delete()
                raise CommandError(
                    "loading {0} failed: stopping".format(path))

    def analyze(self):
        pos_re = re.compile("[a-z]+$")
        paths = set(SemanticField.objects.all().values_list("path",
                                                            flat=True))

        total = len(paths)
        subcats = 0
        total_missing = 0
        for path in paths:
            as_noun = pos_re.sub("n", path)
            if as_noun not in paths:
                total_missing += 1
                # self.stdout
                # .write("{0} has no noun equivalent".format(path))
                cat = SemanticField.objects.get(path=path)
                if cat.is_subcat:
                    subcats += 1

        self.stdout.write("{0} fields total".format(total))
        self.stdout.write("{0} fields have no noun equivalent"
                          .format(total_missing))
        self.stdout.write("{0} of them are subcategories".format(subcats))
