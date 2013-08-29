from django.test import Client
from django.contrib.auth import get_user_model
#from django.contrib.auth.models import User
from .models import ZoteroUser

# import nose for tests.
import nose.tools as noz

User = get_user_model()

# code to test the bibsearch views
class TestSearchView(object):
    """ tests the search view at /search/ for functionality """

    def __init__(self, *args, **kwargs):
        self.client = None
        self.user = None
        super(TestSearchView, self).__init__(*args, **kwargs)

    def setup(self):
        self.client = Client()
        # create test user with zotero profile setup.
        self.user = User.objects.create_user(username='test', password='test')

    def testGet(self):
        """Unauthenticated response(url: /search/)"""
        #self.client.logout()
        # the user is not logged in.
        response = self.client.get('http://testserver/search/')

        noz.assert_equal(response.status_code, 403)

    def testAuthGET(self):
        """Authenticated response without zotero profile (url: /search/)"""

        # login the test user
        response = self.client.login(username=u'test', password=u'test')

        noz.assert_equal(response, True)

        response = self.client.get('http://testserver/search/')

        noz.assert_equal(response.status_code, 500)

    def testAuthGET2(self):
        """Authenticated AJAX or GET with zotero profile (url: /search/)"""
        # create a dummy profile
        zo = ZoteroUser(btw_user=self.user, uid="123456", api_key="abcdef")
        zo.save()

        # login the test user
        response = self.client.login(username=u'test', password=u'test')

        noz.assert_equal(response, True)

        response = self.client.get('http://testserver/search/')

        noz.assert_equal(response.status_code, 200)

        # test ajax get call without any data
        response = self.client.get('http://testserver/search/',
                                   {},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        noz.assert_equal(response.status_code, 200)
        zo.delete()

    def testAuthGET3(self):
        zo = ZoteroUser(btw_user=self.user, uid="123456", api_key="abcdef")
        zo.save()
        response = self.client.login(username=u'test', password=u'test')

        noz.assert_equal(response, True)

        # test ajax get call with dummy data
        response = self.client.post('http://testserver/search/exec/',
                                    {'library': 5, 'keyword': 'testtest'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # should get redirected to the pagination view
        noz.assert_equal(response.status_code, 302)
        noz.assert_equal(response.has_header('Location'), True)
        noz.assert_equal(response['Location'],
                         "http://testserver/search/results/")
        zo.delete()

    def tearDown(self):
        user = User.objects.get(username='test')
        user.delete()


class TestResultsView(object):
    """ Tests for results view """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='test')

    def testEmptySession(self):
        """ Unauthenticated, empty session (url: /search/results/) """

        response = self.client.get("http://testserver/search/results/")
        noz.assert_equal(response.status_code, 403)

    def testValidSession(self):
        """Authenticated, without/with session data (url: /search/results/)"""

        # test authentication
        response = self.client.login(username=u'test', password=u'test')
        noz.assert_equal(response, True)

        # test the authenticated session object without results list
        response = self.client.get("http://testserver/search/results/")
        noz.assert_equal(response.status_code, 500)

        # populate the session requirements.
        session_obj = self.client.session
        session_obj['results_list'] = []
        session_obj.save()

        # test authenticated session with results list
        response = self.client.get("http://testserver/search/results/")
        noz.assert_equal(response.status_code, 200)

    def tearDown(self):
        user = User.objects.get(username='test')
        user.delete()


class TestSyncView(object):
    """ Tests for sync view """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='test', password='test')

    def testEmptySession(self):
        """ Unauthenticated response (url: /search/sync/) """

        response = self.client.get("http://testserver/search/sync/")
        noz.assert_equal(response.status_code, 403)

    def testValidSession(self):
        """ Authenticated without/with sync data(url: /search/sync/) """

        # test authentication
        response = self.client.login(username=u'test', password=u'test')
        noz.assert_equal(response, True)

        # test the authenticated response object without sync data
        response = self.client.post("http://testserver/search/sync/")
        noz.assert_equal(response.status_code, 500)

        # populate the sync requirements ('enc' should be in query dict).
        response = self.client.post("http://testserver/search/sync/", {
            'enc': u''})  # empty upload without session variable for results.
        noz.assert_equal(response.status_code, 500)
        noz.assert_equal(
            response.content, 'ERROR: sync data i/o error.')

        # populate the session requirements.
        session_obj = self.client.session
        session_obj['results_list'] = ['test']
        session_obj.save()

        # rerun the assertion to test for a different error string.
        response = self.client.post("http://testserver/search/sync/", {
            'enc': u''})  # empty upload with a session variable for results.
        noz.assert_equal(response.status_code, 500)
        noz.assert_equal(
            response.content, 'Error: malformed data cannot be copied.')


        # populate the sync requirements ('enc' should be in query dict).
        response = self.client.post("http://testserver/search/sync/", {
            'enc': u'nilakhyaNILAKHYA'})
        noz.assert_equal(response.status_code, 200)
        noz.assert_equal(
            response.content, 'Error: Item not in result database.')

    def tearDown(self):
        user = User.objects.get(username='test')
        user.delete()
