from django_webtest import WebTest
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true
from .util import TestMeta, replay

User = get_user_model()
server_name = "http://testserver"


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
