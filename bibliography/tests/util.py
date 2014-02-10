from functools import wraps
import time
import urllib2
import os

import mock

from django.conf import settings

dirname = os.path.dirname(__file__)


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
    fname = os.path.join(dirname, "proxy_files",
                         file_name + "." + f.__name__)

    # Early error if the file we're supposed to read does not exist.
    if hasattr(f, "replay") and not os.path.exists(fname):
        raise Exception(fname + " does not exist.")

    @wraps(f)
    def wrapper(*args, **kwargs):

        import subprocess
        server = settings.ZOTERO_SETTINGS.get('server',
                                              "https://api.zotero.org/")
        # Set the environment to proxy through mitmproxy.
        prev_https_proxy = os.environ.get('https_proxy', None)
        proxy = None

        # This flushes the previous opener that may have been
        # installed.  We must do this so that urllib2 picks up the new
        # https_proxy configuration.
        urllib2.install_opener(urllib2.build_opener())

        if not hasattr(f, "proxy"):
            port = get_port()

            cmd = ["mitmdump", "-a", "-q", "-F", server, "-p", str(port)]
            if hasattr(f, "record"):
                cmd += ["-s", os.path.join(dirname, "proxy_rewrite.py"),
                        "-w", fname]
            else:
                cmd += ["--no-pop", "-S", fname]

            proxy = subprocess.Popen(cmd)
            if proxy.poll():
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
            except urllib2.URLError as e:
                if proxy.poll():
                    raise Exception("can't start mitmdump")
                time.sleep(0.1)

        try:
            ret = f(*args, **kwargs)
        finally:
            if proxy is not None:
                proxy.kill()
            if prev_https_proxy is not None:
                os.environ['https_proxy'] = prev_https_proxy
            else:
                del os.environ['https_proxy']

        return ret

    return wrapper

urlopen_patcher = mock.patch('bibliography.zotero.urllib2.urlopen')


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
