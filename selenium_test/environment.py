import os
import time
import urllib2
import tempfile
import subprocess
import shutil
import httplib

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

import selenic.util
from behave import step_registry

# Turn on long messages. This will apply to all assertions unless turned off
# somewhere else.
from nose.tools import assert_equal  # pylint: disable=E0611
assert_equal.im_self.longMessage = True

import wedutil
from selenium_test import btw_util


def before_all(context):
    driver = config.get_driver()
    context.driver = driver
    context.util = selenic.util.Util(driver)
    context.selenic_config = config
    # Without this, window sizes vary depending on the actual browser
    # used.
    driver.set_window_size(1020, 580)
    context.initial_window_size = {"width": 1020, "height": 580}
    try:
        assert_true(driver.desired_capabilities.get("nativeEvents", False),
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
    context.server_fifo = os.path.join(context.server_tempdir, "fifo")
    os.mkfifo(context.server_fifo)
    context.server = subprocess.Popen(
        ["utils/start_nginx", context.server_fifo])


def after_all(context):
    driver = context.driver

    try:
        config.set_test_status(driver.session_id, not context.failed)
    except httplib.HTTPException:
        # Ignore cases where we can't set the status.
        pass
    selenium_quit = os.environ.get("SELENIUM_QUIT")
    if not ((selenium_quit == "never") or
            (context.failed and selenium_quit == "on-success")):
        driver.quit()
    context.server.terminate()
    shutil.rmtree(context.server_tempdir, True)


def before_scenario(context, scenario):
    driver = context.driver
    util = context.util

    window_size = driver.get_window_size()
    if window_size != context.initial_window_size:
        driver.set_window_size(context.initial_window_size["width"],
                               context.initial_window_size["height"])

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
            urllib2.urlopen(config.SERVER + "/login")
            found = True
        except urllib2.URLError:
            time.sleep(0.5)


def after_scenario(context, _scenario):
    driver = context.driver

    # If the scenario ends on an editor window, we want to move away
    # from it NOW so that the next scenario does not trigger the alert
    # about moving away.
    if driver.execute_script("return window.wed_editor !== undefined;"):
        driver.get(context.selenic_config.SERVER + "/lexicography")
        alert = driver.switch_to_alert()
        alert.accept()

    # Reset the server between scenarios.
    with open(context.server_fifo, 'w') as fifo:
        fifo.write("1")


def before_step(context, _step):
    if context.behave_wait:
        time.sleep(context.behave_wait)
