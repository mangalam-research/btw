import unittest
import os
import tempfile
import shutil
import subprocess
from contextlib import contextmanager
import mock

from nose.tools import nottest

from django.core.management.base import CommandError
from django.test.utils import override_settings

from .util import Caller, call_command
from lib.settings import join_prefix

tmpdir = None
runpath = None
logpath = None
libpath = None

def setUpModule():
    # We must stop the global redis
    try:
        call_command('btwredis', 'stop')
    except CommandError:
        pass

    # pylint: disable=global-statement
    global tmpdir
    global runpath
    global logpath
    global libpath
    tmpdir = tempfile.mkdtemp(prefix="btw-test-btwredis")
    runpath = os.path.join(tmpdir, "run")
    logpath = os.path.join(tmpdir, "log")
    libpath = os.path.join(tmpdir, "lib")
    os.mkdir(runpath)
    os.mkdir(logpath)
    os.mkdir(libpath)

def tearDownModule():
    if os.path.exists(tmpdir):
        shutil.rmtree(tmpdir)
    # Restart redis so that the rest of the tests can run. We let
    # exceptions trickle up because a failure here has serious consequences.
    call_command('btwredis', 'start')


@contextmanager
def with_fake_settings():
    with override_settings(BTW_REDIS_SITE_PREFIX="testing",
                           BTW_RUN_PATH=runpath,
                           BTW_REDIS_SOCKET_DIR_PATH=runpath,
                           BTW_LOGGING_PATH=logpath,
                           TOPDIR=tmpdir,
                           BTW_REDIS_PASSWORD="foo"):
        yield

@nottest
@contextmanager
def with_test_redis(stop_fails=False):
    with with_fake_settings():
        stdout, stderr = call_command('btwredis', 'start')
        try:
            yield stdout, stderr
        finally:
            try:
                call_command('btwredis', 'stop')
            except:  # pylint: disable=bare-except
                if not stop_fails:
                    raise

class BTWRedisTestCase(unittest.TestCase):

    def tearDown(self):
        super(BTWRedisTestCase, self).tearDown()
        # Make sure that we don't leave redis running...
        try:
            call_command('btwredis', 'stop')
        except CommandError:
            pass

    def assertNoOutput(self, c):
        self.assertTrue(c.called)
        self.assertEqual(c.stdout, "")
        self.assertEqual(c.stderr, "")

    def test_no_command(self):
        """
        Tests that btwredis requires a command.
        """
        c = Caller()
        with self.assertRaisesRegexp(CommandError, r"too few arguments"):
            c.call_command("btwredis")
        self.assertNoOutput(c)

    def test_start(self):
        """
        Test that ``btwredis start`` starts redis and that the files we
        expect are present.
        """
        with with_test_redis() as (stdout, stderr):
            # Check that the settings are respected
            self.assertTrue(os.path.exists(os.path.join(runpath, "redis",
                                                        "testing.redis.pid")))
            self.assertTrue(os.path.exists(os.path.join(runpath,
                                                        "testing.redis.sock")))
            self.assertTrue(os.path.exists(
                os.path.join(logpath, "redis", "testing.redis-server.log")))
            self.assertEqual(stdout, "Started redis.\n")
            self.assertEqual(stderr, "")

    def test_start_twice(self):
        """
        Test that ``btwredis start`` fails if redis is already started.
        """
        c = Caller()
        with with_test_redis(), self.assertRaisesRegexp(
                CommandError,
                r"redis appears to be running already\."):
            c.call_command("btwredis", "start")
        self.assertNoOutput(c)

    def test_start_failure(self):
        """
        Test that ``btwredis start`` fails if redis fails to start.
        """

        c = Caller()
        with self.assertRaisesRegexp(
                CommandError,
                r"cannot talk to redis\."):

            class MockPopen(subprocess.Popen):
                __times = 0

                def communicate(self, *args, **kwargs):
                    fake = False
                    if args[0].startswith("auth "):
                        MockPopen.__times += 1
                        if MockPopen.__times >= 2:
                            fake = True

                    ret = super(MockPopen, self).communicate(*args, **kwargs)
                    return ("NOAUTH", "") if fake else ret

            with mock.patch("subprocess.Popen", new=MockPopen):
                c.call_command("btwredis", "start")

        self.assertNoOutput(c)

    def test_stop(self):
        """
        Test that ``btwredis stop`` works.
        """
        with with_test_redis(stop_fails=True):
            stdout, stderr = call_command("btwredis", "stop")
            self.assertEqual(stdout, "Stopped redis.\n")
            self.assertEqual(stderr, "")

    def test_stop_failure(self):
        """
        Test that ``btwredis stop`` fails if there is no pid file.
        """
        c = Caller()
        with self.assertRaisesRegexp(
                CommandError,
                r"cannot read pid from "):
            c.call_command("btwredis", "stop")
        self.assertNoOutput(c)

    def test_stop_corrupt_pid(self):
        """
        Test that ``btwredis stop`` fails if the pid file is corrupt.
        """
        fake_pidfile_dir = os.path.join(runpath, "redis")
        fake_pidfile_path = os.path.join(fake_pidfile_dir,
                                         "testing.redis.pid")

        # If other tests have run, the directory already exists. If
        # not, the directory is absent.
        if not os.path.exists(fake_pidfile_dir):
            os.makedirs(fake_pidfile_dir)

        with open(fake_pidfile_path, "w") as f:
            f.write("foo")

        c = Caller()
        with with_fake_settings(), self.assertRaisesRegexp(
                CommandError,
                r"the pid file contains something that "
                r"cannot be converted to an integer: foo"):
            c.call_command("btwredis", "stop")
        self.assertNoOutput(c)

    def test_stop_workers_running(self):
        """
        Test that ``btwredis stop`` fails if workers are running.
        """

        # We mock btwredis's method rather than really start a
        # worker. Starting/stopping workers is rather expensive.

        c = Caller()
        with mock.patch(
                "btw_management.management.commands.btwredis"
                ".get_running_workers") \
            as grw, \
            with_fake_settings(), \
            self.assertRaisesRegexp(
                CommandError,
                r"cannot stop redis while BTW workers are running."):
            # We want to return an array of length > 0. The contents
            # are not important.
            grw.return_value = [1, 2]
            c.call_command("btwredis", "stop")
        self.assertNoOutput(c)

    def test_check(self):
        "Test that ``btwredis check`` works."

        with with_test_redis():
            stdout, stderr = call_command("btwredis", "check")
            self.assertEqual(stdout, "Redis instance is alive.\n")
            self.assertEqual(stderr, "")

    def test_check_fails(self):
        """
        Test that ``btwredis check`` fails if there is no redis server.
        """

        c = Caller()
        with with_fake_settings(), self.assertRaisesRegexp(
                CommandError, r"cannot contact redis."):
            c.call_command("btwredis", "check")

        self.assertNoOutput(c)
