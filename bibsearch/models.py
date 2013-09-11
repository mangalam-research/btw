# Django imports
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings

from south.modelsinspector import add_introspection_rules

#python imports
import re

# module imports
from .utils import Zotero

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

add_introspection_rules([], [r"^bibsearch\.models\.ZoteroUIDField"])


class ZoteroUIDField(models.CharField):
    description = "A Zotero user id or group id."

    def __init__(self, *args, **kwargs):
        # The length of the uid takes into account the 2-character
        # prefix we add to distinguish user ids from group ids.
        kwargs['max_length'] = 22
        super(ZoteroUIDField, self).__init__(*args, **kwargs)

add_introspection_rules([], [r"^bibsearch\.models\.ZoteroAPIKeyField"])


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
