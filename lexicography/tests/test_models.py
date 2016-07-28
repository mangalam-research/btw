import os
import datetime
import mock

from django.test import TransactionTestCase, TestCase
from django.test.utils import override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.cache import caches
from django.utils import translation
from django.db import connection
import lxml.etree

from ..models import Entry, ChangeRecord, PublicationChange, Chunk
from .. import locking, xml, models
from .test_xml import as_editable
import lib.util as util
from lib.existdb import ExistDB
from lib.existdb import get_collection_path, list_collection
from lib.testutil import wipd
from bibliography.tests import mock_zotero
from bibliography.models import Item, PrimarySource
from semantic_fields.models import SemanticField

cache = caches['article_display']

mock_records = mock_zotero.Records([
    {
        "data":
        {
            "key": "1",
            "title": "Title 1",
            "date": "Date 1",
            "creators": [
                {"name": "Abelard (Name 1 for Title 1)"},
                {"firstName": "FirstName 2 for Title 1",
                 "lastName": "LastName 2 for Title 1"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "2",
            "title": "Title 2",
            "date": "Date 2",
            "creators": [
                {"name": "Beth (Name 1 for Title 2)"},
                {"firstName": "FirstName 2 for Title 2",
                 "lastName": "LastName 2 for Title 2"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo2.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "3",
            "title": "Title 3",
            "date": "Date 3",
            "creators": [
                {"name": "Zeno (Name 1 for Title 3)"},
                {"firstName": "FirstName 2 for Title 3",
                 "lastName": "LastName 2 for Title 3"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo3.com",
                "type": "text/html"
            }
        }
    }
])

get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json"))

user_model = get_user_model()

# Disable warnings about accessing protected members.
# pylint: disable=W0212

valid_editable = as_editable(os.path.join(xml.schemas_dirname, "prasada.xml"))
xmltree = xml.XMLTree(valid_editable)
schema_version = xmltree.extract_version()

class EntryTestCase(util.DisableMigrationsTransactionMixin,
                    TransactionTestCase):

    fixtures = local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")
        self.entry = Entry.objects.get(id=1)

    def test_dependency_key(self):
        """
        Tests that the dependency key is properly generated.
        """
        self.assertEqual(self.entry.dependency_key, "abcd")

    def test_is_locked_returns_none(self):
        """
        Tests that Entry.is_locked returns None when the entry is not
        locked.
        """
        self.assertIsNone(self.entry.is_locked())

    def test_is_locked_returns_user(self):
        """
        Tests that Entry.is_locked returns the user who owns the lock.
        """
        locking.try_acquiring_lock(self.entry, self.foo)
        user = self.entry.is_locked()
        self.assertEqual(user.id, self.foo.id)

    def test_is_locked_expired(self):
        """
        Tests that Entry.is_locked returns None on an expired lock.
        """
        lock = locking.try_acquiring_lock(self.entry, self.foo)
        lock._force_expiry()
        self.assertIsNone(self.entry.is_locked())

    def test_is_editable_by_no_lock(self):
        """
        Tests that Entry.is_editable_by(X) returns True when there is no lock.
        """
        self.assertTrue(self.entry.is_editable_by(self.foo))

    def test_is_editable_by_superuser(self):
        """
        Tests that Entry.is_editable_by(X) returns True when X is a superuser.
        """
        newuser = user_model()
        newuser.username = "super"
        newuser.is_superuser = True
        newuser.save()
        self.assertTrue(self.entry.is_editable_by(newuser))

    def test_is_editable_non_author(self):
        """
        Tests that Entry.is_editable_by(X) returns False when the user
        does not have the right permissions.
        """
        newuser = user_model()
        newuser.username = "new"
        newuser.save()
        self.assertFalse(self.entry.is_editable_by(newuser))

    def test_is_editable_by_locked_by_same(self):
        """
        Tests that Entry.is_editable_by(X) returns True when locked by X.
        """
        locking.try_acquiring_lock(self.entry, self.foo)
        self.assertTrue(self.entry.is_editable_by(self.foo))

    def test_is_editable_by_locked_by_other_but_expired(self):
        """
        Tests that Entry.is_editable_by(X) returns True when locked by Y
        but the lock is expired.
        """
        lock = locking.try_acquiring_lock(self.entry, self.foo)
        lock._force_expiry()
        self.assertTrue(self.entry.is_editable_by(self.foo2))

    def test_is_editable_by_locked_by_other(self):
        """
        Tests that Entry.is_editable_by(X) returns False when locked by Y.
        """
        locking.try_acquiring_lock(self.entry, self.foo)
        self.assertFalse(self.entry.is_editable_by(self.foo2))

    def test_active_entries(self):
        """
        """
        original_count = Entry.objects.active_entries().count()
        # We change one record to be deleted. This is not how it
        # happens in the real application but for our purpose here
        # this is fine.
        self.entry.deleted = True
        self.entry.save()
        self.assertEqual(Entry.objects.active_entries().count(),
                         original_count - 1)

    def test_update(self):
        """
        The update method creates a new ChangeRecord.
        """
        entry = self.entry
        original_change_record_count = entry.changerecord_set.count()
        old_latest = entry.latest
        entry.update(
            self.foo,
            "q",
            old_latest.c_hash,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        self.assertEqual(entry.changerecord_set.count(),
                         original_change_record_count + 1,
                         "There should be one additional change record.")
        latest = entry.latest
        self.assertEqual(latest.entry, entry)
        self.assertEqual(latest.user, self.foo)
        self.assertEqual(latest.session, "q")
        self.assertEqual(latest.c_hash, old_latest.c_hash)
        self.assertEqual(latest.lemma, old_latest.lemma)
        self.assertEqual(latest.ctype, ChangeRecord.UPDATE)
        self.assertEqual(latest.csubtype, ChangeRecord.MANUAL)
        self.assertFalse(latest.published)
        self.assertNotEqual(latest, old_latest)

    def test_update_on_new_entry(self):
        entry = Entry()
        self.assertEqual(entry.changerecord_set.count(), 0,
                         "There should not be any change records yet.")
        entry.update(
            self.foo,
            "q",
            self.entry.latest.c_hash,
            self.entry.lemma + " copy",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        self.assertEqual(entry.changerecord_set.count(), 1,
                         "There should be one additional change record.")
        latest = entry.latest
        self.assertEqual(latest.entry, entry)
        self.assertEqual(latest.user, self.foo)
        self.assertEqual(latest.session, "q")
        self.assertEqual(latest.c_hash, self.entry.latest.c_hash)
        self.assertEqual(latest.lemma, entry.lemma)
        self.assertEqual(latest.ctype, ChangeRecord.CREATE)
        self.assertEqual(latest.csubtype, ChangeRecord.MANUAL)
        self.assertFalse(latest.published)

    def test_schema_version(self):
        """
        Test that the schema_version property returns the schema_version
        of the latest version of an entry.
        """
        self.assertEqual(self.entry.schema_version,
                         self.entry.latest.c_hash.schema_version)

        # Make sure we are actually changing the version number!
        self.assertNotEqual(self.entry.schema_version, "0.0")

        c = Chunk(data=valid_editable.decode('utf-8'),
                  schema_version="0.0")
        c.save()
        self.entry.update(
            self.foo,
            "q",
            c,
            self.entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        self.assertEqual(self.entry.schema_version, "0.0")


class ChangeRecordTestCase(util.DisableMigrationsTransactionMixin,
                           TransactionTestCase):
    fixtures = local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")
        self.noperm = user_model.objects.get(username="noperm")
        self.entry = Entry.objects.get(id=1)
        c = Chunk(data=valid_editable.decode('utf-8'),
                  schema_version=schema_version)
        c.save()
        self.valid = Entry()
        self.valid.update(self.foo,
                          "q",
                          c,
                          "foo2",
                          ChangeRecord.CREATE,
                          ChangeRecord.MANUAL)

    def test_publish_new(self):
        """
        Publishing the latest change record updates the latest_published
        field.
        """
        entry = self.valid
        old_latest = entry.latest
        entry.update(
            self.foo,
            "q",
            old_latest.c_hash,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        latest = entry.latest
        self.assertTrue(latest.publish(self.foo))
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         latest)

    def test_publish_old(self):
        """
        Publishing an old change record updates the latest_published
        field.
        """
        entry = self.valid
        old_latest = entry.latest
        entry.update(
            self.foo,
            "q",
            old_latest.c_hash,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        self.assertTrue(old_latest.publish(self.foo))
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         old_latest)

    def test_unpublish_nothing_left(self):
        """
        Unpublishing the only change that was published sets
        latest_published to None.
        """
        entry = self.valid
        latest = entry.latest
        self.assertTrue(latest.publish(self.foo))
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         latest)
        self.assertTrue(latest.unpublish(self.foo))
        self.assertIsNone(Entry.objects.get(id=entry.id).latest_published)

    def test_unpublish_newest(self):
        """
        Unpublishing the newest published version updates latest_published to
        the previous published version.
        """
        entry = self.valid
        old_latest = entry.latest
        entry.update(
            self.foo,
            "q",
            old_latest.c_hash,
            entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        latest = entry.latest
        self.assertTrue(old_latest.publish(self.foo))
        self.assertTrue(latest.publish(self.foo))
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         latest)
        self.assertTrue(latest.unpublish(self.foo))
        self.assertEqual(Entry.objects.get(id=entry.id).latest_published,
                         old_latest)

    def test_publish_creates_publication_change(self):
        """
        Publishing a change record creates a new PublicationChange.
        """
        entry = self.valid
        latest = entry.latest
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        self.assertFalse(latest.published,
                         "The change record we are about to use must not be "
                         "published yet.")
        self.assertTrue(latest.publish(self.foo))
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count + 1)
        latest_pc = PublicationChange.objects.latest('datetime')
        self.assertEqual(latest_pc.changerecord, latest)
        self.assertEqual(latest_pc.ctype, PublicationChange.PUBLISH)
        self.assertEqual(latest_pc.user, self.foo)
        # The timedelta is arbitrary.
        self.assertTrue(util.utcnow() -
                        latest_pc.datetime <= datetime.timedelta(seconds=5))

    def test_republish_is_a_noop(self):
        """
        Republishing a change record (when it is already published) does
        not create a new PublicationChange.
        """
        entry = self.valid
        latest = entry.latest
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        self.assertFalse(latest.published,
                         "The change record we are about to use must not be "
                         "published yet.")
        self.assertTrue(latest.publish(self.foo))
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count + 1)
        self.assertFalse(latest.publish(self.foo),
                         "the return value should be False, indicating a noop")
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count + 1, "the count should not have changed")

    def test_unpublish_creates_publication_change(self):
        """
        Unpublishing a change record creates a new PublicationChange.
        """
        entry = self.valid
        latest = entry.latest
        self.assertTrue(latest.publish(self.foo))
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        self.assertTrue(latest.unpublish(self.foo))
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count + 1)
        latest_pc = PublicationChange.objects.latest('datetime')
        self.assertEqual(latest_pc.changerecord, latest)
        self.assertEqual(latest_pc.ctype, PublicationChange.UNPUBLISH)
        self.assertEqual(latest_pc.user, self.foo)
        # The timedelta is arbitrary.
        self.assertTrue(util.utcnow() -
                        latest_pc.datetime <= datetime.timedelta(seconds=5))

    def test_unpublish_again_is_a_noop(self):
        """
        Unpublishing a change record again (when it is still unpublished)
        does not creates a new PublicationChange.
        """
        entry = self.valid
        latest = entry.latest
        self.assertTrue(latest.publish(self.foo))
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        self.assertTrue(latest.unpublish(self.foo))
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count + 1)
        self.assertFalse(latest.unpublish(self.foo),
                         "the return value should be False, indicating a noop")
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count + 1, "the count should not have changed")

    def test_publish_invalid_is_a_noop(self):
        """
        Publishing a change record that encode an invalid state of an
        article is a noop.
        """
        entry = self.entry
        latest = entry.latest
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        self.assertFalse(latest.publish(self.foo))
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count)

    def test_publish_without_permission_raises_permission_denied(self):
        """
        Trying to publish without the necessary permissions results in a
        ``PermissionDenied`` exception and does not create a new
        ``PublicationChange``.
        """
        entry = self.valid
        latest = entry.latest
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        with self.assertRaises(PermissionDenied):
            latest.publish(self.noperm)
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count)

    def test_unpublishing_without_permission_raises_permission_denied(self):
        """
        Trying to unpublish without the necessary permissions results in a
        ``PermissionDenied`` exception and does not create a new
        ``PublicationChange``.
        """
        entry = self.valid
        latest = entry.latest
        latest.publish(self.foo)
        old_count = PublicationChange.objects.filter(
            changerecord=latest).count()
        with self.assertRaises(PermissionDenied):
            latest.unpublish(self.noperm)
        self.assertEqual(
            PublicationChange.objects.filter(changerecord=latest).count(),
            old_count)

    def test_schema_version(self):
        """
        Test that the schema_version property returns the schema_version
        of the version of the change record.
        """
        self.assertEqual(self.entry.latest.schema_version,
                         self.entry.latest.c_hash.schema_version)

        # Make sure we are actually changing the version number!
        self.assertNotEqual(self.entry.latest.schema_version, "0.0")

        c = Chunk(data=valid_editable.decode('utf-8'),
                  schema_version="0.0")
        c.save()
        self.entry.update(
            self.foo,
            "q",
            c,
            self.entry.lemma,
            ChangeRecord.UPDATE,
            ChangeRecord.MANUAL)
        self.assertEqual(self.entry.latest.schema_version, "0.0")

class EntryLockTestCase(util.DisableMigrationsTransactionMixin,
                        TransactionTestCase):
    fixtures = local_fixtures

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")

    def test_expirable_expired(self):
        entry = Entry.objects.get(id=1)
        lock = locking.try_acquiring_lock(entry, self.foo)
        lock._force_expiry()
        self.assertTrue(lock.expirable)


@mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                     get_item=get_item_mock)
@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_ALWAYS_EAGER_PROPAGATES_EXCEPTIONS=True,
                   BROKER_BACKEND='memory',
                   ROOT_URLCONF='lexicography.tests.urls')
class ChunkManagerTestCase(util.DisableMigrationsMixin, TestCase):
    fixtures = local_fixtures

    @classmethod
    def setUpTestData(cls):
        super(ChunkManagerTestCase, cls).setUpTestData()
        translation.activate('en-us')
        item = Item(pk=1, item_key="3",
                    uid=Item.objects.zotero.full_uid)
        item.save()

        ps = PrimarySource(pk=1,
                           item=item,
                           reference_title="Foo",
                           genre="SU")
        ps.save()

        item = Item(pk=2, item_key="1",
                    uid=Item.objects.zotero.full_uid)
        item.save()

        sf = SemanticField(path="01.05n",
                           heading="foo")
        sf.save()
        Chunk.objects.prepare("xml", True)

    def setUp(self):
        self.manager = Chunk.objects
        super(ChunkManagerTestCase, self).setUp()

    def test_hashes_with_semantic_field_no_match(self):
        """
        Returns an empty set if nothing matches.
        """
        self.assertEqual(len(self.manager.hashes_with_semantic_field("99n")),
                         0)

    def test_hashes_with_semantic_field_all(self):
        """
        Returns a match when something matches.
        """
        self.assertEqual(
            len(self.manager.hashes_with_semantic_field("01.05n")), 1)

# We separate this test from the other manager tests because they have
# different initialization needs.
@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_ALWAYS_EAGER_PROPAGATES_EXCEPTIONS=True,
                   BROKER_BACKEND='memory')
class ChunkManagerSimpleTestCase(util.DisableMigrationsMixin, TestCase):
    chunk_collection_path = get_collection_path("chunks")
    display_collection_path = get_collection_path("display")

    @classmethod
    def setUpTestData(cls):
        super(ChunkManagerSimpleTestCase, cls).setUpTestData()
        cls.foo = user_model.objects.create(username="foo", password="foo")

    def setUp(self):
        self.manager = Chunk.objects
        return super(ChunkManagerSimpleTestCase, self).setUp()

    def make_reachable(self, chunk):
        # Make the chunk reachable
        e = Entry()
        e.update(
            self.foo,
            "q",
            chunk,
            "foo",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        return e

    def list_chunk_collection(self):
        db = ExistDB()
        return list_collection(db, self.chunk_collection_path)

    def list_display_collection(self):
        db = ExistDB()
        return list_collection(db, self.chunk_collection_path)

    def check_collects(self, op, *args):
        self.assertEqual(self.manager.count(), 0)
        c = Chunk(data="", is_normal=False)
        c.save()
        self.assertEqual(self.manager.count(), 1)
        getattr(self.manager, op)(*args)
        self.assertEqual(self.manager.count(), 0)

    def test_collect_collects_unreachable(self):
        """
        ``collect`` collects unreachable chunks.
        """
        self.check_collects("collect")

    def test_collect_does_not_collect_reachable(self):
        """
        Does not collect reachable chunks.
        """
        self.assertEqual(self.manager.count(), 0)
        c = Chunk(data="", is_normal=False)
        c.save()

        self.make_reachable(c)
        self.assertEqual(self.manager.count(), 1)

        self.manager.collect()
        # Not collected!
        self.assertEqual(self.manager.count(), 1)

    def test_sync_collects(self):
        """
        ``sync_with_exist`` causes a collection of unreachable chunks.
        """
        self.check_collects("sync_with_exist")

    def check_skip_abnormal_chunks(self, op, collection, *args):
        c = Chunk(data="", is_normal=False)
        c.save()
        self.make_reachable(c)
        db = ExistDB()
        self.assertEqual(len(list_collection(db, collection)), 0)

        getattr(self.manager, op)(*args)

        self.assertEqual(len(list_collection(db, collection)), 0)

        # Make sure our chunk was not collected.
        self.assertEqual(self.manager.count(), 1)

    def check_syncs_normal_chunks(self, op, collection, *args):
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        self.make_reachable(c)
        c.chunkmetadata.delete()

        # We have to delete the collection because merely saving the
        # chunk causes it to be synced, but this is not what we are
        # testing here. We want to make sure that calling
        # sync_with_exist will perform the sync.
        db = ExistDB()
        db.removeCollection(collection, True)
        self.assertEqual(len(list_collection(db, collection)), 0)

        getattr(self.manager, op)(*args)

        self.assertEqual(len(list_collection(db, collection)), 1)

        # Make sure our chunk was not collected.
        self.assertEqual(self.manager.count(), 1)

    def test_sync_skips_abnormal_chunks(self):
        """
        ``sync_with_exist`` does not sync abnormal chunks.
        """

        self.check_skip_abnormal_chunks("sync_with_exist",
                                        self.chunk_collection_path)

    def test_sync_syncs_normal_chunks(self):
        """
        ``sync_with_exist`` syncs normal chunks.
        """

        self.check_syncs_normal_chunks("sync_with_exist",
                                       self.chunk_collection_path)

    def check_deletes_documents(self, op, collection, *args):
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        entry = self.make_reachable(c)
        c.chunkmetadata.delete()

        # We have to delete the collection because merely saving the
        # chunk causes it to be synced, but this is not what we are
        # testing here. We want to make sure that calling
        # op will perform the sync.
        db = ExistDB()
        db.removeCollection(collection, True)
        self.assertEqual(len(list_collection(db, collection)), 0)

        op = getattr(self.manager, op)
        op(*args)

        self.assertEqual(len(list_collection(db, collection)), 1)

        # Make sure our chunk was not collected.
        self.assertEqual(self.manager.count(), 1)

        # Now we delete the chunk in SQL because we do not want the
        # ``delete`` method to be called, as it would take care of
        # removing the document itself. (And yes, we do interpolate
        # the table name. This is safe as ``Entry._meta.db_table`` is
        # a value under our control.)
        with connection.cursor() as cursor:
            cr = entry.latest
            cursor.execute(
                "DELETE FROM {} WHERE id = %s".format(entry._meta.db_table),
                [entry.pk])
            # We have to do this ourselves because Django's cascading
            # delete is implemented at the ORM level, not the database
            # level.
            cursor.execute(
                "DELETE FROM {} WHERE id = %s".format(cr._meta.db_table),
                [cr.pk])

        # Check that no collection or syncing has occurred.
        self.assertEqual(self.manager.count(), 1)
        self.assertEqual(len(list_collection(db, collection)), 1)

        op(*args)

        # Make sure our chunk was collected.
        self.assertEqual(self.manager.count(), 0)
        self.assertEqual(len(list_collection(db, collection)), 0)

    def test_sync_deletes_exist_documents(self):
        """
        ``sync_with_exist`` deletes those eXist documents that belong to
        chunks that no longer exist.
        """

        self.check_deletes_documents("sync_with_exist",
                                     self.chunk_collection_path)

    def test_prepare_collects(self):
        """
        ``prepare`` causes a collection of unreachable chunks.
        """
        self.check_collects("prepare", "xml", True)

    def test_prepare_skips_abnormal_chunks(self):
        """
        ``prepare`` does not sync abnormal chunks.
        """
        self.check_skip_abnormal_chunks("prepare",
                                        self.display_collection_path,
                                        "xml", True)

    def test_prepare_syncs_normal_chunks(self):
        """
        ``prepare`` syncs normal chunks.
        """
        self.check_syncs_normal_chunks("prepare",
                                       self.display_collection_path,
                                       "xml", True)

    def test_prepare_deletes_exist_documents(self):
        """
        ``prepare`` deletes those eXist documents that belong to
        chunks that no longer exist.
        """

        self.check_deletes_documents("prepare",
                                     self.display_collection_path,
                                     "xml", True)

@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_ALWAYS_EAGER_PROPAGATES_EXCEPTIONS=True,
                   BROKER_BACKEND='memory')
class ChunkTestCase(util.DisableMigrationsMixin, TestCase):
    chunk_collection_path = get_collection_path("chunks")
    display_collection_path = get_collection_path("display")

    prepare_kinds = ("bibl", "xml")

    @classmethod
    def setUpTestData(cls):
        super(ChunkTestCase, cls).setUpTestData()
        cls.foo = foo = user_model.objects.create(
            username="foo", password="foo")
        scribe = Group.objects.get(name='scribe')
        cls.foo.groups.add(scribe)

    def setUp(self):
        cache.clear()
        return super(ChunkTestCase, self).setUp()

    def assertLogRegexp(self, handler, stream, regexp):
        handler.flush()
        self.assertRegexpMatches(stream.getvalue(), regexp)

    def test_abnormal_is_invalid(self):
        """
        Checks that an abnormal chunk is invalid, and that its validity is
        saved after being computed.
        """
        c = Chunk(data="", is_normal=False)
        c.save()
        self.assertIsNone(c._valid)
        self.assertFalse(c.valid)
        self.assertFalse(Chunk.objects.get(pk=c.pk)._valid,
                         "_valid was saved.")

    def test_valid(self):
        """
        Checks that an normal chunk can be valid, and that its validity is
        saved after being computed.
        """
        c = Chunk(data=valid_editable.decode('utf-8'),
                  schema_version=schema_version)
        c.save()
        self.assertIsNone(c._valid)
        self.assertTrue(c.valid)
        self.assertTrue(Chunk.objects.get(pk=c.pk)._valid,
                        "_valid was saved.")

    def test_valid(self):
        """
        Checks that an normal chunk can be valid, and that its validity is
        saved after being computed.
        """
        c = Chunk(data=valid_editable.decode('utf-8'),
                  schema_version=schema_version)
        c.save()
        self.assertIsNone(c._valid)
        self.assertTrue(c.valid)
        self.assertTrue(Chunk.objects.get(pk=c.pk)._valid,
                        "_valid was saved.")

    def test_invalid(self):
        """
        Checks that data that is invalid is recognized as invalid, and the
        the validity is saved after being computed.
        """

        # This data is just flat out invalid...
        data = """
<btw:entry xmlns="http://www.tei-c.org/ns/1.0" version="0.10"\
  xmlns:btw="http://mangalamresearch.org/ns/btw-storage">
  <btw:lemma></btw:lemma>
</btw:entry>
        """

        c = Chunk(data=data,
                  schema_version=schema_version)
        c.save()
        self.assertIsNone(c._valid)
        self.assertFalse(c.valid)
        self.assertFalse(Chunk.objects.get(pk=c.pk)._valid,
                         "_valid was saved.")

    def test_invalid_schematron(self):
        """
        Checks that data that is invalid only due to the schematron check
        is recognized as invalid, and the the validity is saved after
        being computed.
        """
        tree = lxml.etree.fromstring(valid_editable)
        sfs = tree.xpath("//btw:example/btw:semantic-fields | "
                         "//btw:example-explained/btw:semantic-fields",
                         namespaces=xml.default_namespace_mapping)

        for el in sfs:
            el.getparent().remove(el)
        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertTrue(
            util.validate_with_rng(xml.schema_for_version(schema_version),
                                   data),
            "the data should validate")
        self.assertFalse(util.schematron(
            xml.schematron_for_version(schema_version),
            data), "the data should not pass the schematron check")
        c = Chunk(data=data,
                  schema_version=schema_version)
        c.save()
        self.assertIsNone(c._valid)
        self.assertFalse(c.valid)
        self.assertFalse(Chunk.objects.get(pk=c.pk)._valid,
                         "_valid was saved.")

    def test_published_false(self):
        """
        ``published`` is false for chunks that have not been published.
        """
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        self.assertFalse(c.published)

    def test_published_true(self):
        """
        ``published`` is true for chunks that have been published.
        """
        c = Chunk(data=valid_editable.decode('utf-8'),
                  schema_version=schema_version)
        c.save()
        e = Entry()
        e.update(
            self.foo,
            "q",
            c,
            "foo",
            ChangeRecord.CREATE,
            ChangeRecord.MANUAL)
        e.latest.publish(self.foo)
        self.assertTrue(c.published)

    def test_exist_path(self):
        """
        ``exist_path`` returns good values.
        """
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        self.assertEqual(c.exist_path("chunks"),
                         "/".join([get_collection_path("chunks"),
                                   c.c_hash]))
        self.assertEqual(c.exist_path("display"),
                         "/".join([get_collection_path("display"),
                                   c.c_hash]))

    def test_exist_path_raises(self):
        """
        ``exist_path`` raises an error if the kind is wrong.
        """
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        with self.assertRaisesRegexp(ValueError, "unknown value"):
            c.exist_path("invalid")

    def test_display_key(self):
        """
        ``display_key`` returns good values.
        """
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        for kind in self.prepare_kinds:
            self.assertEqual(c.display_key(kind),
                             "{}_{}".format(c.c_hash, kind))

    def test_display_key_raises(self):
        """
        ``display_key`` raises an error if the kind is wrong.
        """
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        with self.assertRaisesRegexp(ValueError, "unknown display key kind"):
            c.display_key("invalid")

    def test_get_cached_value_starts_task(self):
        """
        Check that ``get_cached_value`` starts an actual task if the value
        is missing, and returns ``None``.
        """
        c = Chunk(data="<div/>", is_normal=True)
        c.save()

        for kind in self.prepare_kinds:
            cache.clear()
            with util.WithStringIO(models.logger) as (stream, handler):
                self.assertIsNone(c.get_cached_value(kind))
                self.assertLogRegexp(
                    handler,
                    stream,
                    "^{0} is missing from article_display, launching task$"
                    .format(c.display_key(kind)))

    def test_get_cached_value_knows_about_tasks(self):
        """
        Check that ``get_cached_value`` will log if a task is already
        computing the value and will return ``None``.
        """
        c = Chunk(data="<div/>", is_normal=True)
        c.save()

        for kind in self.prepare_kinds:
            cache.clear()
            cache.set(c.display_key(kind), {"task": "foo"})
            with util.WithStringIO(models.logger) as (stream, handler):
                self.assertIsNone(c.get_cached_value(kind))
                self.assertLogRegexp(
                    handler,
                    stream,
                    "^{0} is being computed by task foo$"
                    .format(c.display_key(kind)))

    def test_get_cached_value_returns_available_data(self):
        """
        Check that ``get_cached_value`` will log if a task is already
        computing the value and will return ``None``.
        """
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        # We have to launch the bibl data preparation ourselves.
        c.prepare("bibl", True)

        for kind in self.prepare_kinds:
            expected = cache.get(c.display_key(kind))
            self.assertIsNotNone(expected)
            self.assertEqual(c.get_cached_value(kind), expected)

    def check_skip_abnormal_chunks(self, op, collection, *args):
        c = Chunk(data="", is_normal=False)
        c.save()

        # We have to delete the collection because merely saving the
        # chunk causes it to be synced, but this is not what we are
        # testing here. We want to make sure that calling
        # sync_with_exist will perform the sync.
        db = ExistDB()
        db.removeCollection(collection, True)
        self.assertEqual(len(list_collection(db, collection)), 0)

        getattr(c, op)(*args)

        self.assertEqual(len(list_collection(db, collection)), 0)

    def test_sync_skips_abnormal_chunks(self):
        """
        ``sync_with_exist`` skips abnormal chunks.
        """
        self.check_skip_abnormal_chunks("sync_with_exist",
                                        self.chunk_collection_path)

    def check_sync_normal_chunks(self, op, collection, *args):
        c = Chunk(data="<div/>", is_normal=True)
        c.save()
        c.chunkmetadata.delete()

        # We have to delete the collection because merely saving the
        # chunk causes it to be synced, but this is not what we are
        # testing here. We want to make sure that calling
        # sync_with_exist will perform the sync.
        db = ExistDB()
        db.removeCollection(collection, True)
        self.assertEqual(len(list_collection(db, collection)), 0)

        ret = getattr(c, op)(*args)

        self.assertEqual(len(list_collection(db, collection)), 1)
        return ret

    def test_sync_syncs_normal_chunks(self):
        """
        ``sync_with_exist`` syncs normal chunks.
        """
        self.check_sync_normal_chunks("sync_with_exist",
                                      self.chunk_collection_path)

    def test_sync_handles_overwrites(self):
        """
        ``sync_with_exist`` will not overwrite documents already in eXist.
        """
        db = ExistDB()
        db.removeCollection(self.chunk_collection_path, True)
        c = Chunk(data="<div/>", is_normal=True)
        c.save()

        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         1)

        with mock.patch('lexicography.models.ExistDB.load') as load_mock:
            c.sync_with_exist()
            self.assertEqual(load_mock.call_count, 0,
                             "load should not have been called!")

        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         1)

    def test_prepare_xml_skips_abnormal_chunks(self):
        """
        ``prepare`` with the "xml" kind skips abnormal chunks.
        """
        self.check_skip_abnormal_chunks("prepare",
                                        self.display_collection_path,
                                        "xml",
                                        True)

    def test_prepare_xml_syncs_normal_chunks(self):
        """
        ``prepare`` with the "xml" kind syncs normal chunks.
        """
        self.check_sync_normal_chunks("prepare",
                                      self.display_collection_path,
                                      "xml", True)

    def test_prepare_can_run_asynchronously(self):
        """
        ``prepare`` can run asynchronously
        """
        c = Chunk(data="<doc/>", is_normal=True)
        c.save()

        for kind in self.prepare_kinds:
            ret = c.prepare("xml")
            # When run asynchronously, we get an AsyncResult on which we
            # can call ``get``.
            ret.get()

    def test_save_syncs_and_prepares(self):
        """
        Saving a chunk syncs it and prepares it for display.
        """
        db = ExistDB()
        db.removeCollection(self.chunk_collection_path, True)
        db.removeCollection(self.display_collection_path, True)
        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         0)
        self.assertEqual(len(list_collection(db,
                                             self.display_collection_path)),
                         0)

        c = Chunk(data="<div/>", is_normal=True)
        c.save()

        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         1)
        self.assertEqual(len(list_collection(db,
                                             self.display_collection_path)),
                         1)

    def test_delete_removes_data_from_exist_and_cache(self):
        """
        Deleting a chunk removes its associated data from eXist and from
        the cache.
        """
        db = ExistDB()
        c = Chunk(data="<div/>", is_normal=True)
        c.clean()
        cache.delete(c.c_hash)
        db.removeCollection(self.chunk_collection_path, True)
        db.removeCollection(self.display_collection_path, True)
        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         0)
        self.assertEqual(len(list_collection(db,
                                             self.display_collection_path)),
                         0)

        for kind in self.prepare_kinds:
            self.assertIsNone(cache.get(c.display_key(kind)))

        c.save()
        # Only the "xml" data is created on save.
        self.assertIsNotNone(cache.get(c.display_key("xml")))
        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         1)
        self.assertEqual(len(list_collection(db,
                                             self.display_collection_path)),
                         1)

        c.delete()
        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         0)
        self.assertEqual(len(list_collection(db,
                                             self.display_collection_path)),
                         0)
        for kind in self.prepare_kinds:
            self.assertIsNone(cache.get(c.display_key(kind)))

    def test_delete_abnormal_does_not_touch_exist_or_cache(self):
        """
        Deleting an abnormal chunk removes its associated data from eXist
        and from the cache.
        """
        db = ExistDB()
        c = Chunk(data="<div/>", is_normal=False)
        c.clean()
        cache.delete(c.c_hash)
        db.removeCollection(self.chunk_collection_path, True)
        db.removeCollection(self.display_collection_path, True)

        c.save()
        for kind in self.prepare_kinds:
            self.assertIsNone(cache.get(c.display_key(kind)))
        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         0)
        self.assertEqual(len(list_collection(db,
                                             self.display_collection_path)),
                         0)

        with mock.patch('lexicography.models.ExistDB.removeDocument') as \
                remove_mock:
            c.delete()
            self.assertEqual(remove_mock.call_count, 0)

        self.assertEqual(len(list_collection(db, self.chunk_collection_path)),
                         0)
        self.assertEqual(len(list_collection(db,
                                             self.display_collection_path)),
                         0)
        for kind in self.prepare_kinds:
            self.assertIsNone(cache.get(c.display_key(kind)))
