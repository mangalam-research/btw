import tempfile
import os
import shutil
import mock

from django.core.management.base import CommandError
from django.test.utils import override_settings
from django.test import SimpleTestCase

from .util import Caller, call_command
from btw_management.management.commands.btwworker import flush_caches

tmpdir = None
runpath = None
logpath = None
old_btw_env_suppress_message = None

def setUpModule():
    # pylint: disable=global-statement
    global tmpdir
    global runpath
    global logpath
    global old_btw_env_suppress_message

    tmpdir = tempfile.mkdtemp(prefix="btw-test-btwworker")
    runpath = os.path.join(tmpdir, "run")
    logpath = os.path.join(tmpdir, "log")
    os.mkdir(runpath)
    os.mkdir(logpath)
    old_btw_env_suppress_message = os.environ.get("BTW_ENV_SUPPRESS_MESSAGE")
    os.environ["BTW_ENV_SUPPRESS_MESSAGE"] = "1"
    # We purge all tasks before running the tests here so that the workers
    # do not attempt to do anything.
    from celery.task.control import discard_all
    discard_all()

def tearDownModule():
    if old_btw_env_suppress_message:
        os.environ["BTW_ENV_SUPPRESS_MESSAGE"] = old_btw_env_suppress_message
    if os.environ.get("BTW_TESTING_KEEP_BTWWORKER_DIR", None) is None:
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
    else:
        print "Keeping", tmpdir

@override_settings(BTW_LOGGING_PATH_FOR_BTW="",
                   BTW_RUN_PATH_FOR_BTW="",
                   BTW_CELERY_WORKER_PREFIX="testing",
                   CELERY_DEFAULT_QUEUE="testing.default",
                   BTW_CELERY_BIBLIOGRAPHY_QUEUE="testing.bibliography",
                   CELERY_WORKER_DIRECT=True,
                   ENVPATH=None,
                   TOPDIR="foo",
                   BTW_SLUGIFIED_SITE_NAME="testing")
class BTWWorkerTestCase(SimpleTestCase):
    maxDiff = None

    def setUp(self):
        # We changed BTW_CELERY_WORKER_PREFIX but the workers in
        # btwworker are still cached. We must flush them.
        flush_caches()
        from django.conf import settings
        settings.BTW_LOGGING_PATH_FOR_BTW = logpath
        settings.BTW_RUN_PATH_FOR_BTW = runpath

    def assertNoOutput(self, c):
        self.assertTrue(c.called)
        self.assertEqual(c.stdout, "")
        self.assertEqual(c.stderr, "")

    def check_no_arguments(self, cmd):
        c = Caller()
        with self.assertRaisesRegexp(CommandError,
                                     cmd + r" does not take arguments\."):
            c.call_command("btwworker", cmd, "foo")

        self.assertNoOutput(c)

    def check_no_all(self, cmd):
        c = Caller()
        with self.assertRaisesRegexp(
                CommandError, cmd + r" does not take the --all option\."):
            c.call_command("btwworker", cmd, all=True)

        self.assertNoOutput(c)

    def test_no_command(self):
        """
        Tests that btwredis requires a command.
        """
        c = Caller()
        with self.assertRaisesRegexp(CommandError,
                                     r"you must specify a command\."):
            c.call_command("btwworker")
        self.assertNoOutput(c)

    def test_bad_command(self):
        """
        Tests that btwredis requires a command.
        """
        c = Caller()
        with self.assertRaisesRegexp(CommandError,
                                     r"bad command: foo"):
            c.call_command("btwworker", "foo")
        self.assertNoOutput(c)

    def test_names(self):
        """
        Test that ``btwredis names`` prints the names of the known
        workers.
        """
        stdout, stderr = call_command("btwworker", "names")
        self.assertEqual(stdout,
                         "testing.worker\ntesting.bibliography.worker\n")
        self.assertEqual(stderr, "")

    def test_names_does_not_take_arguments(self):
        """
        Test that ``btwredis names`` does not take arguments.
        """
        self.check_no_arguments("names")

    def test_names_does_not_take_all(self):
        """
        Test that ``btwredis names`` does not take ``--all``.
        """
        self.check_no_all("names")

    def test_start_all(self):
        """
        Test that ``btwredis start --all`` starts all workers.
        """
        try:
            stdout, stderr = call_command("btwworker", "start", all=True)
            stdout_ping, stderr_ping = call_command("btwworker", "ping")
        finally:
            call_command("btwworker", "stop", all=True)
        self.assertEqual(stdout, """\
testing.worker has started.
testing.bibliography.worker has started.
""")
        self.assertEqual(stderr, "")
        self.assertEqual(stdout_ping, """\
Pinging worker testing.worker... passed
Pinging worker testing.bibliography.worker... passed
""")
        self.assertEqual(stderr_ping, "")

    def test_start_one(self):
        """
        Test that ``btwredis start [name]`` starts the named worker.
        """
        try:
            stdout, stderr = call_command("btwworker", "start",
                                          "testing.worker")
            stdout_ping, stderr_ping = call_command("btwworker", "ping")
        finally:
            call_command("btwworker", "stop", all=True)
        self.assertEqual(stdout, "testing.worker has started.\n")
        self.assertEqual(stderr, "")
        self.assertEqual(stdout_ping, """\
Pinging worker testing.worker... passed
Pinging worker testing.bibliography.worker... failed: no pidfile
""")
        self.assertEqual(stderr_ping, "")

    def test_start_bad_env(self):
        """
        Test that ``btwredis start [name]`` fails if the environment is wrong.
        """
        try:
            from core.tasks import get_btw_env
            old_apply_async = get_btw_env.apply_async

            def mock_apply(*args, **kwargs):
                ret = old_apply_async(*args, **kwargs)
                return mock.Mock(
                    wraps=ret,
                    # We want the original get method to be called but
                    # always return 'foo'.
                    **{'get': lambda *args, **kwargs:
                       ret.get(*args, **kwargs) and 'foo' or 'foo'})

            with mock.patch(
                    "core.tasks.get_btw_env.apply_async",
                    **{'side_effect': mock_apply}):
                stdout, stderr = call_command("btwworker", "start",
                                              all=True)
        finally:
            call_command("btwworker", "stop", all=True)
        self.assertEqual(stdout, """\
testing.worker has started.
testing.bibliography.worker has started.
""")
        from btw.settings._env import env
        self.assertEqual(stderr, """\
testing.worker: not using environment {0} (uses environment foo)
testing.bibliography.worker: not using environment {0} (uses \
environment foo)
""".format(env))

    def test_stop_all(self):
        """
        Test that ``btwredis stop --all`` stops all workers.
        """
        try:
            call_command("btwworker", "start", all=True)
            stdout_ping, stderr_ping = call_command("btwworker", "ping")
        finally:
            stdout, stderr = call_command("btwworker", "stop", all=True)

        self.assertEqual(stdout, """\
testing.worker has stopped.
testing.bibliography.worker has stopped.
""")
        self.assertEqual(stderr, "")
        self.assertEqual(stdout_ping, """\
Pinging worker testing.worker... passed
Pinging worker testing.bibliography.worker... passed
""")
        self.assertEqual(stderr_ping, "")

    def test_stop_one(self):
        """
        Test that ``btwredis stop [name]`` stops one worker.
        """
        try:
            call_command("btwworker", "start", all=True)
            stdout_ping, stderr_ping = call_command("btwworker", "ping")
            stdout, stderr = call_command("btwworker", "stop",
                                          "testing.worker")
            stdout_ping2, stderr_ping2 = call_command("btwworker", "ping")
        finally:
            call_command("btwworker", "stop", all=True)

        self.assertEqual(stdout, """\
testing.worker has stopped.
""")
        self.assertEqual(stderr, "")
        self.assertEqual(stdout_ping, """\
Pinging worker testing.worker... passed
Pinging worker testing.bibliography.worker... passed
""")
        self.assertEqual(stderr_ping, "")
        self.assertEqual(stdout_ping2, """\
Pinging worker testing.worker... failed: no pidfile
Pinging worker testing.bibliography.worker... passed
""")
        self.assertEqual(stderr_ping2, "")

    def test_stop_not_running(self):
        """
        Test that ``btwredis stop --all`` knows when workers are not
        running.
        """
        stdout, stderr = call_command("btwworker", "stop", all=True)

        self.assertEqual(stdout, """\
testing.worker was not running.
testing.bibliography.worker was not running.
""")
        self.assertEqual(stderr, "")

    def test_check_does_not_take_arguments(self):
        """
        Test that ``btwredis check`` does not take arguments.
        """
        self.check_no_arguments("check")

    def test_check_does_not_take_all(self):
        """
        Test that ``btwredis check`` does not take ``--all``.
        """
        self.check_no_all("check")

    def test_check(self):
        """
        Test that ``btwworker check`` checks the workers.
        """
        try:
            call_command("btwworker", "start", all=True)
            stdout, stderr = call_command("btwworker", "check")
        finally:
            call_command("btwworker", "stop", all=True)
        self.assertEqual(stdout, """\
Checking worker testing.worker... passed
Checking worker testing.bibliography.worker... passed
""")
        self.assertEqual(stderr, "")

    def test_check_not_started(self):
        """
        Test that ``btwredis check`` reports workers that are not started.
        """
        try:
            call_command("btwworker", "start", "testing.worker")
            stdout, stderr = call_command("btwworker", "check")
        finally:
            call_command("btwworker", "stop", all=True)
        self.assertEqual(stdout, """\
Checking worker testing.worker... passed
Checking worker testing.bibliography.worker... failed: no pidfile
""")
        self.assertEqual(stderr, "")

    def test_check_bad_env(self):
        """
        Test that ``btwredis check`` reports workers that have a bad
        environment.
        """
        try:
            call_command("btwworker", "start", all=True)
            from core.tasks import get_btw_env
            old_apply_async = get_btw_env.apply_async

            def mock_apply(*args, **kwargs):
                ret = old_apply_async(*args, **kwargs)
                return mock.Mock(
                    wraps=ret,
                    # We want the original get method to be called but
                    # always return 'foo'.
                    **{'get': lambda *args, **kwargs:
                       ret.get(*args, **kwargs) and 'foo' or 'foo'})

            with mock.patch(
                    "core.tasks.get_btw_env.apply_async",
                    **{'side_effect': mock_apply}):
                stdout, stderr = call_command("btwworker", "check")
        finally:
            call_command("btwworker", "stop", all=True)

        from btw.settings._env import env

        self.assertEqual(stdout, """\
Checking worker testing.worker... failed: not using environment {0} \
(uses environment foo)
Checking worker testing.bibliography.worker... failed: not using \
environment {0} (uses environment foo)
""".format(env))
        self.assertEqual(stderr, "")

    def test_ping_does_not_take_arguments(self):
        """
        Test that ``btwredis ping`` does not take arguments.
        """
        self.check_no_arguments("ping")

    def test_ping_does_not_take_all(self):
        """
        Test that ``btwredis ping`` does not take ``--all``.
        """
        self.check_no_all("ping")

    def test_ping_not_started(self):
        """
        Test that ``btwredis ping`` reports workers that are not started.
        """
        try:
            call_command("btwworker", "start", "testing.worker")
            stdout, stderr = call_command("btwworker", "ping")
        finally:
            call_command("btwworker", "stop", all=True)
        self.assertEqual(stdout, """\
Pinging worker testing.worker... passed
Pinging worker testing.bibliography.worker... failed: no pidfile
""")
        self.assertEqual(stderr, "")
