from django_webtest import WebTest
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true
import mock

from .util import TestMeta, replay
from ..models import Item

User = get_user_model()
server_name = "http://testserver"

# Turn on long messages. This will apply to all assertions unless turned off
# somewhere else.
assert_equal.im_self.longMessage = True


class BaseTest(WebTest):
    __metaclass__ = TestMeta

    def __init__(self, *args, **kwargs):
        super(BaseTest, self).__init__(*args, **kwargs)
        self.client = None
        self.user = None
        self.search_url = server_name + reverse('bibliography_search')
        self.exec_url = server_name + reverse('bibliography_exec')
        self.results_url = server_name + reverse('bibliography_results')
        self.sync_url = server_name + reverse('bibliography_sync')
        self.bare_title_url = reverse('bibliography_title')
        self.title_url = server_name + self.bare_title_url
        self.login_url = server_name + reverse('login')

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

    def test_search(self):
        """
        Tests that when the user is logged it, doing an AJAX request on
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
        assert_equal(response.status_code, 302)
        assert_true(response.has_header('Location'))
        assert_equal(response['Location'], self.results_url)


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


class MockRecords(object):

    def __init__(self, values):
        self.values = values

    def get_item(self, itemKey):
        return [x for x in self.values if x["itemKey"] == itemKey][0]

    def __len__(self):
        return len(self.values)

mock_records = MockRecords([
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


class TestTitleView(BaseTest):

    """
    Tests for the title view.
    """

    # We use ``side_effect`` for this mock because we need to refetch
    # ``mock_records.values`` at run time since we change it for some
    # tests.
    get_all_mock = mock.Mock(side_effect=lambda: (mock_records.values, {}))
    get_item_mock = mock.Mock(side_effect=mock_records.get_item)

    def setUp(self):
        super(TestTitleView, self).setUp()
        self.get_item_mock.reset_mock()
        self.get_all_mock.reset_mock()

    def test_not_logged(self):
        """
        Test that the response is a redirection to the login page when the
        user is not logged in.
        """
        response = self.client.get(self.title_url)
        self.assertRedirects(response, self.login_url +
                             "?next=" + self.bare_title_url)

    @mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                         get_item=get_item_mock)
    def test_logged(self):
        """
        Test that we get a response.
        """
        response = self.client.login(username=u'test', password=u'test')
        assert_true(response)

        response = self.client.get(self.title_url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")

    @mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                         get_item=get_item_mock)
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

        assert_equal(self.get_all_mock.call_count, 1,
                     "all items should have been fetched, but only once")
        assert_equal(Item.objects.all().count(), len(mock_records),
                     "all items should have been cached as ``Item``")

    @mock.patch.multiple("bibliography.zotero.Zotero", get_all=get_all_mock,
                         get_item=get_item_mock)
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

        assert_equal(self.get_all_mock.call_count, 1,
                     "all items should have been fetched, but only once")
        assert_equal(Item.objects.all().count(), len(mock_records),
                     "all items should have been cached as ``Item``")
        first_length = len(mock_records)

        # Simulate a change on the server.
        mock_records.values = new_values

        response = self.client.get(self.title_url)
        assert_equal(response.status_code, 200,
                     "the request should be successful")

        assert_equal(self.get_all_mock.call_count, 2,
                     "all items should have been fetched, again")
        assert_equal(Item.objects.all().count(), first_length +
                     len(mock_records),
                     "all items should have been cached as ``Item``")
