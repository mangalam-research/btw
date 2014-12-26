import os

from django_webtest import TransactionWebTest
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.contrib.sites.models import Site

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


class GeneralTestCase(ViewTestCase):

    fixtures = ["initial_data.json",
                os.path.join("core", "tests", "fixtures", "sites.json")]

    brand_xpath = '//a[@class="navbar-brand"]'
    alert_xpath = \
        '//div[@id="btw-site-navigation"]/div[@role="alert"]'

    def test_defaults(self):
        """
        Tests the default values that affect the appearance of
        the site.
        """

        response = self.app.get('/')
        brand = response.lxml.xpath(self.brand_xpath)[0]
        self.assertEqual(brand.text, "BTW dev")

        self.assertEqual(len(response.lxml.xpath(self.alert_xpath)),
                         0, "there should be no alert")

    def test_site_name(self):
        """
        Tests that the site name should be determined by the name of the
        site in the database.
        """
        site = Site.objects.get_current()
        site.name = "foo"
        site.save()

        response = self.app.get('/')
        brand = response.lxml.xpath(self.brand_xpath)[0]
        self.assertEqual(brand.text, "foo")

    @override_settings(BTW_DEMO=True)
    def test_demo_alert(self):
        """
        Tests that a demo alert shows up if the site is a demo.
        """
        response = self.app.get('/')
        alerts = response.lxml.xpath(self.alert_xpath)
        self.assertEqual(len(alerts), 1, "there should be one alert")
        self.assertEqual(
            alerts[0].text.strip(),
            "You are on the demo site. Do not save any work here.")


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

    def test_main_show_login(self):
        """
        Tests that the main view shows a login option when the user has
        not logged in yet.
        """
        response = self.app.get(reverse("main"))
        self.assertTrue(
            len(response.lxml.xpath("//a[@href='{0}']"
                                    .format(reverse("login")))) > 0)

    def test_main_show_logout(self):
        """
        Tests that the main view shows a logout option when the user is
        logged in.
        """
        response = self.app.get(reverse("main"), user='foo')
        self.assertTrue(
            len(response.lxml.xpath("//a[@href='{0}']"
                                    .format(reverse("logout")))) > 0)

    def test_main_show_administration(self):
        """
        Tests that the main view shows an administration option when the
        user is an administrator.
        """
        response = self.app.get(reverse("main"), user='admin')
        self.assertTrue(
            len(response.lxml.xpath("//a[@href='{0}']"
                                    .format(reverse("admin:index")))) > 0)

    def test_main_does_not_show_administration(self):
        """
        Tests that the main view does not show an administration option
        when the user is not an administrator.
        """
        response = self.app.get(reverse("main"), user='foo')
        self.assertTrue(
            len(response.lxml.xpath("//a[@href='{0}']"
                                    .format(reverse("admin:index")))) == 0)


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
