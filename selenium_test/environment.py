
import os
import time
import tempfile
import subprocess
import shutil
import http.client
import atexit
import signal
import datetime
import sys
import types
import re

from slugify import slugify
import selenic.util
from selenic import Builder
from behave.tag_matcher import ActiveTagMatcher
from pyvirtualdisplay import Display

from nose.tools import assert_equal, assert_true  # pylint: disable=E0611
from selenium_test import btw_util
from selenium.common.exceptions import UnexpectedAlertPresentException

assert_equal.__self__.maxDiff = None

_dirname = os.path.dirname(__file__)

conf_path = os.path.join(os.path.dirname(_dirname), "config",
                         "selenium_config.py")
# Turn on long messages. This will apply to all assertions unless turned off
# somewhere else.
assert_equal.__self__.longMessage = True

def sig(num, _frame):
    # Doing this ensures that cleanup will be called once before_all
    # has registered it with atexit.
    sys.exit("behave process received %d\n\n" % num)

os.environ['DJANGO_SETTINGS_MODULE'] = 'btw.selenium_test_settings'

# We need to trap these signals because behave does not do it
# itself. If we do not trap them, then if Buildbot sends a SIGTERM
# signal because a test is taking too long then cleanup won't run and
# some child processes may stay behind and cleanup actions won't be
# done.
signal.signal(signal.SIGTERM, sig)
signal.signal(signal.SIGINT, sig)

def cleanup(context, failed):
    driver = context.driver

    selenium_quit = context.selenium_quit
    actually_quit = not ((selenium_quit in ("never", "on-enter")) or
                         (context.failed and selenium_quit ==
                          "on-success"))

    keep_tempdirs = context.behave_keep_tempdirs

    builder = context.builder
    if driver:
        try:
            builder.set_test_status(not (failed or context.failed))
        except http.client.HTTPException:
            # Ignore cases where we can't set the status.
            pass
        if actually_quit:
            # Yes, we trap every possible exception. There is not much
            # we can do if the driver refuses to stop.
            try:
                driver.quit()
            except:   # pylint: disable=bare-except
                pass
        elif selenium_quit == "on-enter":
            input("Hit enter to quit")
            try:
                driver.quit()
            except:  # pylint: disable=bare-except
                pass

        context.driver = None

    if context.tunnel_id:
        # The tunnel was created by selenic, ask selenic to kill it.
        builder.stop_tunnel()
        context.tunnel_id = None

    if context.tunnel:
        # Tunnel created by us...
        context.tunnel.send_signal(signal.SIGTERM)
        context.tunnel = None

    if context.wm:
        context.wm.send_signal(signal.SIGTERM)
        context.wm = None

    if context.display:
        context.display.stop()
        context.display = None

    server = context.server
    if context.server:
        try:
            # Must read started before quitting...
            context.server.wait_for_start()
            server.write("quit\n")
            try:
                server.wait()
            except KeyboardInterrupt:
                pass
        except DeadServer:
            pass  # It is already dead...
        context.server = None

    if context.server_tempdir:
        if keep_tempdirs:
            print("Keeping server tempdir:", context.server_tempdir)
        else:
            shutil.rmtree(context.server_tempdir, True)
        context.server_tempdir = None

    if context.download_dir:
        if keep_tempdirs:
            print("Keeping download tempdir:", context.download_dir)
        else:
            shutil.rmtree(context.download_dir, True)
        context.download_dir = None

class DeadServer(Exception):
    pass

class ServerControl(object):

    def __init__(self, server, read_fifo, write_fifo):
        self.server = server
        self.write_fifo = write_fifo
        self.read_fifo = read_fifo

        # Indicates whether we must wait for a start. We must wait
        # when the server has just been started, or when the server
        # has been restarted.
        self.must_wait_for_start = True

    def wait(self):
        return self.server.wait()

    def wait_for_start(self):
        if not self.must_wait_for_start:
            return

        read = self.read()
        if read != 'started':
            raise ValueError("did not get the 'started' string; got " + read)
        self.must_wait_for_start = False

    def before_scenario(self):
        self.wait_for_start()
        self.new_test()

    def restart(self):
        self.write("restart\n")
        self.must_wait_for_start = True

    def new_test(self):
        self.write("newtest\n")
        self.read()

    def is_alive(self):
        try:
            self.assert_alive()
        except DeadServer:
            return False

        return True

    def assert_alive(self):
        if self.server is None:
            raise DeadServer("the server is already dead")

        status = self.server.poll()
        if status is not None:
            self.server = None
            if status >= 0:
                raise DeadServer("server exited with: " + str(status))
            else:
                raise DeadServer(
                    "server already with signal: " + str(-status))

    def patch_reset(self):
        self.write("patch reset\n")
        self.read()

    def write(self, text):
        self.assert_alive()
        with open(self.write_fifo, 'w') as fifo:
            fifo.write(text)

    def read(self):
        self.assert_alive()
        try:
            with open(self.read_fifo, 'r') as fifo:
                return fifo.read().strip()
        except IOError:
            # Wait for the server to die.
            while self.is_alive():
                time.sleep(0.1)

celery_log_re = re.compile(
    r"^\[(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) "
    r"(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2}),\d+: (?P<level>.*?)/"
    r"(?P<worker>.*?)\]")

# A LogChecker is meant to check Celery worker logs for errors that
# may be reported there. The Django unit tests that we run all run the
# workers with CELERY_ALWAYS_EAGER, which does not allow detecting
# errors that may be caused by race conditions. So the Selenium tests
# are the only place where we can see errors caused by a race
# condition. Unfortunately, this is not a sure thing either because
# some race conditions are hard to reproduce. But this is better than
# nothing. Had it been implemented beforehand, it actually **would**
# have been able to find a race condition that occured in Summer-Fall
# 2016 that remained undetected until it made its way onto the demo
# site.
class LogChecker(object):

    def __init__(self, path):
        self.path = path

        try:
            stat = os.stat(self.path)
        except OSError:
            stat = None

        # We do not want to check old stuff so we record the size of the
        # file at the start.
        self.size_at_prev_check = stat.st_size if stat is not None else 0

    def hasErrors(self):
        stat = os.stat(self.path)

        if stat.st_size > self.size_at_prev_check:
            with open(self.path, 'r') as log:
                log.seek(self.size_at_prev_check)
                for line in log:
                    match = celery_log_re.match(line)
                    if match and match.group('level') not in \
                       ("DEBUG", "INFO", "WARNING"):
                        return line

            self.size_at_prev_check = stat.st_size

        return False

def sigchld(context):
    context.server.assert_alive()

screenshots_dir_path = os.path.join("test_logs", "screenshots")


def setup_screenshots(context):
    now = datetime.datetime.now().replace(microsecond=0)
    this_screenshots_dir_path = os.path.join(screenshots_dir_path,
                                             now.isoformat())

    os.makedirs(this_screenshots_dir_path)
    latest = os.path.join(screenshots_dir_path, "LATEST")
    try:
        os.unlink(latest)
    except OSError as ex:
        if ex.errno != 2:
            raise

    os.symlink(os.path.basename(this_screenshots_dir_path),
               os.path.join(screenshots_dir_path, "LATEST"))
    context.screenshots_dir_path = this_screenshots_dir_path


def dump_config(builder):
    print("***")
    print(builder.config)
    print("***")

def remove_server_limit():
    # Turn off the limit which may have been set during testing.
    try:
        os.unlink("sitestatic/LIMIT")
    except OSError:
        pass  # The file may not exist.

def before_all(context):

    atexit.register(cleanup, context, True)

    if not hasattr(context, "step_registry"):
        raise Exception("you must use a test runner that exposes "
                        "step_registry on the context object")

    # We need to set these to None so that cleanup does not fail. It
    # expects to be able to check these fields without having to check
    # first for their existence.
    context.driver = None
    context.wm = None
    context.display = None
    context.server = None
    context.server_tempdir = None
    context.download_dir = None
    context.tunnel_id = None
    context.tunnel = None
    context.builder = None
    context.created_documents = {}

    context.selenium_quit = os.environ.get("SELENIUM_QUIT")
    context.behave_keep_tempdirs = os.environ.get("BEHAVE_KEEP_TEMPDIRS")
    context.visible = os.environ.get("SELENIUM_VISIBLE")

    userdata = context.config.userdata
    context.builder = builder = Builder(conf_path, userdata)

    dump_config(builder)
    if userdata.get("check_selenium_config", False):
        exit(0)

    setup_screenshots(context)

    browser_to_tag_value = {
        "INTERNETEXPLORER": "ie",
        "CHROME": "ch",
        "FIREFOX": "ff",
        "EDGE": "edge"
    }

    values = {
        'browser': browser_to_tag_value[builder.config.browser],
    }

    platform = builder.config.platform
    if platform.startswith("OS X "):
        values['platform'] = 'osx'
    elif platform.startswith("WINDOWS "):
        values['platform'] = 'win'
    elif platform == "LINUX" or platform.startswith("LINUX "):
        values['platform'] = 'linux'

    # We have some cases that need to match a combination of platform
    # and browser
    values['platform_browser'] = values['platform'] + "," + values['browser']

    context.active_tag_matcher = ActiveTagMatcher(values)

    # Without this, window sizes vary depending on the actual browser
    # used.
    initial_window_size = context.initial_window_size = \
        {"width": 1366, "height": 768}

    if not builder.remote:
        visible = context.visible or \
            context.selenium_quit in ("never", "on-success", "on-enter")
        context.display = Display(visible=visible,
                                  size=(initial_window_size["width"],
                                        initial_window_size["height"]))
        context.display.start()
        print("Display started")
        builder.update_ff_binary_env('DISPLAY')
        context.wm = subprocess.Popen(["openbox", "--sm-disable"])
        print("Window manager started")

        chrome_options = builder.local_conf.get("CHROME_OPTIONS", None)
        if chrome_options:
            # We set a temporary directory for Chrome downloads. Even if
            # we do not test downloads, this will prevent Chrome from
            # polluting our *real* download directory.
            context.download_dir = tempfile.mkdtemp()
            prefs = {
                "download.default_directory": context.download_dir
            }
            chrome_options.add_experimental_option("prefs", prefs)
    else:
        context.display = None
        context.wm = None

        tunnel_id = os.environ.get("TUNNEL_ID")
        if not tunnel_id:
            context.tunnel_id = builder.start_tunnel()
        else:
            builder.set_tunnel_id(tunnel_id)

    driver = builder.get_driver()
    context.driver = driver
    print("Obtained driver")
    context.util = selenic.util.Util(driver, 5)

    behave_wait = os.environ.get("BEHAVE_WAIT_BETWEEN_STEPS")
    context.behave_wait = behave_wait and float(behave_wait)

    context.server_tempdir = tempfile.mkdtemp()
    server_write_fifo = os.path.join(
        context.server_tempdir, "fifo_to_server")
    os.mkfifo(server_write_fifo)
    server_read_fifo = os.path.join(
        context.server_tempdir, "fifo_from_server")
    os.mkfifo(server_read_fifo)

    nginx_port = str(builder.get_unused_port())
    server = subprocess.Popen(
        ["utils/start_server", server_write_fifo,
         server_read_fifo, nginx_port], close_fds=True)
    context.server = ServerControl(server, server_read_fifo,
                                   server_write_fifo)
    signal.signal(signal.SIGCHLD, lambda *_: sigchld(context))

    # We must add the port to the server
    context.builder.SERVER += ":" + nginx_port

    context.selenium_logs = os.environ.get("SELENIUM_LOGS", False)

    remove_server_limit()

    lognames = subprocess.check_output(
        ["./manage.py", "btwworker", "lognames"])

    context.log_checkers = [LogChecker(name) for name in lognames.splitlines()]

def check_logs(context):
    for checker in context.log_checkers:
        failure = checker.hasErrors()
        if failure:
            raise AssertionError("Error in log {0}: {1}".format(checker.path,
                                                                failure))

def after_all(context):
    cleanup(context, False)
    check_logs(context)

CLEARCACHE = "clearcache:"
FAIL = "fail:"

def before_scenario(context, scenario):
    if context.active_tag_matcher.should_exclude_with(scenario.effective_tags):
        scenario.skip(reason="Disabled by an active tag")
        return

    driver = context.driver
    driver.set_window_size(context.initial_window_size["width"],
                           context.initial_window_size["height"])
    driver.set_window_position(0, 0)
    context.initial_window_handle = driver.current_window_handle

    matching_funcs = set(m.func for m in
                         [context.step_registry.find_match(s) for s
                          in scenario.steps] if m is not None)
    # Record whether we need sense recording.  What we are doing here
    # is scanning the list of steps for this scenario, seeking the
    # actual implementation of each step and verifying whether the
    # function is present in btw_util.require_sense_recording. This
    # dict was populated by using the decorator in btw_util.
    context.require_sense_recording = \
        any(f for f in matching_funcs if f
            in btw_util.require_sense_recording)

    # A set of all the sense labels for which we need to record renditions.
    context.require_rendition_recording = \
        btw_util.require_rendition_recording.get_senses_for_functions(
            matching_funcs)

    # A set of all the sense labels for which we need to record subsenses.
    context.require_subsense_recording = \
        btw_util.require_subsense_recording.get_senses_for_functions(
            matching_funcs)

    # Each scenario means logging in again.
    context.is_logged_in = False

    context.default_table = None
    context.tables = {}

    def clear_tables(self):
        self.default_table = None
        self.tables = {}

    context.clear_tables = types.MethodType(clear_tables, context)

    def register_table(self, table, default=False):
        name = table.name
        if name in self.tables:
            raise ValueError("trying to register a table with a duplicate "
                             "name: " + name)
        if default:
            self.default_table = table
        self.tables[name] = table

    context.register_table = types.MethodType(register_table, context)

    server = context.server
    #
    # This allows tags like:
    #
    # @clearcache:article_display
    # @fail:on_ajax
    # etc...
    #
    #
    caches = []
    for tag in scenario.tags:
        if tag.startswith(CLEARCACHE):
            caches.append(tag[len(CLEARCACHE):])
        elif tag.startswith(FAIL):
            what = tag[len(FAIL):]
            if what == "on_ajax":
                server.write("patch changerecord_details to fail on ajax\n")
                server.read()
            else:
                raise Exception("unknown failure type: " + what)
        elif tag == "wip" or \
                tag.startswith("not.with_") or \
                tag.startswith("use.with_") or \
                tag.startswith("only.with_") or \
                tag.startswith("active.with_") or \
                tag.startswith("not_active.with_"):
            pass  # Don't panic when encountering behave's stock tags.
        else:
            raise Exception("unknown tag")

    # Initialize some default values.
    context.session_id = None
    context.sf_editor_test = False

    # This will block until the server is started. Or will continue
    # immediately if a restart had not occurred.
    context.server.before_scenario()

    if caches:
        server = context.server
        server.write('clearcache ' + ' '.join(caches) + "\n")
        server.read()

    check_logs(context)

def after_scenario(context, scenario):
    if scenario.status == "skipped":
        return  # No cleanup needed...

    driver = context.driver

    handles = driver.window_handles

    if len(handles) > 1:
        driver.switch_to_window(context.initial_window_handle)

    driver.execute_script("""
    // Overwrite onbeforeunload to prevent the dialog from showing up.
    if (window.wed_editor)
        window.onbeforeunload = function () {};

    // Find all datatable instances and cancel their Ajax operations.
    if (typeof jQuery !== "undefined" && jQuery.fn.dataTable) {
        var settings_ar =
            jQuery(jQuery.fn.dataTable.tables()).DataTable().settings();
        for (var i = 0, settings; (settings = settings_ar[i]); ++i) {
            if (settings.jqXHR) {
                // console.log("aborting a datatable's ajax");
                settings.jqXHR.abort();
            }
        }
    }

    // This pre-aborts all new queries generated after this code runs.
    if (typeof jQuery !== "undefined") {
        jQuery(document).ajaxSend(function (event, jqXHR, settings) {
            jqXHR.abort();
        });
    }

    //
    // We want each test to start with a blank slate. This is required
    // because some DataTables use localStorage or sessionStorage to
    // record data.
    //
    localStorage.clear()
    sessionStorage.clear()

    // If it is defined we want to stop appenders so that we don't get a
    // cookie error.
    if (typeof log4javascript !== "undefined") {
      log4javascript.getLogger("wed").removeAllAppenders();
    }

    """)

    # Close all extra tabs.
    if len(handles) > 1:
        for handle in handles:
            if handle != context.initial_window_handle:
                driver.switch_to_window(handle)
                driver.close()
        driver.switch_to_window(context.initial_window_handle)
    driver.delete_all_cookies()

    context.ajax_timeout_test = False
    context.server.patch_reset()
    remove_server_limit()

    check_logs(context)

def before_step(context, _step):
    context.server.assert_alive()
    if context.behave_wait:
        time.sleep(context.behave_wait)


def after_step(context, step):
    driver = context.driver
    if step.status == "failed":
        name = os.path.join(context.screenshots_dir_path,
                            slugify(context.scenario.name + "_" +
                                    step.name) + ".png")
        try:
            driver.save_screenshot(name)
            print("")
            print("Captured screenshot:", name)
            print("")
        except UnexpectedAlertPresentException:
            pass  # There's nothing we can do

    context.server.assert_alive()
    # Perform this query only if SELENIUM_LOGS is on.
    if context.selenium_logs:
        logs = driver.execute_script("""
        return window.selenium_log;
        """)
        if logs:
            print("")
            print("JavaScript log:")
            print("\n".join(repr(x) for x in logs))
            print("")
            driver.execute_script("""
            window.selenium_log = [];
            """)
