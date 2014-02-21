import datetime
from ..models import Invitation


def expire(invitation):
    invitation.creation_date -= Invitation.objects.expiration_delay + \
        datetime.timedelta(seconds=1)
    invitation.save()

BAD_KEY = "You need a valid invitation to register for this site. " \
    "If you were sent an invitation already, it may have expired, "\
    "or you may have already used it."
