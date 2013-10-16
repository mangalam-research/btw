import os

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
    context.driver = config.get_driver()
    context.selenic_config = config
    context.util = selenic.util.Util(context.driver)


def after_all(context):
    driver = context.driver
    config.set_test_status(driver.session_id, not context.failed)
    if not context.failed and "BEHAVE_NO_QUIT" not in os.environ:
        driver.quit()


def before_scenario(context, scenario):
    driver = context.driver
    context.before_scenario_window_size = driver.get_window_size()

    # Record whether we need sense recording.  What we are doing here
    # is scanning the list of steps for this scenario, seeking the
    # actual implementation of each step and verifying whether the
    # function is present in btw_util.require_sense_recording. This
    # dict was populated by using the decorator in btw_util.
    context.require_sense_recording = \
        any(s for s in scenario.steps if
            step_registry.registry.find_match(s).func
            in btw_util.require_sense_recording)


def after_scenario(context, _scenario):
    driver = context.driver
    util = context.util

    window_size = driver.get_window_size()
    if window_size != context.before_scenario_window_size:
        wedutil.set_window_size(util,
                                context.before_scenario_window_size["width"],
                                context.before_scenario_window_size["height"])

    # If the scenario ends on an editor window, we want to move away
    # from it NOW so that the next scenario does not trigger the alert
    # about moving away.
    if driver.execute_script("return window.wed_editor !== undefined;"):
        driver.get(context.selenic_config.SERVER + "/lexicography")
        alert = driver.switch_to_alert()
        alert.accept()
