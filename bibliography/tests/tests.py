import os
import urllib2
import httplib
from functools import wraps
import time

from django_webtest import WebTest
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.conf import settings

import nose.tools as noz
import mock

dirname = os.path.dirname(__file__)

User = get_user_model()
server_name = "http://testserver"


def get_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def record(f):
    """
    Use this decorator to mark a test as being in recording mode.

    """
    f.record = True
    return f


def replay(entity):
    """
    Use this decorator to mark a test as being in replay mode. This
    decorator optionally takes an argument. So it can be used this way::

         @replay
         def foo(...):
            ...

    Or like this::

         @replay(proxy)
         def foo(...):

    The ``proxy`` parameter is a URL to a proxy to use. If this
    parameter is not used, the test suite will start a ``mitmproxy``
    instance. If it is used, then the test suite will not start a
    proxy.

    """
    # The tests with callable allow us to use this decorator
    # as @replay(proxy...) and @replay.
    def _replay(f):
        f.replay = True
        if entity is not None and not callable(entity):
            f.proxy = entity
        return f

    if callable(entity):
        return _replay(entity)

    return _replay


def raw(f):
    """
    Use this decorator to mark a test as being in raw mode. In raw
    mode no proxiying is done, and no error will be raised if the
    tested code uses ``urllib2.urlopen``.

    """
    f.raw = True
    return f


def _proxify(file_name, f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        fname = os.path.join(dirname, "proxy_files",
                             file_name + "." + f.__name__)

        import subprocess
        server = settings.ZOTERO_SETTINGS.get('server',
                                              "https://api.zotero.org/")
        # Set the environment to proxy through mitmproxy.
        prev_https_proxy = os.environ.get('https_proxy', None)
        proxy = None
        if not hasattr(f, "proxy"):
            port = get_port()
            cmd = ["mitmdump", "-a", "-q", "-F", server, "-p", str(port)]
            if hasattr(f, "record"):
                cmd += ["-s", os.path.join(dirname, "proxy_rewrite.py"),
                        "-w", fname]
            else:
                cmd += ["--no-pop", "-S", fname]

            proxy = subprocess.Popen(cmd)
            if proxy.returncode:
                raise Exception("can't start mitmdump")

            # We need to check that the proxy is ready to work.
            os.environ['https_proxy'] = "https://localhost:" + str(port)
        else:
            os.environ['https_proxy'] = f.proxy

        ready = False
        while not ready:
            try:
                urllib2.urlopen(server)
                ready = True
            except urllib2.URLError:
                time.sleep(0.1)

        try:
            ret = f(*args, **kwargs)
        finally:
            if proxy is not None:
                proxy.kill()
            if prev_https_proxy:
                os.environ['https_proxy'] = prev_https_proxy

        return ret

    return wrapper

urlopen_patcher = mock.patch('bibliography.utils.urllib2.urlopen')


def no_net_decorator(f):
    """
    This decorator will raise an exception if the test decorated by it
    accesses ``urllib2.urlopen``.

    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        urlopen_mock = urlopen_patcher.start()

        try:
            ret = f(*args, **kwargs)
        finally:
            urlopen_patcher.stop()
            if urlopen_mock.called:
                raise Exception("unexpected call to urllib2.urlopen")
        return ret

    return wrapper


class TestMeta(type):
    def __new__(meta, name, bases, dct):
        """
        Scan the class to be created for test methods that have been
        decorated with ``@replay``, ``@record`` and ``@raw``. Test
        methods are those whose name begins with ``test_``:

        * Methods decorated with ``@replay`` and ``@record`` are
          wrapped by :func:`_proxify`.

        * Methods decorated with ``@raw`` are left alone.

        * Other methods are wrapped by ``no_net_decorator``. In other
        words, any undecorated method that tries to access
        ``urllib2.urlopen`` will raise an error.

        """
        for (key, value) in dct.items():
            if key.startswith("test_"):
                if hasattr(value, "record") or hasattr(value, "replay"):
                    dct[key] = _proxify(name, value)
                elif hasattr(value, "raw"):
                    pass
                else:
                    dct[key] = no_net_decorator(value)
        return super(TestMeta, meta).__new__(meta, name, bases, dct)


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

        noz.assert_equal(response.status_code, 403)

    def test_search(self):
        """
        Tests that when the user is logged it, doing an AJAX request on
        the search URL or loading the page yields a 200 response.
        """
        # login the test user
        response = self.client.login(username=u'test', password=u'test')

        noz.assert_true(response)

        response = self.client.get(self.search_url)

        noz.assert_equal(response.status_code, 200)

        # test ajax get call without any data
        response = self.client.get(self.search_url,
                                   {},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        noz.assert_equal(response.status_code, 200)

    @replay
    def test_exec(self):
        """
        Tests that a logged in user gets redirected to the pagination view
        upon posting to exec.
        """
        response = self.client.login(username=u'test', password=u'test')

        noz.assert_true(response)

        response = self.client.post(self.exec_url,
                                    {'library': 5, 'keyword': 'testtest'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # Should get redirected to the pagination view.
        noz.assert_equal(response.status_code, 302)
        noz.assert_true(response.has_header('Location'))
        noz.assert_equal(response['Location'], self.results_url)


class TestResultsView(BaseTest):
    """
    Tests for the results view.
    """
    def test_not_logged(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.client.get(self.results_url)
        noz.assert_equal(response.status_code, 403)

    def test_logged(self):
        """
        Authenticated, without/with session data.
        """

        # Log in.
        response = self.client.login(username=u'test', password=u'test')
        noz.assert_true(response)

        # Test the authenticated session object without results list
        response = self.client.get(self.results_url)
        noz.assert_equal(response.status_code, 500)

        # Populate the session requirements.
        session_obj = self.client.session
        session_obj['results_list'] = []
        session_obj.save()

        # Test authenticated session with results list.
        response = self.client.get(self.results_url)
        noz.assert_equal(response.status_code, 200)


class TestSyncView(BaseTest):
    """
    Tests for sync view.
    """
    def test_not_logged(self):
        """
        Test that the response is 403 when the user is not logged in.
        """
        response = self.client.get(self.sync_url)
        noz.assert_equal(response.status_code, 403)

    def test_logged(self):
        """
        Authenticated without/with sync data.
        """

        # Log in.
        response = self.client.login(username=u'test', password=u'test')
        noz.assert_true(response)

        # Test the response we get without sync data.
        response = self.client.post(self.sync_url)
        noz.assert_equal(response.status_code, 500)

        # Populate the sync requirements ('enc' should be in query dict).
        # Empty upload without session variable for results.
        response = self.client.post(self.sync_url, {'enc': u''})
        noz.assert_equal(response.status_code, 500)
        noz.assert_equal(response.content,
                         "ERROR: session data or query parameters incorrect.")

        # populate the session requirements.
        session_obj = self.client.session
        session_obj['results_list'] = ['test']
        session_obj.save()

        # rerun the assertion to test for a different error string.
        response = self.client.post(self.sync_url, {
            'enc': u''})  # empty upload with a session variable for results.
        noz.assert_equal(response.status_code, 500)
        noz.assert_equal(response.content,
                         'ERROR: malformed data cannot be copied.')

        # populate the sync requirements ('enc' should be in query dict).
        response = self.client.post(self.sync_url, {
            'enc': u'nilakhyaNILAKHYA'})
        noz.assert_equal(response.status_code, 200)
        noz.assert_equal(response.content,
                         'ERROR: Item not in result database.')
