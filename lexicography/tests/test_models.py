import os
import datetime

from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
import lxml.etree

from ..models import Entry, ChangeRecord, PublicationChange, Chunk
from .. import locking, xml
import lib.util as util
from .test_xml import as_editable

dirname = os.path.dirname(__file__)
local_fixtures = list(os.path.join(dirname, "fixtures", x)
                      for x in ("users.json", "views.json"))

user_model = get_user_model()

# Disable warnings about accessing protected members.
# pylint: disable=W0212

valid_editable = as_editable(os.path.join(xml.schemas_dirname, "prasada.xml"))
xmltree = xml.XMLTree(valid_editable)
schema_version = xmltree.extract_version()

class EntryTestCase(util.NoPostMigrateMixin, TransactionTestCase):
    fixtures = local_fixtures
    serialized_rollback = True

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")
        self.entry = Entry.objects.get(id=1)
        from django.db import connections
        for db_name in self._databases_names(include_mirrors=False):
            with open("/tmp/" + db_name, 'w') as f:
                f.write(connections[db_name]._test_serialized_contents)

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


class ChangeRecordTestCase(util.NoPostMigrateMixin, TransactionTestCase):
    fixtures = local_fixtures
    serialized_rollback = True

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

    def test_article_display_key_unpublished(self):
        """
        Tests that the article display key is properly generated for an
        unpublished change record.
        """
        cr = self.valid.latest
        self.assertEqual(cr.article_display_key(),
                         "{0}_False".format(cr.c_hash.c_hash))

    def test_article_display_key_published(self):
        """
        Tests that the article display key is properly generated for a
        published change record.
        """
        cr = self.valid.latest
        cr.publish(self.foo)
        self.assertEqual(cr.article_display_key(),
                         "{0}_True".format(cr.c_hash.c_hash))

    def test_article_display_key_force_published(self):
        """
        Tests that the article display key is properly generated for an
        unpublished change record when the published status is forced
        ``True``.
        """
        cr = self.valid.latest
        self.assertEqual(cr.article_display_key(True),
                         "{0}_True".format(cr.c_hash.c_hash))

    def test_article_display_key_force_unpublished(self):
        """
        Tests that the article display key is properly generated for a
        published change record when the published status is forced
        ``False``.
        """
        cr = self.valid.latest
        cr.publish(self.foo)
        self.assertEqual(cr.article_display_key(False),
                         "{0}_False".format(cr.c_hash.c_hash))

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

class EntryLockTestCase(util.NoPostMigrateMixin, TransactionTestCase):
    fixtures = local_fixtures
    serialized_rollback = True

    def setUp(self):
        self.foo = user_model.objects.get(username="foo")
        self.foo2 = user_model.objects.get(username="foo2")

    def test_expirable_expired(self):
        entry = Entry.objects.get(id=1)
        lock = locking.try_acquiring_lock(entry, self.foo)
        lock._force_expiry()
        self.assertTrue(lock.expirable)


class ChunkTestCase(util.NoPostMigrateMixin, TransactionTestCase):
    fixtures = local_fixtures
    serialized_rollback = True

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
                         namespaces={
                             "btw":
                             "http://mangalamresearch.org/ns/btw-storage"
                         })
        for el in sfs:
            el.getparent().remove(el)
        data = lxml.etree.tostring(
            tree, xml_declaration=True, encoding='utf-8').decode('utf-8')
        self.assertTrue(util.validate(xml.schema_for_version(schema_version),
                                      data), "the data should validate")
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
