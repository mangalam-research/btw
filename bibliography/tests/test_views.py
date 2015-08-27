# -*- encoding: utf-8 -*-
import json
import urllib

from django_webtest import WebTest
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.utils import translation
from cms.test_utils.testcases import BaseCMSTestCase

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true
import mock

from .util import TestMeta, replay
from . import mock_zotero
from ..models import Item, PrimarySource

User = get_user_model()

# Turn on long messages. This will apply to all assertions unless turned off
# somewhere else.
assert_equal.im_self.longMessage = True

@override_settings(ROOT_URLCONF='bibliography.tests.urls')
class _BaseTest(BaseCMSTestCase, WebTest):
    __metaclass__ = TestMeta

    url = None
    xhr = False

    def __init__(self, *args, **kwargs):
        super(_BaseTest, self).__init__(*args, **kwargs)
        self.client = None
        self.user = None

    def setUp(self):
        super(_BaseTest, self).setUp()
        translation.activate('en-us')
        self.client = Client()
        # create test user with zotero profile setup.
        self.user = User.objects.create_user(username='test', password='test')
        self.noperm = User.objects.create_user(username='noperm',
                                               password='test')
        self.login_url = reverse('login')


class LoginMixin(object):

    def test_not_logged(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.client.get(
            self.url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest' if self.xhr else None)
        assert_equal(response.status_code, 403)

    def test_logged(self):
        """
        Test that we get a response.
        """
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        response = self.client.get(self.url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")


class TestSearchView(_BaseTest, LoginMixin):

    """
    Tests for the search view.
    """

    def setUp(self):
        super(TestSearchView, self).setUp()
        self.url = reverse('bibliography_search')

    # We override the base one.
    def test_not_logged(self):
        """
        Tests that the response is 403 when the user is not logged in.
        """
        # the user is not logged in.
        response = self.client.get(self.url, {},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        assert_equal(response.status_code, 403)

    # We override the base one.
    @replay
    def test_logged(self):
        """
        Tests that when the user is logged in, doing an AJAX request on
        the search URL or loading the page yields a 200 response.
        """
        # login the test user
        response = self.client.login(username=u'test', password=u'test')

        assert_true(response)

        response = self.client.get(self.url)

        assert_equal(response.status_code, 200)

        # test ajax get call without any data
        response = self.client.get(self.url, {},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert_equal(response.status_code, 200)


mock_records = mock_zotero.Records([
    {
        "data":
        {
            "key": "1",
            "title": "Title 1",
            "date": "Date 1",
            "creators": [
                {"name": "Name 1 for Title 1"},
                {"firstName": "FirstName 2 for Title 1",
                 "lastName": "LastName 2 for Title 1"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "2",
            "title": "Title 2",
            "date": "Date 2",
            "creators": [
                {"name": "Name 1 for Title 2"},
                {"firstName": "FirstName 2 for Title 2",
                 "lastName": "LastName 2 for Title 2"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo2.com",
                "type": "text/html"
            }
        }
    }
])

new_values = [
    {
        "data":
        {
            "key": "3",
            "title": "Title 3",
            "date": "Date 3",
            "creators": [
                {"name": "Name 1 for Title 3"},
                {"firstName": "FirstName 2 for Title 3",
                 "lastName": "LastName 2 for Title 3"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo3.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "4",
            "title": "Title 4",
            "date": "Date 4",
            "creators": [
                {"name": "Name 1 for Title 4"},
                {"firstName": "FirstName 2 for Title 4",
                    "lastName": "LastName 2 for Title 4"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo4.com",
                "type": "text/html"
            }
        }
    },
    {
        "data":
        {
            "key": "5",
            "title": "Title 5",
            "date": "Date 5",
            "creators": [
                {"name": "Name 1 for Title 5"},
                {"firstName": "FirstName 2 for Title 5",
                 "lastName": "LastName 2 for Title 5"},
            ]
        },
        "links": {
            "alternate": {
                "href": "https://www.foo5.com",
                "type": "text/html"
            }
        }
    }
]


# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: mock_records.values)
get_item_mock = mock.Mock(side_effect=mock_records.get_item)


class _PatchZoteroTest(_BaseTest):

    def setUp(self):
        super(_PatchZoteroTest, self).setUp()
        get_item_mock.reset_mock()
        get_all_mock.reset_mock()
        mock_records.reset()
        self.patch = mock.patch.multiple("bibliography.zotero.Zotero",
                                         get_all=get_all_mock,
                                         get_item=get_item_mock)
        self.patch.start()
        from ..tasks import fetch_items
        fetch_items()

    def tearDown(self):
        self.patch.stop()
        super(_PatchZoteroTest, self).tearDown()

class TestItemsView(_PatchZoteroTest):

    """
    Tests for the items view.
    """

    def setUp(self):
        super(TestItemsView, self).setUp()
        self.url = reverse(
            'bibliography_items',
            args=(Item.objects.get(item_key="1").pk,))

    def test_correct_data(self):
        response = self.app.get(self.url, user=u'test')
        data = json.loads(response.body)
        assert_equal(data["title"], "Title 1")
        assert_equal(data["date"], "Date 1")
        assert_equal(data["creators"],
                     "Name 1 for Title 1, LastName 2 for Title 1")
        assert_equal(data["pk"], Item.objects.get(item_key="1").pk)


class TestManageView(_PatchZoteroTest, LoginMixin):

    """
    Tests for the manage view.
    """

    def setUp(self):
        super(TestManageView, self).setUp()
        self.url = reverse('bibliography_manage')

    # Override the base one.
    def test_not_logged(self):
        """
        Test that the response is a redirection to the login page when the
        user is not logged in.
        """
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, self.login_url + "?" +
                             urllib.urlencode({"next": self.url}))

class TestItemTableView(_PatchZoteroTest, LoginMixin):

    """
    Tests for the ItemTable view.
    """
    #
    # Note that this test is not testing the nitty gritty of
    # django-datatables-view. So don't go looking for such tests here.
    #

    def setUp(self):
        super(TestItemTableView, self).setUp()
        self.url = reverse('bibliography_item_table')


class TestItemPrimarySourcesView(_PatchZoteroTest, LoginMixin):

    """
    Tests for the item_primary_sources view.
    """

    #
    # Note that this test is not testing the nitty gritty of
    # django-datatables-view. So don't go looking for such tests here.
    #

    def setUp(self):
        super(TestItemPrimarySourcesView, self).setUp()
        #
        # When used in the app, caching should have occured due to
        # other views.
        #
        self.url = reverse(
            'bibliography_item_primary_sources',
            args=(Item.objects.get(item_key="1").pk,))

    def test_post(self):
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        response = self.client.post(self.url)
        assert_equal(response.status_code, 405, "the request should fail")


class PrimarySourceMixin(object):

    get_headers = {"Accept": "application/x-form"}
    initial_values = None
    # This is a fake value selected to shut jslint up.
    submit_method = id
    no_permission_failure_status = 403

    def make_submit_headers(self, form):
        ret = dict(self.get_headers)
        ret["Content-Type"] = \
            "application/x-www-form-urlencoded; charset=UTF-8"
        ret["X-CSRFToken"] = str(form['csrfmiddlewaretoken'].value)
        return ret

    def submit(self, form, *args, **kwargs):
        submit_headers = self.make_submit_headers(form)
        headers = kwargs.pop("headers", {})
        submit_headers.update(headers)
        return self.submit_method(headers=submit_headers,
                                  *args, **kwargs)

    def test_no_permission(self):
        """
        Test that a user without the right permissions cannot create a
        primary source.
        """

        response = self.client.login(username=u'noperm', password=u'test')
        assert_true(response)

        response = self.client.get(self.url)
        assert_equal(response.status_code, self.no_permission_failure_status,
                     "the request should fail")

    def test_form(self):
        """
        Test that the form is properly initialized.
        """
        response = self.app.get(
            self.url, headers=self.get_headers, user="test")
        assert_equal(response.status_code, 200)
        form = response.form
        assert_equal(form['reference_title'].value,
                     self.initial_values.reference_title)
        assert_equal(form['genre'].value, self.initial_values.genre)

    def test_post_valid_form(self):
        """
        Test that a valid form passes through, and creates an object.
        """
        count_before = PrimarySource.objects.all().count()
        response = self.app.get(
            self.url, headers=self.get_headers, user="test")
        assert_equal(response.status_code, 200)
        form = response.form
        form['reference_title'] = 'Flibble'
        form['genre'] = 'SH'
        response = self.submit(form, self.url, params=form.submit_fields())
        assert_equal(response.status_code, 200)

        source = self.element_of_interest()
        assert_equal(source.reference_title, "Flibble")
        assert_equal(source.genre, "SH")
        assert_equal(source.item.pk, Item.objects.get(item_key="1").pk)
        self.assert_count_after_valid_post(count_before)

    def test_post_title_normalized(self):
        """
        Test that a valid form normalizes a title that has leading or
        trailing spaces in it.
        """
        response = self.app.get(
            self.url, headers=self.get_headers, user="test")
        assert_equal(response.status_code, 200)
        form = response.form
        form['reference_title'] = '  Bar  '
        form['genre'] = 'SH'
        response = self.submit(form, self.url, params=form.submit_fields())
        assert_equal(response.status_code, 200)

        source = self.element_of_interest()
        assert_equal(source.reference_title, "Bar")
        assert_equal(source.genre, "SH")
        assert_equal(source.item.pk, Item.objects.get(item_key="1").pk)

    def test_post_form_empty_title(self):
        """
        Test that an empty title yields an error.
        """
        response = self.app.get(
            self.url, headers=self.get_headers, user="test")
        assert_equal(response.status_code, 200)
        form = response.form
        form['reference_title'] = ''
        form['genre'] = 'SH'
        response = self.submit(form, self.url, params=form.submit_fields(),
                               expect_errors=True)
        self.assertContains(
            response,
            '<span id="error_id_reference_title_1" class="error-msg">'
            'This field is required.</span>',
            status_code=400)

    def test_post_form_duplicate_title(self):
        """
        Test that a duplicate title yields an error.
        """
        response = self.app.get(
            self.url, headers=self.get_headers, user="test")
        assert_equal(response.status_code, 200)
        form = response.form
        form['reference_title'] = "Foo"
        form['genre'] = 'SU'
        response = self.submit(form, self.url, params=form.submit_fields(),
                               expect_errors=True)
        self.assertContains(
            response,
            '<span id="error_id_reference_title_1" class="error-msg">'
            'Primary source with this Reference title already exists.</span>',
            status_code=400)

    def test_post_latin1_charset(self):
        """
        Test that a valid form passes through, and creates an correct
        object, even if the charset is not utf-8.
        """
        count_before = PrimarySource.objects.all().count()
        response = self.app.get(
            self.url, headers=self.get_headers, user="test")
        assert_equal(response.status_code, 200)
        form = response.form
        form['reference_title'] = u'Flébble'.encode('latin-1')
        form['genre'] = 'SH'
        response = self.submit(
            form, self.url, params=form.submit_fields(),
            headers={
                'Content-Type':
                'application/x-www-form-urlencoded; charset=latin1'
            }
        )
        assert_equal(response.status_code, 200)

        source = self.element_of_interest()
        assert_equal(source.reference_title, u"Flébble")
        assert_equal(source.genre, "SH")
        assert_equal(source.item.pk, Item.objects.get(item_key="1").pk)
        self.assert_count_after_valid_post(count_before)


class TestNewPrimarySourcesView(_PatchZoteroTest, PrimarySourceMixin,
                                LoginMixin):

    """
    Tests for the new_primary_sources view.
    """

    no_permission_failure_status = 302

    def setUp(self):
        super(TestNewPrimarySourcesView, self).setUp()
        #
        # When used in the app, caching should have occured due to
        # other views.
        #
        item = Item.objects.get(item_key="1")
        self.url = reverse(
            'bibliography_new_primary_sources',
            args=(item.pk,))
        source = PrimarySource(item=Item.objects.get(item_key="1"),
                               reference_title="Blah",
                               genre="SU")
        source.save()
        source = PrimarySource(item=Item.objects.get(item_key="1"),
                               reference_title="Foo",
                               genre="SU")
        source.save()
        self.initial_values = PrimarySource(item=item, reference_title='',
                                            genre='SU')
        self.submit_method = self.app.post
        self.user.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(PrimarySource),
            codename="add_primarysource"))

    def element_of_interest(self):
        return PrimarySource.objects.all().last()

    def assert_count_after_valid_post(self, count_before):
        assert_equal(PrimarySource.objects.all().count(), count_before + 1)


class TestPrimarySourcesView(_PatchZoteroTest, PrimarySourceMixin, LoginMixin):

    """
    Tests for the primary_sources view.
    """

    def setUp(self):
        super(TestPrimarySourcesView, self).setUp()
        #
        # When used in the app, caching should have occured due to
        # other views.
        #
        source = PrimarySource(item=Item.objects.get(item_key="1"),
                               reference_title="Blah",
                               genre="SU")
        self.initial_values = source
        source.save()
        source = PrimarySource(item=Item.objects.get(item_key="1"),
                               reference_title="Foo",
                               genre="SU")
        source.save()
        self.submit_method = self.app.put
        self.url = reverse(
            'bibliography_primary_sources',
            args=(PrimarySource.objects.all()[0].pk,))
        self.user.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(PrimarySource),
            codename="change_primarysource"))

    def element_of_interest(self):
        return PrimarySource.objects.get(pk=self.initial_values.pk)

    def assert_count_after_valid_post(self, count_before):
        assert_equal(PrimarySource.objects.all().count(), count_before)

    def test_logged(self):
        """
        Test that we get a response.
        """
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        response = self.app.get(
            self.url, headers=self.get_headers, user='test')
        assert_equal(response.status_code, 200,
                     "the request should be successful")

    def test_correct_data(self):
        response = self.app.get(
            self.url, {'Accept': 'application/json'}, user='test')
        data = json.loads(response.body)
        assert_equal(data["reference_title"], "Blah")
        assert_equal(data["genre"], "SU")
        item = Item.objects.get(item_key="1")
        assert_equal(data["item"]["pk"], item.pk)
        assert_equal(data["item"]["title"], item.title)
        assert_equal(data["item"]["creators"], item.creators)
        assert_equal(data["item"]["date"], item.date)
