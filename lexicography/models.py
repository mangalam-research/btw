import hashlib
import datetime

from django.db import models
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.conf import settings
from django.utils.decorators import method_decorator
from django.db import transaction
from eulexistdb.db import ExistDB

from lib import util
from lib.existdb import get_chunk_collection_path, list_collection
from . import usermod
from . import xml
from . import signals
# This is just to make sure that caching is loaded whenever models are
# loaded. Django 1.6 does not have a neat way to do this. We could
# load caching in __init__.py but it has side-effects.
from . import caching as _

class EntryManager(models.Manager):

    def locked(self, qs=None):
        """
        :param qs: A query set from which to find the locked entries. May
                   be ``None``, in which case all entries are searched.
        :type qs: :class:`django.db.models.query import QuerySet`
        :returns: A list of locked entries.
        :rtype: :class:`list`
        """

        if qs is None:
            # This should be faster than going through Entry.objects.all().
            return [lock.entry for lock in EntryLock.objects.all() if not
                    lock.expirable]

        return [entry for entry in qs if entry.is_locked()]

    def active_entries(self):
        """
        Active entries are those that have not been deleted from the
        system.
        """
        # An entry is inactive if the latest change record for it is a
        # deletion.
        return self.exclude(deleted=True)


class Entry(models.Model):
    objects = EntryManager()

    class Meta(object):
        verbose_name_plural = "Entries"
        unique_together = (("lemma", ), )
        # This is really application-wide but Django insists that permissions
        # be associated with specific models.
        permissions = (('garbage_collect', "Perform a garbage collection."),
                       )

    lemma = models.CharField(max_length=1024)
    # This field must be allowed to be null because there is a
    # circular reference between ``Entry`` and ``ChangeRecord``.
    latest = models.ForeignKey('ChangeRecord', related_name='+', null=True)
    latest_published = models.ForeignKey('ChangeRecord', related_name="+",
                                         null=True)
    deleted = models.BooleanField(default=False, db_index=True)

    def save(self, *args, **kwargs):
        was_nonexistent = self.pk is None
        super(Entry, self).save(*args, **kwargs)
        if was_nonexistent:
            self._send(signals.entry_available)

    def __unicode__(self):
        return self.lemma

    def get_absolute_url(self):
        return reverse('lexicography_entry_details', args=(self.id, ))

    @method_decorator(transaction.atomic)
    def update(self, user, session_key, chunk, lemma, ctype, subtype,
               note=""):
        if self.id is None and ctype != ChangeRecord.CREATE:
            raise ValueError("The Entry has no id but the ctype is not CREATE")

        self.lemma = lemma
        # save() first. So that if we have an integrity error, there is no
        # stale ChangeRecord to remove.
        self.save()

        cr = ChangeRecord(
            entry=self,
            lemma=lemma,
            user=user,
            datetime=util.utcnow(),
            session=session_key,
            ctype=ctype,
            csubtype=subtype,
            c_hash=chunk,
            note=note)

        cr.save()

        # We can't set latest before we've saved cr.
        self.latest = cr
        self.save()

    @method_decorator(transaction.atomic)
    def mark_deleted(self, user):
        dr = DeletionChange(
            entry=self,
            user=user,
            ctype=DeletionChange.DELETE,
            datetime=util.utcnow()
        )
        dr.save()
        was_deleted = self.deleted
        self.deleted = True
        self.save()
        if not was_deleted:
            self._send(signals.entry_unavailable)

    @method_decorator(transaction.atomic)
    def undelete(self, user):
        dr = DeletionChange(
            entry=self,
            user=user,
            ctype=DeletionChange.UNDELETE,
            datetime=util.utcnow()
        )
        dr.save()
        was_deleted = self.deleted
        self.deleted = False
        self.save()
        if was_deleted:
            self._send(signals.entry_available)

    @method_decorator(transaction.atomic)
    def _update_latest_published(self):
        was_published = self.latest_published is not None
        try:
            self.latest_published = self.changerecord_set.filter(
                published=True).latest('datetime')
        except ChangeRecord.DoesNotExist:
            self.latest_published = None
        self.save()
        if self.latest_published is not None:
            if not was_published:
                self._send(signals.entry_newly_published)
        elif was_published:
            self._send(signals.entry_unpublished)

    def _send(self, signal):
        signal.send(self.__class__, instance=self)

    def is_locked(self):
        """
        :returns: The user who has a lock on this entry.
        :rtype: If the entry is locked, returns the user. The value of
                :attr:`settings.AUTH_USER_MODEL` determines the
                class. Otherwise, returns ``None``.
        """
        if self.entrylock_set.exists():
            lock = self.entrylock_set.all()[0]
            if not lock.expirable:
                return lock.owner

        return None

    def is_editable_by(self, user):
        """
        Determines whether the entry is editable by the specified
        user. This method considers both Django permissions **and**
        locking. That is, if the user lacks the permissions or cannot
        lock the entry, then the user cannot edit the entry. The user
        must have the same permissions as those in the group named
        "scribe", either because the user belongs to that group or
        because the user has all the permissions of that
        group.

        :param user: The user for whom we want to check whether the entry
                     is editable.
        :type user: The value of :attr:`settings.AUTH_USER_MODEL`
                    determines the class.
        :returns: True if editable. False if not.
        :rtype: :class:`bool`
                """

        # Superusers have all permissions so we don't check them.
        if not user.is_superuser and not usermod.can_author(user):
            return False

        owner = self.is_locked()
        if owner is None:
            return True

        return owner.pk == user.pk

    @property
    def dependency_key(self):
        return self.lemma

    @property
    def schema_version(self):
        """
        The schema version of the latest version of this entry.
        """
        return self.latest.schema_version

    def use_latest_schema_version(self, request):
        """
        Ensures that the entry is using the latest schema version. If it
        is **already** so, then this method does nothing. Otherwise,
        it will edit the entry to upgrade it to the latest schema
        version.

        This method must be able to lock the entry for modification.

        :returns: The latest version of this entry, or ``None`` if the
        entry could not be locked.
        :rtype: :class:`ChangeRecord`
        """
        latest_version = xml.get_supported_schema_versions().keys()[-1]

        if self.schema_version == latest_version:
            # No need to upgrade.
            return self.latest

        # We need to upgrade.
        data = xml.convert_to_version(self.latest.c_hash.data,
                                      self.schema_version,
                                      latest_version)
        chunk = Chunk(data=data, schema_version=latest_version)
        chunk.save()
        xmltree = xml.XMLTree(chunk.data.encode("utf-8"))
        if not self.try_updating(
                request, chunk,
                xmltree,
                ChangeRecord.VERSION,
                ChangeRecord.AUTOMATIC,
                "Update to schema version " + latest_version):
            return None

        return self.latest

    def try_updating(self, request, chunk, xmltree, ctype, subtype,
                     note=""):
        # We cannot import this at the top level without causing a loop.
        from .locking import try_acquiring_lock

        chunk.save()
        user = request.user
        session_key = request.session.session_key
        lemma = xmltree.extract_lemma()
        if self.id is None:
            self.update(user, session_key, chunk, lemma,
                        ChangeRecord.CREATE, subtype, note)
            if try_acquiring_lock(self, user) is None:
                raise Exception("unable to acquire the lock of an entry "
                                "that was just created but not committed!")
        else:
            if try_acquiring_lock(self, user) is None:
                return False
            self.update(user, session_key, chunk, lemma, ctype, subtype,
                        note)
        return True


class ChangeRecord(models.Model):

    CREATE = 'C'
    UPDATE = 'U'
    REVERT = 'R'
    VERSION = 'V'
    TYPE_CHOICES = (
        (CREATE, "Create"),
        (UPDATE, "Update"),
        (REVERT, "Revert"),
        (VERSION, "Version update"),
    )

    AUTOMATIC = 'A'
    MANUAL = 'M'
    RECOVERY = 'R'
    SUBTYPE_CHOICES = (
        (AUTOMATIC, "Automatic"),
        (MANUAL, "Manual"),
        (RECOVERY, "Recovery")
    )

    entry = models.ForeignKey(Entry)
    # Yep, arbitrarily limited to 1K. CharField() needs a limit. We
    # could use TextField() but the flexibility there comes at a cost.
    lemma = models.CharField(max_length=1024)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.PROTECT)
    datetime = models.DateTimeField()
    session = models.CharField(max_length=100, null=True)
    ctype = models.CharField(max_length=1, choices=TYPE_CHOICES)
    csubtype = models.CharField(max_length=1, choices=SUBTYPE_CHOICES)
    c_hash = models.ForeignKey('Chunk', on_delete=models.PROTECT)
    published = models.BooleanField(default=False)
    # Here too we arbitrarily limit the size.
    note = models.CharField(max_length=1024, blank=True)

    def get_absolute_url(self):
        return reverse('lexicography_entry_details',
                       args=(self.entry.id, self.id, ))

    @property
    def etag(self):
        return self.c_hash.c_hash

    @method_decorator(transaction.atomic)
    def can_publish(self, user):
        """
        Returns a boolean indicating whether the user can publish this
        ``ChangeRecord``. If the user cannot author, then the user
        cannot publish anything.
        """
        return usermod.can_author(user)

    @method_decorator(transaction.atomic)
    def can_be_published(self):
        """
        Returns a boolean indicating whether this record can be published
        at all, by anyone. For instance, a ``ChangeRecord`` that
        encodes an invalid state of an article cannot be published.
        """
        return self.c_hash.valid

    @method_decorator(transaction.atomic)
    def publish(self, user):
        if not self.published:
            if not self.can_be_published():
                return False

            if not self.can_publish(user):
                raise PermissionDenied
            self.published = True
            self.save()
            pc = PublicationChange(changerecord=self,
                                   ctype=PublicationChange.PUBLISH,
                                   user=user,
                                   datetime=util.utcnow())
            pc.save()
            # pylint: disable=protected-access
            self.entry._update_latest_published()
            return True
        return False

    @method_decorator(transaction.atomic)
    def unpublish(self, user):
        if self.published:
            if not self.can_publish(user):
                raise PermissionDenied

            self.published = False
            self.save()
            pc = PublicationChange(changerecord=self,
                                   ctype=PublicationChange.UNPUBLISH,
                                   user=user,
                                   datetime=util.utcnow())
            pc.save()
            # pylint: disable=protected-access
            self.entry._update_latest_published()
            return True
        return False

    def article_display_key(self, published=None):
        """
        Retuns the key to be used in the article_display cache for this
        ChangeRecord. The key is built from the publication status of
        the record (which may be overriden) and from the hash of the
        Chunk corresponding to the record. If it so happens that two
        ChangeRecords share the same Chunk (which may happen) then
        they will share the same pair of possible keys (published and
        unpublished), which is what we want.

        :param published: Override the publication status of this
                          record for the sake of computing the key.
        :type published: :class:`bool`
        """
        if published is None:
            published = self.published

        return "{0}_{1}".format(self.c_hash.c_hash, published)

    @property
    def schema_version(self):
        """
        The schema version of this update.
        """
        return self.c_hash.schema_version

    class Meta(object):
        unique_together = (("entry", "datetime", "ctype"), )

    def __unicode__(self):
        return self.entry.lemma + " " + self.user.username + " " + \
            str(self.datetime)


class ChunkManager(models.Manager):

    @method_decorator(transaction.atomic)
    def collect(self):
        """
        Garbage collects (i.e. deletes) all the chunks that are no longer
        referenced by any Entry or ChangeRecord.

        :returns: The chunks that were removed.
        :rtype: class:`Chunk`
        """
        # A SQL DELETE will not delete anything if any of the records
        # to be deleted are protected, so we retry until it works. How
        # could it happen? After the list is acquired but before the
        # delete operation, a user creates a new entry, which happens
        # to have the same contents as one of the chunks which was no
        # longer being referenced when we acquired our list. (This is
        # possible because we do not prevent writing to Chunk objects
        # while we collect.) The delete will fail with a
        # ProtectedError. The next iteration of the loop would
        # probably get a clean list. (Or it can retry if it fails
        # again.)
        while True:
            chunks = Chunk.objects.filter(changerecord__isnull=True)
            try:
                chunks.delete()
                break
            except models.ProtectedError:
                pass

        return chunks

    def sync_with_exist(self):
        self.collect()
        db = ExistDB()
        present = set()
        for chunk in self.filter(is_normal=True):
            chunk.sync_with_exist(db)
            present.add(chunk.c_hash)

        chunk_collection_path = get_chunk_collection_path()
        for path in list_collection(db, chunk_collection_path):
            parts = path.split("/")
            if parts[-1] not in present:
                db.removeDocument(path)


class Chunk(models.Model):
    objects = ChunkManager()

    c_hash = models.CharField(
        max_length=40,
        primary_key=True,
        help_text="This is the primary key for chunks. It is a hash of "
        "the <code>data</code> field."
    )
    is_normal = models.BooleanField(
        default=True,
        help_text="A 'normal' chunk is one that is well-formed XML"
    )
    # Yep, arbitrary 10 char limit. This field can contain an empty
    # string if the version is somehow not computable. For instance if
    # the data is "abnormal".
    schema_version = models.CharField(
        max_length=10,
        help_text="This is the version of the btw-storage schema that ought "
        "to be used to validate this chunk."
    )
    _valid = models.NullBooleanField(
        null=True,
        db_column="valid",
        help_text="Whether this chunk is valid when validated against the "
        "schema version specified in the <code>schema_version</code> "
        "field. You do not normally access this field through "
        "<code>valid</code>."
    )
    data = models.TextField()

    @property
    def valid(self):
        """
        Whether or not the chunk is valid. Use this rather than the
        ``_valid`` field.
        """
        if self._valid is not None:
            return self._valid

        if not self.is_normal:
            self._valid = False
        else:
            self._valid = util.validate_with_rng(
                xml.schema_for_version(self.schema_version), self.data)

            if self._valid:
                # We must perform the schematron checks to see whether it is
                # actually valid.
                sch = xml.schematron_for_version(self.schema_version)
                if sch:
                    self._valid = util.schematron(sch, self.data)
        self.save()

        return self._valid

    def __unicode__(self):
        return self.c_hash + " Schema version: " + self.schema_version

    def clean(self):
        sha1 = hashlib.sha1()
        sha1.update(self.data.encode('utf-8'))
        self.c_hash = sha1.hexdigest()

    @property
    def exist_path(self):
        chunk_collection_path = get_chunk_collection_path()
        return "/".join([chunk_collection_path, self.c_hash])

    def sync_with_exist(self, db=None):
        # We do not put "abnormal" chunks in exist.
        if not self.is_normal:
            return

        db = db or ExistDB()
        data = self.data
        if not db.load(data.encode("utf-8"), self.exist_path):
            raise Exception("could not sync with eXist database")

    def save(self, *args, **kwargs):
        self.clean()
        self.sync_with_exist()
        return super(Chunk, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # We were not saved in the first place. Remember that chunks
        # are immutable. So a normal chunk cannot become abnormal, or
        # vice-versa.
        if not self.is_normal:
            return

        db = ExistDB()
        db.removeDocument(self.exist_path)
        return super(Chunk, self).delete(*args, **kwargs)


class PublicationChange(models.Model):
    PUBLISH = 'P'
    UNPUBLISH = 'U'
    TYPE_CHOICES = (
        (PUBLISH, "Publish"),
        (UNPUBLISH, "Unpublish")
    )

    changerecord = models.ForeignKey(ChangeRecord)
    ctype = models.CharField(max_length=1, choices=TYPE_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.PROTECT)
    datetime = models.DateTimeField()


class DeletionChange(models.Model):
    DELETE = 'D'
    UNDELETE = 'U'
    TYPE_CHOICES = (
        (DELETE, "Delete"),
        (UNDELETE, "Undelete")
    )

    entry = models.ForeignKey(Entry)
    ctype = models.CharField(max_length=1, choices=TYPE_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.PROTECT)
    datetime = models.DateTimeField()

if getattr(settings, 'LEXICOGRAPHY_LOCK_EXPIRY') is None:
    raise ImproperlyConfigured('LEXICOGRAPHY_LOCK_EXPIRY not set')

LEXICOGRAPHY_LOCK_EXPIRY = datetime.timedelta(
    hours=settings.LEXICOGRAPHY_LOCK_EXPIRY)


class EntryLock(models.Model):

    class Meta(object):
        verbose_name = "Entry lock"
        verbose_name_plural = "Entry locks"
        unique_together = (("entry"), )

    entry = models.ForeignKey(Entry)
    # The owner is who benefits from this lock.
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    datetime = models.DateTimeField()

    @property
    def expirable(self):
        """
        :returns: ``True`` if the lock is expirable, ``False`` if not.
        :rtype: :class:`bool`
        """
        return util.utcnow() - self.datetime > LEXICOGRAPHY_LOCK_EXPIRY

    def _force_expiry(self):
        """
        Forces the lock to expire. This is meant to be used for testing.
        """
        self.datetime = self.datetime - LEXICOGRAPHY_LOCK_EXPIRY - \
            datetime.timedelta(seconds=1)
        self.save()


class Handle(models.Model):

    class Meta(object):
        unique_together = (("session", "handle"), ("session", "entry"))

    session = models.CharField(max_length=100)
    handle = models.IntegerField()
    entry = models.ForeignKey(Entry, null=True)
