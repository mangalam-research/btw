import hashlib
import datetime

from django.db import models
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.utils.decorators import method_decorator
from django.db import transaction

from lib import util
from . import usermod


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
        unique_together = (("headword"), )
        # This is really application-wide but Django insists that permissions
        # be associated with specific models.
        permissions = (('garbage_collect', "Perform a garbage collection."),
                       )

    headword = models.CharField(max_length=1024)
    # This field must be allowed to be null because there is a
    # circular reference between ``Entry`` and ``ChangeRecord``.
    latest = models.ForeignKey('ChangeRecord', related_name='+', null=True)
    latest_published = models.ForeignKey('ChangeRecord', related_name="+",
                                         null=True)
    deleted = models.BooleanField(default=False)

    def __unicode__(self):
        return self.headword

    def get_absolute_url(self):
        return reverse('lexicography_entry_details', args=[str(self.id)])

    @method_decorator(transaction.atomic)
    def update(self, user, session_key, chunk, headword, ctype, subtype):
        if self.id is None and ctype != ChangeRecord.CREATE:
            raise ValueError("The Entry has no id but the ctype is not CREATE")

        cr = ChangeRecord(
            entry=self,
            headword=headword,
            user=user,
            datetime=util.utcnow(),
            session=session_key,
            ctype=ctype,
            csubtype=subtype,
            c_hash=chunk)

        self.headword = headword
        # save() first. So that if we have an integrity error, there is no
        # stale ChangeRecord to remove.
        self.save()

        # We need to do this in case the entry just acquired its id when
        # ``save()`` was called.
        cr.entry = self
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
        self.deleted = True
        self.save()

    @method_decorator(transaction.atomic)
    def undelete(self, user):
        dr = DeletionChange(
            entry=self,
            user=user,
            ctype=DeletionChange.UNDELETE,
            datetime=util.utcnow()
        )
        dr.save()
        self.deleted = False
        self.save()

    @method_decorator(transaction.atomic)
    def _update_latest_published(self):
        try:
            self.latest_published = self.changerecord_set.filter(
                published=True).latest('datetime')
        except ChangeRecord.DoesNotExist:
            self.latest_published = None
        self.save()

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
        "author", either because the user belongs to that group or
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


class ChangeRecord(models.Model):

    CREATE = 'C'
    UPDATE = 'U'
    REVERT = 'R'
    TYPE_CHOICES = (
        (CREATE, "Create"),
        (UPDATE, "Update"),
        (REVERT, "Revert"),
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
    headword = models.CharField(max_length=1024)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.PROTECT)
    datetime = models.DateTimeField()
    session = models.CharField(max_length=100, null=True)
    ctype = models.CharField(max_length=1, choices=TYPE_CHOICES)
    csubtype = models.CharField(max_length=1, choices=SUBTYPE_CHOICES)
    c_hash = models.ForeignKey('Chunk', on_delete=models.PROTECT)
    published = models.BooleanField(default=False)

    def get_absolute_url(self):
        return reverse('lexicography_changerecord_details',
                       args=(self.id, ))

    @property
    def etag(self):
        return self.c_hash.c_hash

    @method_decorator(transaction.atomic)
    def publish(self, user):
        if not self.published:
            self.published = True
            self.save()
            pc = PublicationChange(changerecord=self,
                                   ctype=PublicationChange.PUBLISH,
                                   user=user,
                                   datetime=util.utcnow())
            pc.save()
            # pylint: disable=protected-access
            self.entry._update_latest_published()

    @method_decorator(transaction.atomic)
    def unpublish(self, user):
        if self.published:
            self.published = False
            self.save()
            pc = PublicationChange(changerecord=self,
                                   ctype=PublicationChange.UNPUBLISH,
                                   user=user,
                                   datetime=util.utcnow())
            pc.save()
            # pylint: disable=protected-access
            self.entry._update_latest_published()

    class Meta(object):
        unique_together = (("entry", "datetime", "ctype"), )

    def __unicode__(self):
        return self.entry.headword + " " + self.user.username + " " + \
            str(self.datetime) + " " + (self.session or "")


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
    data = models.TextField()

    def __unicode__(self):
        return self.c_hash + " Schema version: " + self.schema_version

    def clean(self):
        sha1 = hashlib.sha1()
        sha1.update(self.data.encode('utf-8'))
        self.c_hash = sha1.hexdigest()

    def save(self, *args, **kwargs):
        self.clean()
        super(Chunk, self).save(*args, **kwargs)


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

LEXICOGRAPHY_LOCK_EXPIRY = \
    datetime.timedelta(hours=settings.LEXICOGRAPHY_LOCK_EXPIRY)


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


class Authority(models.Model):

    class Meta(object):
        verbose_name_plural = "Authorities"


class UserAuthority(Authority):

    class Meta(object):
        verbose_name_plural = "UserAuthorities"
    user = models.ForeignKey(settings.AUTH_USER_MODEL)


class OtherAuthority(Authority):

    class Meta(object):
        verbose_name_plural = "OtherAuthorities"
    name = models.CharField(max_length=1024)


class Handle(models.Model):

    class Meta(object):
        unique_together = (("session", "handle"), ("session", "entry"))

    session = models.CharField(max_length=100)
    handle = models.IntegerField()
    entry = models.ForeignKey(Entry, null=True)
