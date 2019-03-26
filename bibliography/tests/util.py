from functools import wraps
import time
import urllib.request
import urllib.error
import urllib.parse
import os
import tempfile
import subprocess

import mock

from django.conf import settings
import collections

dirname = os.path.dirname(__file__)

MITMPROXY_CERT_DIR = os.path.join(os.environ['HOME'], ".mitmproxy")

def hash_mitmproxy():
    # Make sure we hash only once.
    if hash_mitmproxy.hashed:
        return

    subprocess.check_call(["c_rehash",
                           os.path.join(os.environ["HOME"], ".mitmproxy")],
                          stdout=open("/dev/null"), stderr=open("/dev/null"))

    hash_mitmproxy.hashed = True

hash_mitmproxy.hashed = False

def check_certs():
    # Make sure we check only once.
    if check_certs.done:
        return

    try:
        subprocess.check_call(["openssl", "x509", "-checkend", "0",
                               "-noout", "-in",
                               os.path.join(MITMPROXY_CERT_DIR,
                                            "mitmproxy-ca-cert.pem")],
                              stdout=open("/dev/null"))
    except subprocess.CalledProcessError:
        raise Exception("""\
The certificate that mitmproxy creates for itself is expired. You \
should remove it and run mitmproxy to create a new certificate.""")

    check_certs.done = True
check_certs.done = False

def get_port():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def record(entity):
    """
    Use this decorator to mark a test as being in recording mode. This
    decorator optionally takes an argument. So it can be used this
    way: :

         @record
         def foo(...):
            ...

    Or like this: :

         @record(proxy)
         def foo(...):

    The ``proxy`` parameter is a URL to a proxy to use. If this
    parameter is not used, the test suite will start a ``mitmproxy``
    instance. If it is used, then the test suite will not start a
    proxy.

    """
    # The tests with callable allow us to use this decorator
    # as @record(proxy...) and @record.
    def _record(f):
        f.record = True
        if entity is not None and not isinstance(entity, collections.Callable):
            f.proxy = entity
        return f

    if isinstance(entity, collections.Callable):
        return _record(entity)

    return _record


def replay(entity):
    """
    Use this decorator to mark a test as being in replay mode. This
    decorator optionally takes an argument. So it can be used this way: :

         @replay
         def foo(...):
            ...

    Or like this: :

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
        if entity is not None and not isinstance(entity, collections.Callable):
            f.proxy = entity
        return f

    if isinstance(entity, collections.Callable):
        return _replay(entity)

    return _replay


def raw(f):
    """
    Use this decorator to mark a test as being in raw mode. In raw
    mode no proxiying is done, and no error will be raised if the
    tested code uses ``urllib.request.urlopen``.

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
        prev_ssl_cert_dir = os.environ.get('SSL_CERT_DIR', None)
        proxy = None

        temp = tempfile.mkstemp()
        try:
            if not hasattr(f, "proxy"):
                port = get_port()

                mitmdump = os.path.join(settings.TOPDIR, ".btw-venv3", "bin",
                                        "mitmdump")
                cmd = [mitmdump,
                       "-q",  # Quiet
                       "-p", str(port)]  # Port to use
                if hasattr(f, "record"):
                    cmd += ["-w", temp[1]]  # Write to file
                else:
                    cmd += [
                        # Don't check upstream certs.
                        "--set", "upstream_cert=false",
                        # Get rid of some sensitive information.
                        "-s",
                        os.path.join(dirname, "proxy_rewrite.py"),
                        # File to read from.
                        "-S", fname]

                proxy = subprocess.Popen(cmd)
                if proxy.poll():
                    raise Exception("can't start mitmdump")

                # We need to check that the proxy is ready to work.
                os.environ['https_proxy'] = "https://localhost:" + str(port)
            else:
                os.environ['https_proxy'] = f.proxy

            # This is needed so that the CA for mitmproxy is found.
            hash_mitmproxy()
            # This is needed so that we don't run mitmproxy with
            # an expired certificate
            check_certs()

            # Make mitmproxy's certificate checkable.
            os.environ['SSL_CERT_DIR'] = \
                MITMPROXY_CERT_DIR + ":" + "/etc/ssl/certs"

            # This flushes the previous opener that may have been installed. We
            # must do this so that urllib picks up the new https_proxy
            # configuration.
            urllib.request.install_opener(urllib.request.build_opener())

            ready = False
            while not ready:
                try:
                    urllib.request.urlopen(server)
                    ready = True
                except urllib.error.URLError as ex:
                    if proxy.poll():
                        raise Exception("can't start mitmdump")
                    time.sleep(0.1)

            try:
                ret = f(*args, **kwargs)
            finally:
                if proxy is not None:
                    if proxy.poll():
                        raise Exception("mitmdump exited with status: " +
                                        proxy.returcode)
                    else:
                        proxy.kill()
                if prev_https_proxy is not None:
                    os.environ['https_proxy'] = prev_https_proxy
                else:
                    del os.environ['https_proxy']

                if prev_ssl_cert_dir is not None:
                    os.environ['SSL_CERT_DIR'] = prev_ssl_cert_dir
                else:
                    del os.environ['SSL_CERT_DIR']

            if not hasattr(f, "proxy") and hasattr(f, "record"):
                py3 = os.path.join(settings.TOPDIR, ".btw-venv3", "bin",
                                   "python3")
                subprocess.check_call([py3,
                                       os.path.join(
                                           dirname, "flow_rewrite.py"),
                                       temp[1], fname])
        finally:
            try:
                os.unlink(temp[1])
            except:  # pylint: disable=bare-except
                pass

        return ret

    return wrapper

urlopen_patcher = mock.patch('bibliography.zotero.urllib.request.urlopen')


def no_net_decorator(f):
    """
    This decorator will raise an exception if the test decorated by it
    accesses ``urllib.request.urlopen``.

    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        urlopen_mock = urlopen_patcher.start()

        try:
            ret = f(*args, **kwargs)
        finally:
            urlopen_patcher.stop()
            if urlopen_mock.called:
                raise Exception("unexpected call to urllib.request.urlopen")
        return ret

    return wrapper


class TestMeta(type):

    def __new__(meta, name, bases, dct):
        """
        Scan the class to be created for test methods that have been
        decorated with ``@replay``, ``@record`` and ``@raw``. Test
        methods are those whose name begins with ``test_``:

        * Methods decorated with ``@replay`` and ``@record`` are
          wrapped by: func: `_proxify`.

        * Methods decorated with ``@raw`` are left alone.

        * Other methods are wrapped by ``no_net_decorator``. In other
        words, any undecorated method that tries to access
        ``urllib.urlopen`` will raise an error.

        """
        for (key, value) in list(dct.items()):
            if key.startswith("test_"):
                if hasattr(value, "record") or hasattr(value, "replay"):
                    dct[key] = _proxify(name, value)
                elif hasattr(value, "raw"):
                    pass
                else:
                    dct[key] = no_net_decorator(value)
        return super(TestMeta, meta).__new__(meta, name, bases, dct)
