from django.db import models
from django.contrib.auth.models import User

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

# Special types

class ZoteroUIDField(models.CharField):
    description = "A Zotero user id or group id."
    def __init__(self, *args, **kwargs):
        # The length of the uid takes into account the 2-character
        # prefix we add to distinguish user ids from group ids.
        kwargs['max_length'] = 22
        super(ZoteroUIDField, self).__init__(*args, **kwargs)

class ZoteroItemKey(models.CharField):
    description = "A Zotero item key."
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 16
        super(ZoteroItemKey, self).__init__(*args, **kwargs)

class ZoteroAPIKeyField(models.CharField):
    description = "A Zotero API key."
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 48
        super(ZoteroAPIKeyField, self).__init__(*args, **kwargs)

class ZoteroUser(models.Model):
    btw_user = models.OneToOneField(User)
    uid = ZoteroUIDField()
    api_key = ZoteroAPIKeyField()

class AbbreviationEntry(models.Model):
    abbreviation = models.TextField() # Immutable
    zotero_entry = models.TextField() # Immutable
    creation_date = models.DateTimeField()

    class Meta:
        verbose_name_plural = "Entries"

    def __unicode__(self):
        return self.abbreviation

class ZoteroEntry(models.Model):

    # Note that we do not support accessing databases other than
    # api.zotero.org so we do not record the server name.

    # This model contains all Zotero entries actually in use by BTW.
    # The entries themselves are immutable. In other words, INSERT can
    # happen but not UPDATE and not DELETE.
    
    # This field contains enough information to retreive the entry
    # from the BTW group: it contains only the <itemKey>, the user ID
    # and APIkey are provided by settings.ZOTERO_SETTINGS["uid"] and
    # settings.ZOTERO_SETTINGS["api_key"]
    #
    zotero_item_key = ZoteroItemKey()
    
    #
    # These following fields give the coordinates of the original
    # entry that a contributor imported into BTW. This is largely
    # FYI-only.
    #
    
    zotero_orig_uid = ZoteroUIDField()
    zotero_orig_item_key = ZoteroItemKey()
    zotero_orig_api_key = ZoteroAPIKeyField()


