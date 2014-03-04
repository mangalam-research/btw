from django_webtest import WebTest
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true
import mock

from .util import TestMeta, replay
from . import mock_zotero
from ..models import Item

User = get_user_model()

# Turn on long messages. This will apply to all assertions unless turned off
# somewhere else.
assert_equal.im_self.longMessage = True


class BaseTest(WebTest):
    __metaclass__ = TestMeta

    def __init__(self, *args, **kwargs):
        super(BaseTest, self).__init__(*args, **kwargs)
        self.client = None
        self.user = None
        self.search_url = reverse('bibliography_search')
        self.exec_url = reverse('bibliography_exec')
        self.results_url = reverse('bibliography_results')
        self.sync_url = reverse('bibliography_sync')
        self.title_url = reverse('bibliography_title')
        self.login_url = reverse('login')

    def setUp(self):
        self.client = Client()
        # create test user with zotero profile setup.
        self.user = User.objects.create_user(username='test', password='test')

    def tearDown(self):
        self.user.delete()


class TestSearchView(BaseTest):

    """
    Tests for the search view.
    """

    def test_search_not_logged_in(self):
        """
        Tests that the response is 403 when the user is not logged in.
        """
        # the user is not logged in.
        response = self.client.get(self.search_url, {},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        assert_equal(response.status_code, 403)

    @replay
    def test_search(self):
        """
        Tests that when the user is logged in, doing an AJAX request on
        the search URL or loading the page yields a 200 response.
        """
        # login the test user
        response = self.client.login(username=u'test', password=u'test')

        assert_true(response)

        response = self.client.get(self.search_url)

        assert_equal(response.status_code, 200)

        # test ajax get call without any data
        response = self.client.get(self.search_url,
                                   {},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        assert_equal(response.status_code, 200)

    @replay
    def test_exec(self):
        """
        Tests that a logged in user gets redirected to the pagination view
        upon posting to exec.
        """
        response = self.client.login(username=u'test', password=u'test')

        assert_true(response)

        response = self.client.post(self.exec_url,
                                    {'library': 5, 'keyword': 'testtest'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # Should get redirected to the pagination view.
        self.assertRedirects(response, self.results_url)


class TestResultsView(BaseTest):

    """
    Tests for the results view.
    """

    def test_not_logged(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.client.get(self.results_url)
        assert_equal(response.status_code, 403)

    def test_logged(self):
        """
        Authenticated, without/with session data.
        """

        # Log in.
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        # Test the authenticated session object without results list
        response = self.client.get(self.results_url)
        assert_equal(response.status_code, 500)

        # Populate the session requirements.
        session_obj = self.client.session
        session_obj['results_list'] = []
        session_obj.save()

        # Test authenticated session with results list.
        response = self.client.get(self.results_url)
        assert_equal(response.status_code, 200)


class TestSyncView(BaseTest):

    """
    Tests for sync view.
    """

    def test_not_logged(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.client.get(self.sync_url)
        assert_equal(response.status_code, 403)

    def test_logged(self):
        """
        Authenticated without/with sync data.
        """

        # Log in.
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        # Test the response we get without sync data.
        response = self.client.post(self.sync_url)
        assert_equal(response.status_code, 500)

        # Populate the sync requirements ('enc' should be in query dict).
        # Empty upload without session variable for results.
        response = self.client.post(self.sync_url, {'enc': u''})
        assert_equal(response.status_code, 500)
        assert_equal(response.content,
                     "ERROR: session data or query parameters incorrect.")

        # populate the session requirements.
        session_obj = self.client.session
        session_obj['results_list'] = ['test']
        session_obj.save()

        # rerun the assertion to test for a different error string.
        response = self.client.post(self.sync_url, {
            'enc': u''})  # empty upload with a session variable for results.
        assert_equal(response.status_code, 500)
        assert_equal(response.content,
                     'ERROR: malformed data cannot be copied.')

        # populate the sync requirements ('enc' should be in query dict).
        response = self.client.post(self.sync_url, {
            'enc': u'nilakhyaNILAKHYA'})
        assert_equal(response.status_code, 200)
        assert_equal(response.content,
                     'ERROR: Item not in result database.')


mock_records = mock_zotero.Records([
    {
        "itemKey": "1",
        "title": "Title 1",
        "date": "Date 1",
        "creators": [
            {"name": "Name 1 for Title 1"},
            {"firstName": "FirstName 2 for Title 1",
             "lastName": "LastName 2 for Title 1"},
        ]
    },
    {
        "itemKey": "2",
        "title": "Title 2",
        "date": "Date 2",
        "creators": [
            {"name": "Name 1 for Title 2"},
            {"firstName": "FirstName 2 for Title 2",
             "lastName": "LastName 2 for Title 2"},
        ]
    }
])

new_values = [
    {
        "itemKey": "3",
        "title": "Title 3",
        "date": "Date 3",
        "creators": [
            {"name": "Name 1 for Title 3"},
            {"firstName": "FirstName 2 for Title 3",
             "lastName": "LastName 2 for Title 3"},
        ]
    },
    {
        "itemKey": "4",
        "title": "Title 4",
        "date": "Date 4",
        "creators": [
            {"name": "Name 1 for Title 4"},
            {"firstName": "FirstName 2 for Title 4",
             "lastName": "LastName 2 for Title 4"},
        ]
    },
    {
        "itemKey": "5",
        "title": "Title 5",
        "date": "Date 5",
        "creators": [
            {"name": "Name 1 for Title 5"},
            {"firstName": "FirstName 2 for Title 5",
             "lastName": "LastName 2 for Title 5"},
        ]
    }
]


# We use ``side_effect`` for this mock because we need to refetch
# ``mock_records.values`` at run time since we change it for some
# tests.
get_all_mock = mock.Mock(side_effect=lambda: (mock_records.values, {}))
get_item_mock = mock.Mock(side_effect=mock_records.get_item)


@mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                     get_item=get_item_mock)
class TestTitleView(BaseTest):

    """
    Tests for the title view.
    """

    def setUp(self):
        super(TestTitleView, self).setUp()
        get_item_mock.reset_mock()
        get_all_mock.reset_mock()
        mock_records.reset()

    def test_not_logged(self):
        """
        Test that the response is a redirection to the login page when the
        user is not logged in.
        """
        response = self.client.get(self.title_url)
        self.assertRedirects(response, self.login_url +
                             "?next=" + self.title_url)

    def test_logged(self):
        """
        Test that we get a response.
        """
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        response = self.client.get(self.title_url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")

    def test_caching(self):
        """
        Test that accessing this view caches the items we obtain from
        Zotero.
        """
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        assert_equal(Item.objects.all().count(), 0,
                     "no Item object should exist yet")

        response = self.client.get(self.title_url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")

        assert_equal(get_all_mock.call_count, 1,
                     "all items should have been fetched, but only once")
        assert_equal(Item.objects.all().count(), len(mock_records),
                     "all items should have been cached as ``Item``")

    def test_recaching(self):
        """
        Test that a change on the Zotero server propagates to the ``Item``
        objects.
        """
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        assert_equal(Item.objects.all().count(), 0,
                     "no Item object should exist yet")

        response = self.client.get(self.title_url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")

        assert_equal(get_all_mock.call_count, 1,
                     "all items should have been fetched, but only once")
        assert_equal(Item.objects.all().count(), len(mock_records),
                     "all items should have been cached as ``Item``")
        first_length = len(mock_records)

        # Simulate a change on the server.
        mock_records.values = new_values

        response = self.client.get(self.title_url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")

        assert_equal(get_all_mock.call_count, 2,
                     "all items should have been fetched, again")
        assert_equal(Item.objects.all().count(), first_length +
                     len(mock_records),
                     "all items should have been cached as ``Item``")


@mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                     get_item=get_item_mock)
class TestReferenceTitleView(BaseTest):

    """
    Tests for the title view.
    """

    def setUp(self):
        super(TestReferenceTitleView, self).setUp()
        get_item_mock.reset_mock()
        get_all_mock.reset_mock()
        mock_records.reset()

    def test_not_logged(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        url = reverse('bibliography_reference_title', args=("1", ))

        response = self.client.post(url, {"value": "blah"})
        assert_equal(response.status_code, 403)

    def test_logged(self):
        """
        Test that we get a response.
        """

        self.user.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Item),
            codename="change_item"))
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        # We must do this first so that the Item data is cached.
        response = self.client.get(self.title_url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")

        url = reverse('bibliography_reference_title', args=("1", ))

        response = self.client.post(url, {
            "value": "foo"
        })
        assert_equal(response.status_code, 200,
                     "the request should be successful")

    def test_change(self):
        """
        Test that the data is changed in the database.
        """

        self.user.user_permissions.add(Permission.objects.get(
            content_type=ContentType.objects.get_for_model(Item),
            codename="change_item"))
        self.user.save()
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        # We must do this first so that the Item data is cached.
        response = self.client.get(self.title_url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")

        item = Item.objects.get(item_key="1")

        assert_equal(item.reference_title, None,
                     "the reference_title value should be None")

        url = reverse('bibliography_reference_title', args=("1", ))

        response = self.client.post(url, {
            "value": "foo"
        })
        assert_equal(response.status_code, 200,
                     "the request should be successful")
        item = Item.objects.get(item_key="1")

        assert_equal(item.reference_title, "foo",
                     "the reference_title value should be changed")

    def test_no_permission(self):
        """
        Test that a user without the right permissions cannot change a
        reference title.
        """

        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        url = reverse('bibliography_reference_title', args=("1", ))

        response = self.client.post(url, {
            "value": "foo"
        })
        assert_equal(response.status_code, 302, "the request should fail")
