# -*- coding: utf-8 -*-

import re
import datetime
import json

from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from south.modelsinspector import add_introspection_rules

from .zotero import Zotero, zotero_settings
from lib import util

# This is an arbitrary limit on the size of a Zotero URL fragment that
# uniquely identifies a Zotero entry.
#
# The URL contains:
#
# /users/<userID>/items/<itemKey>
#
# and a key=<APIkey> parameter which contains a key to access the
# user's data.
#
# - <userID> is 10 digits long (see master.sql in zotero-dataserver's
#   code).
#
# - <itemKey> is 8 chars long (see shard.sql in zotero-dataserver's
#  code).
#
# - <APIKey> is 24 chars long (see master.sql in the Zotero server
#  code.)
#
# For accessing groups the scheme is the same except that the URL
# fragment contains "/groups/<groupID>". A <groupID> has the same
# format as a <userID>. Internally, we ALWAYS store a <userID> with
# the "u" prefix and a <groupID> with the "g" prefix.
#
# We double the values below to build some slack into the system.

add_introspection_rules([], [r"^bibliography\.models\.ZoteroUIDField"])


class ZoteroUIDField(models.CharField):
    description = "A Zotero user id or group id."

    def __init__(self, *args, **kwargs):
        # The length of the uid takes into account the 2-character
        # prefix we add to distinguish user ids from group ids.
        kwargs['max_length'] = 22
        super(ZoteroUIDField, self).__init__(*args, **kwargs)

add_introspection_rules([], [r"^bibliography\.models\.ZoteroAPIKeyField"])


class ZoteroAPIKeyField(models.CharField):
    description = "A Zotero API key."

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 48
        super(ZoteroAPIKeyField, self).__init__(*args, **kwargs)


class ZoteroUser(models.Model):
    btw_user = models.OneToOneField(settings.AUTH_USER_MODEL)
    uid = ZoteroUIDField()
    api_key = ZoteroAPIKeyField()

    def clean(self):
        """ custom validation to check the presence of prefix in uid """

        # step1. validate the userid has the prefix or raise error
        uid = self.uid
        regex = re.compile(r"^(?P<prefix>u|g):(?P<id>\d+)$")
        result = regex.search(uid)
        if not result:
            raise ValidationError("malformed Zotero unique id(Uid field)")
        # optional step, following lines can be disabled
        # if delay has to be minimum.

        else:
            # step 2. connect over the wire and validate the http response
            # only successful connection means both the items are valid.
            api_dict = {'uid': self.uid, 'api_key': self.api_key}

            z_obj = Zotero(api_dict)
            sts, res = z_obj.testKeys()

            if sts == 1:
                raise ValidationError(
                    "Connectivity error url query failed.")

            if res.code == 404:
                raise ValidationError(
                    "Zotero UID invalid(Uid field) url query failed.")
            elif res.code == 403:
                if res.read() == 'Forbidden':
                    raise ValidationError(
                        "Zotero UID mismatch(Zapikey field) url query failed.")
                else:
                    raise ValidationError(
                        "Wrong Zotero APIkey(Zapikey field) url query failed.")


class ItemManager(models.Manager):
    zotero = Zotero(zotero_settings(), 'BTW Library')

    def mark_all_stale(self):
        """
        Mark all records as stale. This does not cause an immediate
        refresh from the Zotero cache or from the server. However,
        next time the records are read, they will all be refreshed.
        """

        # Reminder: this kind of update does not trigger signals, does
        # not call .save().
        self.update(freshness=None)

MINIMUM_FRESHNESS = datetime.timedelta(minutes=30)


class Item(models.Model):

    """
    Models a Zotero item. **This model is not meant for general
    purpose modification of Zotero entries.** What it does is
    represent an item in the local database so that:

    * The data is cached locally, and so the application does not keep
      hitting the Zotero servers.

    * It is possible to use database search and filtering to find
      items, rather than query the Zotero server.

    * Deleting items in the Zotero database or losing the Zotero
      database will not mean that BTW will lose its entries.

    This cache cannot be recreated if the Zotero database is lost. So
    it must be backed up when the server is upgraded, moved, etc.
    """
    objects = ItemManager()

    uid = ZoteroUIDField()
    """The Zotero user id. This identifies where the item came from."""

    item_key = models.CharField(max_length=16)
    """The key Zotero has assigned to the item."""

    date = models.TextField(null=True)
    """Cached date of publication."""

    title = models.TextField(null=True)
    """
    Cached title. This is the original title of the work.
    """

    creators = models.TextField(null=True)
    """
    Those responsible for this work. It could be authors or
    editors. This is cached and processed from the Zotero data.
    """

    freshness = models.DateTimeField(null=True)
    """
    The last date and time at which this entry was refreshed from the
    Zotero database.
    """

    item = models.TextField(null=True)
    """
    The actual item data from the Zotero database, stored as JSON.
    """

    _item = None
    """
    The actual item data from the Zotero database, as a Python
    dict. This is not stored in the database.
    """

    def __init__(self, *args, **kwargs):
        super(Item, self).__init__(*args, **kwargs)
        self.refresh()

    def refresh(self):
        """
        Checks whether the item needs refreshing. If so, it will seek the
        data anew from the Zotero database and recompute the fields
        that cache this data.
        """
        if self._refresh():
            self.date = self._item["data"].get("date", None)
            self.title = self._item["data"].get("title", None)
            self.creators = self._creators()
            self.save()

    def _refresh(self):
        """
        Checks whether the item needs refreshing. If so, it will seek the
        data anew from the Zotero database.
        """

        #
        # Don't refresh objects that are not from our current library.
        #
        if self.uid is not None and Item.objects.zotero.full_uid != self.uid:
            return False

        now = util.utcnow()

        if not (super(Item, self).__getattribute__("item") is None or
                self.freshness is None or now - self.freshness >
                MINIMUM_FRESHNESS):
            return False

        self._item = Item.objects.zotero.get_item(self.item_key)
        self.item = json.dumps(self._item)
        self.freshness = now
        self.save()
        return True

    def mark_stale(self):
        """
        Mark this entry as stale. Note that this does not automatically
        refresh **this** object. However, next time the record is
        fetched from the database, it will be refreshed from the local
        Zotero cache, and perhaps from the Zotero server.
        """
        self.freshness = None
        self.save()

    def _creators(self):
        creators = self._item["data"].get("creators", None)

        ret = None
        if creators is not None:
            names = [creator.get("lastName", creator.get("firstName",
                                                         creator.get("name",
                                                                     "")))
                     for creator in creators]
            ret = ", ".join(names)

        return ret

    @property
    def new_primary_source_url(self):
        return reverse('bibliography_new_primary_sources', args=(self.pk, ))

    @property
    def primary_sources_url(self):
        return reverse('bibliography_item_primary_sources', args=(self.pk, ))

    @property
    def url(self):
        return reverse('bibliography_items', args=(self.pk, ))

    @property
    def zotero_url(self):
        # We purposely do not cause a refresh. The URL should not ever
        # change once an entry is created. The URL is based on the
        # entry key which is immutable and on the library id (user id
        # or group id), which should not change in a BTW installation,
        # short of a major restructuring which should entail a flush
        # of the cache.
        item = json.loads(self.item)

        return item["links"]["alternate"]["href"]

class PrimarySource(models.Model):
    SUTRA = "SU"
    SHASTRA = "SH"
    AVADANA = "AV"
    LITTEXT = "LI"
    PALI = "PA"
    GENRE_CHOICES = (
        (SUTRA, "Sūtra"),
        (SHASTRA, "Śāstra"),
        (AVADANA, "Avadāna"),
        (LITTEXT, "Literary Text"),
        (PALI, "Pāli"),
    )

    class Meta(object):
        verbose_name_plural = "Primary sources"

    def __unicode__(self):
        return self.reference_title

    def save(self, *args, **kwargs):
        self.full_clean()
        return super(PrimarySource, self).save(*args, **kwargs)

    def clean(self):
        if self.reference_title is not None:
            self.reference_title = self.reference_title.strip()

    reference_title = models.TextField(
        unique=True, default=None,
        validators=[RegexValidator(r"[^\s]",
                                   "This field cannot contain only spaces.")])

    """
    The reference title assigned by users of BTW. This is the title
    shown in articles. The reason for this field is that for instance
    an edition of the Abhidharmakośa could be published under the name
    "The Treasury of Scholasticism" but our users would want to refer
    to it by its classical name. This is where such name is recorded.
    """

    genre = models.CharField(max_length=2, choices=GENRE_CHOICES, default=None)
    """The genre to which this primary source belongs."""

    item = models.ForeignKey(Item, related_name="primary_sources")
    """The bibliographical item to which it corresponds."""

    @property
    def url(self):
        return reverse('bibliography_primary_sources', args=(self.pk, ))
