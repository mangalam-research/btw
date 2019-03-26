# -*- encoding: utf-8 -*-
import http.cookiejar as http_cookiejar
import datetime

from django_webtest import WebTest
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import translation
from cms.test_utils.testcases import BaseCMSTestCase

from invitation.tests.util import BAD_KEY
from invitation.models import Invitation
import lib.util as util
from lib import cmstestutil
from lexicography.xml import mods_schema_path

user_model = get_user_model()


@override_settings(ROOT_URLCONF='core.tests.urls')
class ViewTestCase(BaseCMSTestCase, util.DisableMigrationsMixin, WebTest):

    def setUp(self):
        super(ViewTestCase, self).setUp()
        translation.activate('en-us')
        # We need a home page for some of the tests to pass.
        home_page = \
            cmstestutil.create_test_page("Home", "generic_page.html", "en-us")
        home_page.set_as_homepage(True)
        cmstestutil.refresh_cms_apps()

        self.lexicography_url = reverse("lexicography_main")

    def tearDown(self):
        super(ViewTestCase, self).tearDown()
        # We must clear the page cache to make sure tests are working.
        util.delete_own_keys('page')


class GeneralTestCase(ViewTestCase):

    brand_xpath = '//a[@class="navbar-brand"]'
    alert_xpath = \
        '//div[@id="btw-site-navigation"]/div[@role="alert"]'

    def setUp(self):
        super(GeneralTestCase, self).setUp()
        site = Site.objects.get_current()
        site.name = "BTW dev"
        site.domain = "btw.mangalamresearch.org"
        site.save()

    def tearDown(self):
        super(GeneralTestCase, self).tearDown()
        # We need to clear the cache manually because the rollback
        # performed by the testing framework won't trigger the signals
        # that automatically clear the cache. :-/
        Site.objects.clear_cache()

    def test_defaults(self):
        """
        Tests the default values that affect the appearance of
        the site.
        """

        response = self.app.get(reverse('pages-root'))
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

        response = self.app.get(reverse('pages-root'))
        brand = response.lxml.xpath(self.brand_xpath)[0]
        self.assertEqual(brand.text, "foo")

    @override_settings(BTW_DEMO=True)
    def test_demo_alert(self):
        """
        Tests that a demo alert shows up if the site is a demo.
        """
        response = self.app.get(reverse('pages-root'))
        alerts = response.lxml.xpath(self.alert_xpath)
        self.assertEqual(len(alerts), 1, "there should be one alert")
        self.assertEqual(
            alerts[0].text.strip(),
            "You are on the demo site. Do not save any work here.")

    def test_dev_alert(self):
        """
        Tests that a demo alert shows up if the site is accessed while the
        cookie that indicates a developer is turned on.
        """
        # The value can be anything as BTW itself does not care what
        # it is.
        self.app.set_cookie("btw_dev", "foo")
        response = self.app.get(reverse('pages-root'))
        alerts = response.lxml.xpath(self.alert_xpath)
        self.assertEqual(len(alerts), 1, "there should be one alert")
        self.assertEqual(
            alerts[0].text.strip(),
            "You are accessing the site as a DEVELOPER. Make sure to "
            "clear out of developer mode and access the site as a normal "
            "user before telling users to access the site.")


# Turn off the requirement for emails just for this test.
@override_settings(ACCOUNT_EMAIL_VERIFICATION="none")
class LoginTestCase(ViewTestCase):

    def setUp(self):
        super(LoginTestCase, self).setUp()

        self.admin = user_model.objects.create_superuser(
            username='admin', email="foo@foo.foo", password='test')

        g = Group.objects.get(name='scribe')
        self.foo = user_model.objects.create_user(
            username='foo', password='foo')
        self.foo.groups.add(g)

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
        self.assertRedirects(response, "/", target_status_code=302)
        response = response.follow()
        self.assertRedirects(response, reverse("pages-root"))
        self.assertNotEqual(session_id, self.app.cookies.get("sessionid"))
        response = response.follow()

    def test_main_show_login(self):
        """
        Tests that the main view shows a login option when the user has
        not logged in yet.
        """
        response = self.app.get(reverse("pages-root"))
        self.assertTrue(
            len(response.lxml.xpath("//a[@href='{0}']"
                                    .format(reverse("login")))) > 0)

    def test_main_show_logout(self):
        """
        Tests that the main view shows a logout option when the user is
        logged in.
        """
        response = self.app.get(reverse("pages-root"), user='foo')
        self.assertTrue(
            len(response.lxml.xpath("//a[@href='{0}']"
                                    .format(reverse("logout")))) > 0)

    def test_main_show_administration(self):
        """
        Tests that the main view shows an administration option when the
        user is an administrator.
        """
        response = self.app.get(reverse("pages-root"), user='admin')
        self.assertTrue(
            len(response.lxml.xpath("//a[@href='{0}']"
                                    .format(reverse("admin:index")))) > 0)

    def test_main_does_not_show_administration(self):
        """
        Tests that the main view does not show an administration option
        when the user is not an administrator.
        """
        response = self.app.get(reverse("pages-root"), user='foo')
        self.assertTrue(
            len(response.lxml.xpath("//a[@href='{0}']"
                                    .format(reverse("admin:index")))) == 0)


class SignupTestCase(WebTest):

    def setUp(self):
        super(SignupTestCase, self).setUp()
        translation.activate('en-us')
        self.signup_url = reverse("account_signup")
        self.verification_sent = reverse("account_email_verification_sent")

    def tearDown(self):
        super(SignupTestCase, self).tearDown()
        # We must clear the page cache to make sure tests are working.
        util.delete_own_keys('page')

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

        self.assertEqual(self.app.session['invitation_key'], invitation.key,
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
        self.assertTrue(invitation.used,
                        "the invitation should have been used")
        self.assertFalse(
            'invitation_key' in self.app.session,
            "the key should have been removed from the session")

class ModsTestCase(BaseCMSTestCase, WebTest):

    mods_template = """\
<?xml version="1.0"?>\
<modsCollection xmlns="http://www.loc.gov/mods/v3" \
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" \
xsi:schemaLocation="http://www.loc.gov/mods/v3 \
http://www.loc.gov/standards/mods/v3/mods-3-5.xsd"><mods>\
<titleInfo><title>Buddhist Translators Workbench</title></titleInfo>\
<typeOfResource>text</typeOfResource>\
<genre authority="marcgt">dictionary</genre>\
<name type="personal"><namePart type="family">Gómez</namePart>\
<namePart type="given">Luis</namePart>\
<role><roleTerm type="code" authority="marcrelator">edc</roleTerm></role>\
</name>\
<name type="personal"><namePart type="family">Lugli</namePart>\
<namePart type="given">Ligeia</namePart>\
<role><roleTerm type="code" authority="marcrelator">edc</roleTerm></role>\
</name>\
<originInfo><edition>version {version}</edition>\
<place><placeTerm type="text">Berkeley</placeTerm></place>\
<publisher>Mangalam Research Center for Buddhist Languages</publisher>\
<dateCreated>{year}</dateCreated><issuance>continuing</issuance></originInfo>\
<location><url dateLastAccessed="2015-01-02">{url}</url>\
</location></mods></modsCollection>\n"""

    def setUp(self):
        super(ModsTestCase, self).setUp()
        translation.activate('en-us')
        self.mods_url = reverse("core_mods")

    def assertValid(self, mods):
        self.assertTrue(
            util.validate_with_xmlschema(mods_schema_path,
                                         mods.decode("utf-8")),
            "the resulting data should be valid")

    def test_missing_access_date(self):
        """
        Tests that if the access-date parameter is missing, we get a
        reasonable error message.
        """

        response = self.app.get(self.mods_url, expect_errors=True)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, "access-date is a required parameter")

    def test_basic(self):
        """
        Tests that generating a MODS works.
        """
        response = self.app.get(self.mods_url,
                                params={"access-date": "2015-01-02"})

        xml_params = {
            'version': util.version(),
            'year': '2012-' + str(datetime.date.today().year),
            'url': "http://testserver/"
        }

        self.assertEqual(
            response.text,
            self.mods_template.format(**xml_params))
        self.assertValid(response.body)
