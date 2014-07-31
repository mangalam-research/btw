import os
import time
import urllib2
import tempfile
import subprocess
import shutil
import httplib
import atexit
from distutils.version import StrictVersion

# pylint: disable=E0611
from nose.tools import assert_true

_dirname = os.path.dirname(__file__)

local_conf_path = os.path.join(os.path.dirname(_dirname),
                               "build", "config", "selenium_local_config.py")


conf_path = os.path.join(os.path.dirname(_dirname),
                         "build", "config", "selenium_test_config.py")
conf = {"__file__": conf_path}
execfile(conf_path, conf)

config = conf["Config"](local_conf_path)

import selenium
import selenic.util
from behave import step_registry

# Turn on long messages. This will apply to all assertions unless turned off
# somewhere else.
from nose.tools import assert_equal  # pylint: disable=E0611
assert_equal.im_self.longMessage = True

import wedutil
from selenium_test import btw_util


def cleanup(context, failed):
    driver = context.driver

    if driver:
        try:
            config.set_test_status(
                driver.session_id, not (failed or context.failed))
        except httplib.HTTPException:
            # Ignore cases where we can't set the status.
            pass
        selenium_quit = os.environ.get("SELENIUM_QUIT")
        if not ((selenium_quit == "never") or
                (context.failed and selenium_quit == "on-success")):
            driver.quit()
        context.driver = None

    if context.server:
        context.server.terminate()
        context.server = None

    if context.server_tempdir:
        shutil.rmtree(context.server_tempdir, True)
        context.server_tempdir = None


def before_all(context):

    atexit.register(cleanup, context, True)

    driver = config.get_driver()
    context.driver = driver
    context.util = selenic.util.Util(driver,
                                     # Give more time if we are remote.
                                     4 if config.remote else 2)
    context.selenic_config = config

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
            config.set_test_status(driver.session_id, False)
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

    context.server = subprocess.Popen(
        ["utils/start_nginx", context.server_write_fifo,
         context.server_read_fifo])

    context.selenium_logs = os.environ.get("SELENIUM_LOGS", False)


def after_all(context):
    cleanup(context, False)


def before_scenario(context, scenario):
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

    found = False
    while not found:
        try:
            f = urllib2.urlopen(config.SERVER + "/login")
            found = f.getcode() == 200
        except urllib2.URLError:
            time.sleep(0.1)

    # Each scenario means logging in again.
    context.is_logged_in = False


def after_scenario(context, _scenario):
    driver = context.driver

    # Close all extra tabs.
    for handle in driver.window_handles:
        if handle != context.initial_window_handle:
            driver.switch_to_window(handle)
            driver.close()
    driver.switch_to_window(context.initial_window_handle)

    # Reset the server between scenarios.
    with open(context.server_write_fifo, 'w') as fifo:
        fifo.write("restart\n")

    driver.execute_script("""
    // Overwrite onbeforeunload to prevent the dialog from showing up.
    if (window.wed_editor)
        window.onbeforeunload = function () {};
    """)
    driver.delete_all_cookies()


def before_step(context, _step):
    if context.behave_wait:
        time.sleep(context.behave_wait)


def after_step(context, _step):
    driver = context.driver
    # Perform this query only if SELENIUM_LOGS is on.
    if context.selenium_logs:
        logs = driver.execute_script("""
        return window.selenium_log;
        """)
        if logs:
            print
            print "JavaScript log:"
            print "\n".join(repr(x) for x in logs)
            print
            driver.execute_script("""
            window.selenium_log = [];
            """)
