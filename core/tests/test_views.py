import os

from django_webtest import TransactionWebTest
from django.core.urlresolvers import reverse
from django.test.utils import override_settings

# pylint: disable=no-name-in-module
from nose.tools import assert_true, assert_equal, assert_false, \
    assert_not_equal

from invitation.tests.util import BAD_KEY
from invitation.models import Invitation

dirname = os.path.dirname(__file__)


class ViewTestCase(TransactionWebTest):
    fixtures = ["initial_data.json"]

    def setUp(self):
        self.signup_url = reverse("account_signup")
        self.verification_sent = reverse("account_email_verification_sent")
        self.lexicography_url = reverse("lexicography_main")


# Turn off the requirement for emails just for this test.
@override_settings(ACCOUNT_EMAIL_VERIFICATION="none")
class LoginTestCase(ViewTestCase):
    fixtures = ViewTestCase.fixtures + \
        [os.path.join(dirname, "fixtures", "users.json")]

    def test_login(self):
        """
        Tests that a user can login.
        """
        form = self.app.get(reverse("login")).form
        form['login'] = 'foo'
        form['password'] = 'foo'
        response = form.submit()
        self.assertRedirects(response, self.lexicography_url)
        response = response.follow()
        self.assertEqual(response.context['user'].username, 'foo')

    def test_logout(self):
        """
        Tests that a user can logout.
        """
        form = self.app.get(reverse("login")).form
        form['login'] = 'foo'
        form['password'] = 'foo'
        response = form.submit()
        self.assertRedirects(response, self.lexicography_url)
        response = response.follow()
        self.assertEqual(response.context['user'].username, 'foo')
        session_id = self.app.cookies["sessionid"]

        response = self.app.get(reverse("logout"))
        self.assertContains(response, "Are you sure you want to sign out?")
        response = response.form.submit()
        self.assertRedirects(response, reverse("main"))
        assert_not_equal(session_id, self.app.cookies["sessionid"])


class SignupTestCase(ViewTestCase):

    def test_signup_without_invite(self):
        """
        Test that trying to sign up without an invitation gives an error
        message.
        """
        response = self.app.get(self.signup_url)
        self.assertContains(response, BAD_KEY)

    def test_signup(self):
        """
        Test that trying to sign up with an invitation works, and that
        after signup the invitation is marked as used.
        """

        invitation = Invitation.objects.create_invitation(
            recipient="foo@foo.foo")

        url = reverse('invitation_use', args=(invitation.key, ))
        response = self.app.get(url)
        self.assertRedirects(response, self.signup_url)

        assert_equal(self.app.session['invitation_key'], invitation.key,
                     "the key should be stored in the session")
        response = response.follow()
        form = response.form

        form['first_name'] = "First"
        form['last_name'] = "Last"
        form['email'] = "foo@foo.foo"
        form['username'] = "foofoo"
        form['password1'] = "blahblah"
        form['password2'] = "blahblah"
        response = form.submit()
        self.assertRedirects(response, self.verification_sent)

        invitation = Invitation.objects.get(pk=invitation.pk)
        assert_true(invitation.used, "the invitation should have been used")
        assert_false('invitation_key' in self.app.session,
                     "the key should have been removed from the session")
