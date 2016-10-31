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

def setUpModule():
    # pylint: disable=global-statement
    global tmpdir

    tmpdir = tempfile.mkdtemp(prefix="btw-test-btw")

def tearDownModule():
    if os.environ.get("BTW_TESTING_KEEP_BTW_DIR", None) is None:
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
    else:
        print "Keeping", tmpdir

@override_settings(ENVPATH=None,
                   TOPDIR="foo",
                   BTW_SLUGIFIED_SITE_NAME="testing",
                   BTW_CELERY_WORKER_PREFIX="testing",
                   BTW_REDIS_SITE_PREFIX="testing")
class BTWTestCase(SimpleTestCase):

    def setUp(self):
        # We changed BTW_CELERY_WORKER_PREFIX but the workers in
        # btwworker are still cached. We must flush them.
        flush_caches()
        from django.conf import settings
        # We set these to some convenient values...
        settings.BTW_LOGGING_PATH_FOR_BTW = "logpath"
        settings.BTW_RUN_PATH_FOR_BTW = "runpath"
        settings.BTW_RUN_PATH = "foo/var/run"
        self.expected_scripts = \
            [os.path.join(tmpdir, x) for x in ("manage", "start-uwsgi")]

    def tearDown(self):
        # Yep, perform this cleanup for all tests.
        for script in self.expected_scripts:
            if os.path.exists(script):
                os.unlink(script)

    def assertNoOutput(self, c):
        self.assertTrue(c.called)
        self.assertEqual(c.stdout, "")
        self.assertEqual(c.stderr, "")

    def create_fake_scripts(self):
        for script in self.expected_scripts:
            with open(script, 'w') as f:
                f.write(' ')

    def check_no_dir(self, cmd):
        c = Caller()
        with self.assertRaisesRegexp(CommandError, r"too few arguments"):
            c.call_command("btw", cmd)

        self.assertNoOutput(c)

    def check_too_many_args(self, cmd):
        c = Caller()
        with self.assertRaisesRegexp(CommandError,
                                     r"unrecognized arguments: bar"):
            c.call_command("btw", cmd, "foo", "bar")

        self.assertNoOutput(c)

    def test_generate_monit_config_without_dir(self):
        """
        Test that ``btw generate-monit-config`` fails if no directory is
        specified.
        """
        self.check_no_dir("generate-monit-config")

    def test_generate_monit_config_with_too_many_args(self):
        """
        Test that ``btw generate-monit-config`` fails if too many
        arguments are given.
        """
        self.check_too_many_args("generate-monit-config")

    def test_generate_monit_config_with_nonexistent_scripts(self):
        """
        Test that ``btw generate-monit-config`` fails if scripts are missing.
        """
        c = Caller()
        with self.assertRaisesRegexp(CommandError,
                                     "generate-monit-config needs these "
                                     "scripts to exist: " +
                                     ", ".join(self.expected_scripts)):
            c.call_command("btw", "generate-monit-config", tmpdir)

        self.assertNoOutput(c)

    def test_generate_monit_config(self):
        """
        Test that ``btw generate-monit-config`` generates correct
        output.
        """
        self.create_fake_scripts()
        stdout, stderr = call_command("btw", "generate-monit-config",
                                      tmpdir)
        self.assertMultiLineEqual(stdout, """
check process btw-redis pidfile "foo/var/run/redis/testing.redis.pid"
      group testing
      start program = "{script_dir}/manage btwredis start"
          as uid btw and gid btw
      stop program = "{script_dir}/manage btwredis stop"
          as uid btw and gid btw
      if does not exist then start

check process btw pidfile "/run/uwsgi/app/btw/pid"
      group testing
      depends on testing.worker, testing.bibliography.worker, btw-redis
      start program = "{script_dir}/start-uwsgi"
      stop program = "/usr/bin/uwsgi --stop /run/uwsgi/app/btw/pid
      if does not exist then start

check process testing.worker pidfile "foo/var/run/btw/testing.worker.pid"
      group testing
      depends on btw-redis
      start program = "{script_dir}/manage btwworker start testing.worker"
            as uid btw and gid btw
      stop program = "{script_dir}/manage btwworker stop testing.worker"
            as uid btw and gid btw
      if does not exist then start

check process testing.bibliography.worker pidfile "foo/var/run/btw/\
testing.bibliography.worker.pid"
      group testing
      depends on btw-redis
      start program = "{script_dir}/manage btwworker start \
testing.bibliography.worker"
            as uid btw and gid btw
      stop program = "{script_dir}/manage btwworker stop \
testing.bibliography.worker"
            as uid btw and gid btw
      if does not exist then start
""".format(script_dir=tmpdir))
        self.assertEqual(stderr, "")

    def test_generate_scripts_without_dir(self):
        """
        Test that ``btw generate-scripts`` fails if not directory is specified.
        """
        self.check_no_dir("generate-scripts")

    def test_generate_scripts_with_too_many_args(self):
        """
        Test that ``btw generate-scripts`` fails if too many arguments are
        specified.
        """
        self.check_too_many_args("generate-scripts")

    def test_generate_scripts_without_envpath(self):
        """
        Test that ``btw generate-scripts`` generates correct
        scripts when there is no ENVPATH set.
        """
        stdout, stderr = call_command("btw", "generate-scripts",
                                      tmpdir)
        self.assertMultiLineEqual(open(os.path.join(tmpdir, "manage")).read(),
                                  """\
#!/bin/sh
export HOME="/home/btw"
cd "foo"
"python" ./manage.py "$@"
""")

        self.assertMultiLineEqual(
            open(os.path.join(tmpdir, "start-uwsgi")).read(),
            """\
#!/bin/sh
run_dir=/run/uwsgi/app/testing
mkdir -p $run_dir
chown btw:btw $run_dir
# We need to export these so that the variable expansion performed in
# /etc/uwsgi/default.ini can happen.
export UWSGI_DEB_CONFNAMESPACE=app
export UWSGI_DEB_CONFNAME=testing
/usr/bin/uwsgi --ini /etc/uwsgi/default.ini --ini \
/etc/uwsgi/apps-enabled/testing.ini --daemonize /var/log/uwsgi/app/testing.log
""")

        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")

    def test_generate_scripts_with_envpath(self):
        """
        Test that ``btw generate-scripts`` generates correct
        scripts when ENVPATH is set.
        """
        with override_settings(ENVPATH="blah"):
            stdout, stderr = call_command("btw", "generate-scripts",
                                          tmpdir)
            self.assertMultiLineEqual(
                open(os.path.join(tmpdir, "manage")).read(),
                """\
#!/bin/sh
export HOME="/home/btw"
cd "foo"
"blah/bin/python" ./manage.py "$@"
""")

            self.assertMultiLineEqual(
                open(os.path.join(tmpdir, "start-uwsgi")).read(),
                """\
#!/bin/sh
run_dir=/run/uwsgi/app/testing
mkdir -p $run_dir
chown btw:btw $run_dir
# We need to export these so that the variable expansion performed in
# /etc/uwsgi/default.ini can happen.
export UWSGI_DEB_CONFNAMESPACE=app
export UWSGI_DEB_CONFNAME=testing
/usr/bin/uwsgi --ini /etc/uwsgi/default.ini --ini \
/etc/uwsgi/apps-enabled/testing.ini --daemonize /var/log/uwsgi/app/testing.log
""")

            self.assertEqual(stdout, "")
            self.assertEqual(stderr, "")
