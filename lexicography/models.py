from django.db import models
from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.contrib.auth.models import Group
from lib import util

import hashlib
import datetime


class ChangeInfo(models.Model):

    class Meta(object):
        abstract = True

    CREATE = 'C'
    UPDATE = 'U'
    DELETE = 'D'
    REVERT = 'R'
    TYPE_CHOICES = (
        (CREATE, "Create"),
        (UPDATE, "Update"),
        (DELETE, "Delete"),
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

    def copy_to(self, to):
        if not isinstance(to, ChangeInfo):
            raise ValueError("to is not of the right class")
        for i in ChangeInfo._meta.get_all_field_names():
            setattr(to, i, getattr(self, i))


class Entry(ChangeInfo):

    class Meta(object):
        verbose_name_plural = "Entries"
        unique_together = (("headword"), )
        # This is really application-wide but Django insists that permissions
        # be associated with specific models.
        permissions = (('garbage_collect', "Perform a garbage collection."),
                       )

    def __unicode__(self):
        return self.headword

    def get_absolute_url(self):
        return reverse('entry_details', args=[str(self.id)])

    def is_locked(self):
        """
        :returns: The user who has a lock on this entry.
        :rtype: If the entry is locked, returns the user. The value of
                :attr:`settings.AUTH_USER_MODEL` determines the
                class. Otherwise, returns ``None``.
        """
        if self.entrylock_set.exists():
            lock = self.entrylock_set.all()[0]
            if not lock.is_expirable():
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
        if not user.is_superuser:
            # To be able to edit, the user must have the permissions
            # given to authors.
            author = Group.objects.get(name='author')
            for perm in author.permissions.all():
                if not user.has_perm("{0.content_type.app_label}.{0.codename}"
                                     .format(perm)):
                    return False

        owner = self.is_locked()
        if owner is None:
            return True

        return owner.pk == user.pk


class ChangeRecord(ChangeInfo):
    entry = models.ForeignKey(Entry)

    class Meta(object):
        unique_together = (("entry", "datetime", "ctype"), )

    def __unicode__(self):
        return self.entry.headword + " " + self.user.username + " " + \
            str(self.datetime) + " " + (self.session or "")


class Chunk(models.Model):
    c_hash = models.CharField(max_length=40, primary_key=True)
    is_normal = models.BooleanField(default=True)
    data = models.TextField()

    def __unicode__(self):
        return self.c_hash

    def clean(self):
        sha1 = hashlib.sha1()
        sha1.update(self.data.encode('utf-8'))
        self.c_hash = sha1.hexdigest()

    def save(self, *args, **kwargs):
        self.clean()
        super(Chunk, self).save(*args, **kwargs)


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

    def is_expirable(self):
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
