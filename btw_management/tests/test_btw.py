import tempfile
import os
import shutil
from unittest import mock

from django.core.management.base import CommandError
from django.test.utils import override_settings
from django.test import SimpleTestCase

from .util import Caller, call_command
from btw_management.management.commands.btwworker import flush_caches

tmpdir = None
script_tmpdir = None
services_tmpdir = None

def setUpModule():
    # pylint: disable=global-statement
    global tmpdir
    global script_tmpdir
    global services_tmpdir

    tmpdir = tempfile.mkdtemp(prefix="btw-test-btw")
    script_tmpdir = os.path.join(tmpdir, "scripts")
    os.mkdir(script_tmpdir)
    services_tmpdir = os.path.join(tmpdir, "services")
    os.mkdir(services_tmpdir)

def tearDownModule():
    if os.environ.get("BTW_TESTING_KEEP_BTW_DIR", None) is None:
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
    else:
        print("Keeping", tmpdir)

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
            [os.path.join(script_tmpdir, x)
             for x in ("manage", "start-uwsgi", "notify")]

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

    def check_missing_arg(self, cmd, expected):
        c = Caller()
        with self.assertRaisesRegex(CommandError,
                                    r"Error: the following arguments are "
                                    r"required: {}".format(expected)):
            c.call_command("btw", cmd)

        self.assertNoOutput(c)

    def check_too_many_args(self, cmd, expected=1):
        c = Caller()
        args = ["btw", cmd] + ["foo"] * expected + ["bar"]
        with self.assertRaisesRegex(CommandError,
                                    r"unrecognized arguments: bar"):
            c.call_command(*args)

        self.assertNoOutput(c)

    def test_generate_systemd_services_without_dir(self):
        """
        Test that ``btw generate-systemd-services`` fails if no directory is
        specified.
        """
        self.check_missing_arg("generate-systemd-services",
                               "scripts, services")

    def test_generate_systemd_services_with_too_many_args(self):
        """
        Test that ``btw generate-systemd-services`` fails if too many
        arguments are given.
        """
        self.check_too_many_args("generate-systemd-services", 2)

    def test_generate_systemd_services_with_nonexistent_scripts(self):
        """
        Test that ``btw generate-systemd-services`` fails if scripts are
        missing.
        """
        c = Caller()
        with self.assertRaisesRegex(CommandError,
                                    "we need these scripts to exist: " +
                                    ", ".join(self.expected_scripts)):
            c.call_command("btw", "generate-systemd-services",
                           script_tmpdir, services_tmpdir)

        self.assertNoOutput(c)

    def test_generate_systemd_services(self):
        """
        Test that ``btw generate-systemd-services`` generates correct
        output.
        """
        self.create_fake_scripts()
        stdout, stderr = call_command("btw", "generate-systemd-services",
                                      script_tmpdir, services_tmpdir)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")

        self.assertMultiLineEqual(
            open(os.path.join(services_tmpdir,
                              "testing.service")).read(),
            """\
[Unit]
Description=BTW Application for site testing
OnFailure=testing-notification@%n.service

[Service]
Type=oneshot
ExecStart=/bin/true
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
Also=testing-redis.service
Also=testing-uwsgi.service
Also=testing-existdb.service
Also=testing.worker.service
Also=testing.bibliography.worker.service
""")

        self.assertMultiLineEqual(
            open(os.path.join(services_tmpdir,
                              "testing-redis.service")).read(),
            """\
[Unit]
Description=BTW Redis Instance for site testing
PartOf=testing.service
OnFailure=testing-notification@%n.service

[Service]
Type=forking
PIDFile=foo/var/run/redis/testing.redis.pid
ExecStart={script_dir}/manage btwredis start
ExecStop={script_dir}/manage btwredis stop
Restart=on-failure
# Restarting too fast causes issues.
RestartSec=1
User=btw
Group=btw

[Install]
RequiredBy=testing.service
""".format(script_dir=script_tmpdir))

        self.assertMultiLineEqual(
            open(os.path.join(services_tmpdir,
                              "testing-existdb.service")).read(),
            """\
[Unit]
Description=BTW eXist-db instance for site testing
PartOf=testing.service
OnFailure=testing-notification@%n.service

[Service]
Type=forking
PIDFile=foo/var/run/eXist.pid
ExecStart={script_dir}/manage btwexistdb start --timeout=40
ExecStop={script_dir}/manage btwexistdb stop
Restart=on-failure
User=btw
Group=btw

[Install]
RequiredBy=testing.service
""".format(script_dir=script_tmpdir))

        worker_template = """\
[Unit]
Description=BTW Worker {worker_name} for site testing
BindsTo=testing-redis.service
BindsTo=testing-existdb.service
After=testing-redis.service
After=testing-existdb.service
PartOf=testing.service
OnFailure=testing-notification@%n.service

[Service]
Type=forking
PIDFile=foo/var/run/btw/{worker_name}.pid
ExecStart={script_dir}/manage btwworker start {worker_name}
ExecStop={script_dir}/manage btwworker stop {worker_name}
Restart=on-failure
User=btw
Group=btw

[Install]
RequiredBy=testing.service
"""

        self.assertMultiLineEqual(
            open(os.path.join(services_tmpdir,
                              "testing.worker.service")).read(),
            worker_template.format(script_dir=script_tmpdir,
                                   worker_name="testing.worker"))

        self.assertMultiLineEqual(
            open(os.path.join(services_tmpdir,
                              "testing.bibliography.worker.service")).read(),
            worker_template.format(script_dir=script_tmpdir,
                                   worker_name="testing.bibliography.worker"))

        self.assertMultiLineEqual(
            open(os.path.join(services_tmpdir,
                              "testing-uwsgi.service")).read(),
            """\
[Unit]
Description=BTW UWSGI Instance for site testing
BindsTo=testing-redis.service
BindsTo=testing-existdb.service
BindsTo=testing.worker.service
BindsTo=testing.bibliography.worker.service
After=testing-redis.service
After=testing-existdb.service
After=testing.worker.service
After=testing.bibliography.worker.service
PartOf=testing.service
OnFailure=testing-notification@%n.service

[Service]
Type=forking
PIDFile=/run/uwsgi/app/btw/pid
ExecStart={script_dir}/start-uwsgi
ExecStop=/usr/bin/uwsgi --stop /run/uwsgi/app/btw/pid
Restart=on-failure

[Install]
RequiredBy=testing.service
""".format(script_dir=script_tmpdir))

    def test_generate_scripts_without_dir(self):
        """
        Test that ``btw generate-scripts`` fails if not directory is
        specified.
        """
        self.check_missing_arg("generate-scripts", "dir")

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
                                      script_tmpdir)
        self.assertMultiLineEqual(open(os.path.join(script_tmpdir,
                                                    "manage")).read(),
                                  """\
#!/bin/sh
export HOME="/home/btw"
cd "foo"
"python" ./manage.py "$@"
""")

        self.assertMultiLineEqual(
            open(os.path.join(script_tmpdir, "start-uwsgi")).read(),
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

        self.assertMultiLineEqual(
            open(os.path.join(script_tmpdir, "notify")).read(),
            """\
#!/bin/sh

/usr/sbin/sendmail -bm $1<<TXT
Subject: [BTW SERVICE FAILURE] $2 failed

$(systemctl status --full "$2")
TXT
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
                                          script_tmpdir)
            self.assertMultiLineEqual(
                open(os.path.join(script_tmpdir, "manage")).read(),
                """\
#!/bin/sh
export HOME="/home/btw"
cd "foo"
"blah/bin/python" ./manage.py "$@"
""")

            self.assertMultiLineEqual(
                open(os.path.join(script_tmpdir, "start-uwsgi")).read(),
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

            self.assertMultiLineEqual(
                open(os.path.join(script_tmpdir, "notify")).read(),
                """\
#!/bin/sh

/usr/sbin/sendmail -bm $1<<TXT
Subject: [BTW SERVICE FAILURE] $2 failed

$(systemctl status --full "$2")
TXT
""")

            self.assertEqual(stdout, "")
            self.assertEqual(stderr, "")
