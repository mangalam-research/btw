from django_webtest import WebTest
from django.core.urlresolvers import reverse
from django.core import mail
from django.test.utils import override_settings
from django.utils import translation
from cms.test_utils.testcases import BaseCMSTestCase

# pylint: disable=no-name-in-module
from nose.tools import assert_equal

import os

from ..models import Invitation

from .util import expire, BAD_KEY

dirname = os.path.dirname(__file__)

class ViewTestCase(BaseCMSTestCase, WebTest):
    fixtures = list(os.path.join(dirname, "fixtures", x)
                    for x in ("users.json", "sites.json"))

    def setUp(self):
        super(ViewTestCase, self).setUp()
        translation.activate('en-us')
        self.login_url = reverse('login')
        self.bare_invite_url = reverse('invitation_invite')
        self.bare_complete_url = reverse('invitation_complete')
        self.complete_url = reverse('invitation_complete')
        self.signup_url = reverse('account_signup')


class InviteTestCase(ViewTestCase):

    def test_not_logged_in(self):
        """Test that a user who is not logged gets redirected."""
        response = self.app.get(self.bare_invite_url)
        response = response.follow()
        self.assertRedirects(response, self.login_url +
                             "?next=" + self.bare_invite_url)

    def test_lacking_permission_get(self):
        """
        Test that a user without the right permissions cannot get.
        """
        response = self.app.get(
            self.bare_invite_url, user="foo2", expect_errors=True)
        assert_equal(response.status_code, 403)

    def test_lacking_permission_post(self):
        """
        Test that a user without the right permissions cannot post.
        """
        response = self.app.post(
            self.bare_invite_url, user="foo2", expect_errors=True)
        assert_equal(response.status_code, 403)

    @override_settings(DEFAULT_FROM_EMAIL="test@localhost")
    def test_invite(self):
        """
        Test that a user with the right permissions can send an invitation
        and that a proper email is sent.
        """
        response = self.app.get(self.bare_invite_url, user="foo")
        form = response.form
        form['email'] = 'foo@foo.foo'
        form['sender_note'] = 'Blah.'
        response = form.submit()
        self.assertRedirects(response, self.complete_url)
        invitation = Invitation.objects.get(recipient="foo@foo.foo")
        assert_equal(len(mail.outbox), 1)
        assert_equal(mail.outbox[0].subject, "Invitation to register on BTW.")
        assert_equal(mail.outbox[0].from_email, "test@localhost")
        assert_equal(mail.outbox[0].body, u"""
Blah.

You have been invited to join BTW.

Click the link below to register. This link will expire in 5 days.

http://localhost:80/en-us/invitation/use/{0}/

All the best,
The BTW Team
""".format(invitation.key))


class UseTestCase(ViewTestCase):

    def test_bad_key(self):
        """
        Test that trying to use a key that does not exist produces an
        error message.
        """
        url = reverse('invitation_use', args=('foo', ))

        response = self.app.get(url)
        self.assertContains(response, BAD_KEY)

    def test_expired_key(self):
        """
        Test that trying to use a key that has expired produces an error
        message.
        """
        invitation = Invitation.objects.create_invitation(
            recipient="foo@foo.foo")
        expire(invitation)

        url = reverse('invitation_use', args=(invitation.key, ))

        response = self.app.get(url)
        self.assertContains(response, BAD_KEY)

    def test_used_key(self):
        """
        Test that trying to use a key that has been used produces an error
        message.
        """
        invitation = Invitation.objects.create_invitation(
            recipient="foo@foo.foo")
        invitation.used = True
        invitation.save()

        url = reverse('invitation_use', args=(invitation.key, ))

        response = self.app.get(url)
        self.assertContains(response, BAD_KEY)

    def test_good_key(self):
        """
        Test that using a good key redirects to the signup screen.
        """
        invitation = Invitation.objects.create_invitation(
            recipient="foo@foo.foo")
        url = reverse('invitation_use', args=(invitation.key, ))
        response = self.app.get(url)
        self.assertRedirects(response, self.signup_url)
