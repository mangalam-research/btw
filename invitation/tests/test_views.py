import os

from django_webtest import WebTest
from django.urls import reverse
from django.core import mail
from django.test.utils import override_settings
from django.utils import translation
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from cms.test_utils.testcases import BaseCMSTestCase

# pylint: disable=no-name-in-module
from nose.tools import assert_equal

from ..models import Invitation
from .util import expire, BAD_KEY
from lib.util import DisableMigrationsMixin

dirname = os.path.dirname(__file__)
user_model = get_user_model()

class ViewTestCase(BaseCMSTestCase, DisableMigrationsMixin, WebTest):

    def setUp(self):
        super(ViewTestCase, self).setUp()
        translation.activate('en-us')
        self.login_url = reverse('login')
        self.bare_invite_url = reverse('invitation_invite')
        self.bare_complete_url = reverse('invitation_complete')
        self.complete_url = reverse('invitation_complete')
        self.signup_url = reverse('account_signup')

class InviteTestCase(ViewTestCase):

    def setUp(self):
        super(InviteTestCase, self).setUp()
        site = Site.objects.get_current()
        site.name = "BTW"
        site.domain = "btw.mangalamresearch.org"
        site.save()

        g = Group.objects.get(name='scribe')

        self.foo = user_model.objects.create_user(
            username='foo', password='test')

        self.foo.user_permissions.add(Permission.objects.get(
            codename="add_invitation"))
        self.foo.groups.add(g)

        self.foo2 = user_model.objects.create_user(
            username='foo2', password='test')
        self.foo2.groups.add(g)

    def tearDown(self):
        super(InviteTestCase, self).tearDown()
        # We need to clear the cache manually because the rollback
        # performed by the testing framework won't trigger the signals
        # that automatically clear the cache. :-/
        Site.objects.clear_cache()

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
        assert_equal(mail.outbox[0].body, """
Blah.

You have been invited to join BTW.

Click the link below to register. This link will expire in 5 days.

http://testserver/en-us/invitation/use/{0}/

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
