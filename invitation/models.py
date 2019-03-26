import datetime
import uuid

from django.db import models
from django.conf import settings
from django.utils.functional import cached_property

from lib import util


class InvitationManager(models.Manager):

    @cached_property
    def expiration_delay(self):
        return datetime.timedelta(days=settings.INVITATION_EXPIRY_DAYS)

    def create_invitation(self, recipient):
        """
        Create a new invitation.
        """
        invitation = Invitation()
        invitation.recipient = recipient
        invitation.key = uuid.uuid4().hex
        invitation.save()
        return invitation

    def get_active_invitation(self, key):
        """
        Gets an invitation if the key is still active. If not, returns
        ``None``.
        """
        invitation = None
        try:
            invitation = Invitation.objects.get(key=key)
        except Invitation.DoesNotExist:
            pass

        if invitation and (invitation.expired or invitation.used):
            invitation = None

        return invitation


class Invitation(models.Model):

    objects = InvitationManager()

    key = models.CharField(max_length=32)
    creation_date = models.DateTimeField(auto_now_add=True)
    recipient = models.TextField()
    used = models.BooleanField(default=False)

    def __str__(self):
        return "Invitation " + self.key

    @property
    def expired(self):
        """
        True if the invitation has expired. False if not.
        """
        return util.utcnow() - self.creation_date >= \
            Invitation.objects.expiration_delay
