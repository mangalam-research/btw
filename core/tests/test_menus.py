import re
import os

from django.core.urlresolvers import reverse
from django_webtest import WebTest
from django.contrib.auth import get_user_model
from django.test.utils import override_settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from bibliography.models import PrimarySource
from lib.util import DisableMigrationsMixin

dirname = os.path.dirname(__file__)
user_model = get_user_model()

def reverse_to_re(name):
    return re.compile("^" + re.escape(reverse(name)) + "$")

#
# IMPORTANT
#
# Django CMS caches a fair amount of information. This includes menu
# information. Unfortunately, this causes (some of) these tests to
# fail if they are run with the rest of the BTW test suite. Therefore,
# these tests must be run in a *separate* test run.
#

@override_settings(ACCOUNT_EMAIL_VERIFICATION="none")
class MenuTestCase(DisableMigrationsMixin, WebTest):

    saved_menus = None

    def setUp(self):
        super(MenuTestCase, self).setUp()
        from django.utils import translation
        translation.activate('en-us')

        self.admin = user_model.objects.create_superuser(
            username='admin', email="foo@foo.foo", password='test')

        self.scribe = user_model.objects.create_user(
            username='test', password='test')
        g = Group.objects.get(name='scribe')
        g.user_set.add(self.scribe)
        g.save()

        from lib import cmsutil
        cmsutil.refresh_cms_apps()

        from cms.api import create_page
        self.home_page = \
            create_page("Home", "generic_page.html",
                        "en-us")
        self.home_page.toggle_in_navigation()
        self.home_page.publish('en-us')
        self.lexicography_page = \
            create_page("Lexicography", "generic_page.html",
                        "en-us", apphook='LexicographyApp')
        self.lexicography_page.toggle_in_navigation()
        self.lexicography_page.publish('en-us')
        self.bibliography_page = \
            create_page("Bibliography", "generic_page.html",
                        "en-us", apphook='BibliographyApp')
        self.bibliography_page.toggle_in_navigation()
        self.bibliography_page.publish('en-us')

        # What we are doing here is saving the menu setup on the first
        # run of this test. We will use it in tearDown to restore the
        # menus to their pre-expansion values. We need to do this
        # because the primary keys of the pages that carry apps will
        # change with each test. However, without doing this, the
        # expanded menus will refer to primary keys that no longer
        # exist.
        from menus.menu_pool import menu_pool
        menu_pool.discover_menus()
        if self.saved_menus is None:
            self.saved_menus = dict(menu_pool.menus)

    def tearDown(self):
        super(MenuTestCase, self).tearDown()

        # This is needed to ensure that Django CMS does not blow a fuse
        # when we load fixtures for the next test.
        from cms.utils.permissions import set_current_user
        set_current_user(None)

        # This resets the menu pool to pre-expansion values.
        from menus.menu_pool import menu_pool
        menu_pool.menus = self.saved_menus
        menu_pool._expanded = False
        menu_pool.clear()

    def test_home(self):
        """
        Test that there is a link to the home.
        """
        response = self.app.get(reverse('pages-root'))
        response.click(href=reverse_to_re('pages-root'))

    def test_lexicography_main(self):
        """
        Test that there is a link to main page of the lexicography app.
        """
        response = self.app.get(reverse('pages-root'))
        response.click(href=reverse_to_re('lexicography_main'))

    def test_lexicography_new_for_scribes(self):
        """
        Test that there is a link to create new articles if the user is a
        scribe.
        """
        response = self.app.get(reverse('pages-root'), user=self.scribe)
        response.click(href=reverse_to_re('lexicography_entry_new'))

    def test_lexicography_new_for_others(self):
        """
        Test that there is no link to create new articles if the user is
        not a scribe.
        """
        response = self.app.get(reverse('pages-root'))
        with self.assertRaisesRegexp(IndexError,
                                     "^No matching elements found"):
            response.click(href=reverse_to_re('lexicography_entry_new'))

    def test_bibliography_search(self):
        """
        Test that there is a link to search bibliographical articles.
        """
        response = self.app.get(reverse('pages-root'))
        response.click(href=reverse_to_re('bibliography_search'))

    def test_bibliography_manage_for_user_without_permissions(self):
        """
        Test that there is no link to search bibliographical articles for
        a user who lacks the permissions.
        """
        response = self.app.get(reverse('pages-root'), user=self.scribe)
        with self.assertRaisesRegexp(IndexError,
                                     "^No matching elements found"):
            response.click(href=reverse_to_re('bibliography_manage'))

    def test_bibliography_manage_for_user_with_permissions(self):
        """
        Test that there is a link to search bibliographical articles for
        a user who has the permissions.
        """
        manage_bib = user_model.objects.create_user(
            username='manager', password='manager')
        manage_bib.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(PrimarySource),
            codename="add_primarysource"))
        manage_bib.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(PrimarySource),
            codename="change_primarysource"))
        manage_bib.save()

        response = self.app.get(reverse('pages-root'), user=manage_bib)
        response.click(href=reverse_to_re('bibliography_manage'))

    def test_user_menu_shows_user_name(self):
        """
        Test that the user menu shows the user name for logged in users.
        """
        response = self.app.get(reverse('pages-root'), user=self.scribe)
        candidates = response.lxml.xpath(
            "//div[@id='btw-site-navigation']"
            "//ul[contains(@class, ' navbar-right')]/li/a")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].text.strip(), "test")

    def test_user_menu_shows_login_if_the_user_is_not_logged_in(self):
        """
        Test that the user menu shows "Log in" when the user is not logged in.
        """
        response = self.app.get(reverse('pages-root'))
        candidates = response.lxml.xpath(
            "//div[@id='btw-site-navigation']"
            "//ul[contains(@class, ' navbar-right')]/li/a")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].text.strip(), "Log in")

    def test_user_menu_does_not_show_admin_menu_to_non_superusers(self):
        """
        Test that the user menu does not show the admin menu item for users
        who are not super users.
        """
        response = self.app.get(reverse('pages-root'), user=self.scribe)
        with self.assertRaisesRegexp(IndexError,
                                     "^No matching elements found"):
            response.click(href=reverse_to_re('full-admin:index'))

    def test_user_menu_shows_admin_menu_to_superusers(self):
        """
        Test that the user menu shows the admin menu item for users who
        are super users.
        """
        response = self.app.get(reverse('pages-root'),
                                user=user_model.objects.get(username="admin"))
        response.click(href=reverse_to_re('full-admin:index'))

    def test_user_menu_shows_logout(self):
        """
        Test that the user menu shows a logout menu to logged in users.
        """
        response = self.app.get(reverse('pages-root'), user=self.scribe)
        response.click(href=reverse_to_re('logout'))
