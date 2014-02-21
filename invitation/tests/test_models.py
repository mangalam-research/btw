
from django.test import TestCase

# pylint: disable=no-name-in-module
from nose.tools import assert_false, assert_equal, assert_not_equal, \
    assert_true, assert_is_none

from ..models import Invitation

from .util import expire


class InvitationTestCase(TestCase):

    def test_diffent_keys(self):
        """Test that two invitations have different keys."""
        invitation = Invitation.objects.create_invitation("foo@foo.foo")
        invitation2 = Invitation.objects.create_invitation("foo2@foo.foo")
        assert_not_equal(invitation.key, invitation2.key)

    def test_expired(self):
        """Test that an invitation expires."""
        invitation = Invitation.objects.create_invitation("foo@foo.foo")
        assert_false(invitation.expired)
        expire(invitation)
        assert_true(invitation.expired)


class InvitationManagerTestCase(TestCase):

    def test_creation(self):
        """Test that we can create an Invitation."""
        invitation = Invitation.objects.create_invitation("foo@foo.foo")
        assert_false(invitation.used)
        assert_false(invitation.expired)
        assert_equal(invitation.recipient, "foo@foo.foo")
        assert_equal(unicode(invitation), "Invitation " + invitation.key)

    def test_get_active_invitation_with_invalid_key(self):
        """
        Test that calling get_active_invitation with an invalid key
        returns ``None``.
        """
        assert_is_none(Invitation.objects.get_active_invitation("foo"))

    def test_get_active_invitation_with_expired_key(self):
        """
        Test that calling get_active_invitation with an expired key
        returns ``None``.
        """
        invitation = Invitation.objects.create_invitation("foo@foo.foo")
        expire(invitation)
        assert_is_none(
            Invitation.objects.get_active_invitation(invitation.key))

    def test_get_active_invitation_with_used_key(self):
        """
        Test that calling get_active_invitation with an used key
        returns ``None``.
        """
        invitation = Invitation.objects.create_invitation("foo@foo.foo")
        invitation.used = True
        invitation.save()
        assert_is_none(
            Invitation.objects.get_active_invitation(invitation.key))
