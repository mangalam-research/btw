import os
import time
import tempfile
import subprocess
import shutil
import httplib
import atexit
import signal
import datetime
import sys

from slugify import slugify
# pylint: disable=E0611
from nose.tools import assert_true
import selenic.util
from selenic import Builder, outil
from behave import step_registry
from behave.tag_matcher import ActiveTagMatcher
from pyvirtualdisplay import Display

_dirname = os.path.dirname(__file__)

conf_path = os.path.join(os.path.dirname(_dirname),
                         "build", "config", "selenium_config.py")
# Turn on long messages. This will apply to all assertions unless turned off
# somewhere else.
from nose.tools import assert_equal  # pylint: disable=E0611
assert_equal.im_self.longMessage = True

from selenium_test import btw_util

def sig(num, _frame):
    # Doing this ensures that cleanup will be called once before_all
    # has registered it with atexit.
    sys.exit("behave process received %d\n\n" % num)

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
            builder.set_test_status(
                driver.session_id, not (failed or context.failed))
        except httplib.HTTPException:
            # Ignore cases where we can't set the status.
            pass
        if actually_quit:
            # Yes, we trap every possible exception. There is not much
            # we can do if the driver refuses to stop.
            try:
                driver.quit()
            except:
                pass
        elif selenium_quit == "on-enter":
            raw_input("Hit enter to quit")
            try:
                driver.quit()
            except:
                pass

        context.driver = None

    if context.sc_tunnel:
        context.sc_tunnel.send_signal(signal.SIGTERM)
        context.sc_tunnel = None

    if context.sc_tunnel_tempdir:
        if keep_tempdirs:
            print("Keeping tunnel tempdir:", context.sc_tunnel_tempdir)
        else:
            shutil.rmtree(context.sc_tunnel_tempdir, True)
        context.sc_tunnel_tempdir = None

    if context.wm:
        context.wm.send_signal(signal.SIGTERM)
        context.wm = None

    if context.display:
        context.display.stop()
        context.display = None

    if context.server:
        # Must read started before quitting...
        try:
            read = server_read(context)
            if read != 'started':
                raise ValueError("did not get the 'started' string")
            server_write(context, "quit\n")
            try:
                context.server.wait()
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

def server_alive(context):
    if context.server is None:
        return
    status = context.server.poll()
    if status is not None:
        context.server = None
        if status >= 0:
            raise DeadServer("server already exited with: " + str(status))
        else:
            raise DeadServer(
                "server already terminated with signal: " + str(-status))


def server_write(context, text):
    server_alive(context)
    with open(context.server_write_fifo, 'w') as fifo:
        fifo.write(text)

def server_read(context):
    server_alive(context)
    try:
        with open(context.server_read_fifo, 'r') as fifo:
            return fifo.read().strip()
    except IOError:
        # Wait for the server to die.
        while server_alive(context):
            time.sleep(0.1)

def sigchld(context):
    server_alive(context)

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


def before_all(context):

    atexit.register(cleanup, context, True)

    # We need to set these to None so that cleanup does not fail. It
    # expects to be able to check these fields without having to check
    # first for their existence.
    context.driver = None
    context.wm = None
    context.display = None
    context.server = None
    context.server_tempdir = None
    context.download_dir = None
    context.sc_tunnel = None
    context.sc_tunnel_tempdir = None
    context.builder = None

    setup_screenshots(context)

    context.selenium_quit = os.environ.get("SELENIUM_QUIT")
    context.behave_keep_tempdirs = os.environ.get("BEHAVE_KEEP_TEMPDIRS")
    context.visible = os.environ.get("SELENIUM_VISIBLE")

    userdata = context.config.userdata
    context.builder = builder = Builder(conf_path, userdata)

    dump_config(builder)
    if userdata.get("check_selenium_config", False):
        exit(0)

    browser_to_tag_value = {
        "INTERNETEXPLORER": "ie",
        "CHROME": "ch",
        "FIREFOX": "ff"
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

    desired_capabilities = {}
    if not builder.remote:
        visible = context.visible or \
            context.selenium_quit in ("never", "on-success", "on-enter")
        context.display = Display(visible=visible, size=(1024, 600))
        context.display.start()
        builder.update_ff_binary_env('DISPLAY')
        context.wm = subprocess.Popen(["openbox", "--sm-disable"])

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

        sc_tunnel_id = os.environ.get("SC_TUNNEL_ID")
        if not sc_tunnel_id:
            user, key = builder.SAUCELABS_CREDENTIALS.split(":")
            context.sc_tunnel, sc_tunnel_id, \
                context.sc_tunnel_tempdir = \
                outil.start_sc(builder.SC_TUNNEL_PATH, user, key)
        desired_capabilities["tunnel-identifier"] = sc_tunnel_id

    driver = builder.get_driver(desired_capabilities)
    context.driver = driver
    context.util = selenic.util.Util(driver,
                                     # Give more time if we are remote.
                                     5 if builder.remote else 2)
    # Without this, window sizes vary depending on the actual browser
    # used.
    context.initial_window_size = {"width": 1020, "height": 580}
    try:
        assert_true(driver.desired_capabilities["nativeEvents"],
                    "BTW's test suite require that native events be "
                    "available; you may have to use a different version of "
                    "your browser, one for which Selenium supports native "
                    "events.")
    except AssertionError:
        # Make sure to mark the test as failed.
        try:
            builder.set_test_status(driver.session_id, False)
        except httplib.HTTPException:
            # Ignore cases where we can't set the status.
            pass

        # We don't want to check SELENIUM_QUIT here.
        driver.quit()

        raise

    behave_wait = os.environ.get("BEHAVE_WAIT_BETWEEN_STEPS")
    context.behave_wait = behave_wait and float(behave_wait)

    context.server_tempdir = tempfile.mkdtemp()
    context.server_write_fifo = os.path.join(
        context.server_tempdir, "fifo_to_server")
    os.mkfifo(context.server_write_fifo)
    context.server_read_fifo = os.path.join(
        context.server_tempdir, "fifo_from_server")
    os.mkfifo(context.server_read_fifo)

    nginx_port = str(outil.get_unused_sauce_port())
    context.server = subprocess.Popen(
        ["utils/start_nginx", context.server_write_fifo,
         context.server_read_fifo, nginx_port], close_fds=True)
    signal.signal(signal.SIGCHLD, lambda *_: sigchld(context))

    # We must add the port to the server
    context.builder.SERVER += ":" + nginx_port

    context.selenium_logs = os.environ.get("SELENIUM_LOGS", False)


def after_all(context):
    cleanup(context, False)


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
                         [step_registry.registry.find_match(s) for s
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

    # This will block until the server is started.
    read = server_read(context)
    if read != 'started':
        raise ValueError("did not get the 'started' string")

    # Each scenario means logging in again.
    context.is_logged_in = False

    # These documents are not initially present.
    context.created_documents = {}

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
                server_write(context,
                             "patch changerecord_details to fail on ajax\n")
                server_read(context)
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

    if caches:
        server_write(context, 'clearcache ' + ' '.join(caches) + "\n")
        server_read(context)

    context.session_id = None


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

    """)

    # Reset the server between scenarios.
    server_write(context, "restart\n")

    # Close all extra tabs.
    if len(handles) > 1:
        for handle in handles:
            if handle != context.initial_window_handle:
                driver.switch_to_window(handle)
                driver.close()
        driver.switch_to_window(context.initial_window_handle)
    driver.delete_all_cookies()


def before_step(context, _step):
    server_alive(context)
    if context.behave_wait:
        time.sleep(context.behave_wait)


def after_step(context, step):
    driver = context.driver
    if step.status == "failed":
        name = os.path.join(context.screenshots_dir_path,
                            slugify(context.scenario.name + "_"
                                    + step.name) + ".png")
        driver.save_screenshot(name)
        print("")
        print("Captured screenshot:", name)
        print("")

    server_alive(context)
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
