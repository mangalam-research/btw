from nose.tools import assert_equal  # pylint: disable=E0611

from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from behave import then, when, given  # pylint: disable=E0611

import wedutil
from selenium_test import btw_util


@given("the user has logged in")
@when("the user logs in")
def step_impl(context):
    driver = context.driver
    util = context.util
    config = context.selenic_config

    driver.get(config.SERVER + "/login")
    name = util.find_element((By.NAME, "username"))
    pw = util.find_element((By.NAME, "password"))
    form = util.find_element((By.TAG_NAME, "form"))

    ActionChains(driver) \
        .click(name) \
        .send_keys("foo") \
        .click(pw) \
        .send_keys("foo") \
        .perform()

    form.submit()


@when("the user loads the top page of the lexicography app")
def user_load_lexicography(context):
    driver = context.driver
    config = context.selenic_config
    driver.get(config.SERVER + "/lexicography")


@then("the user gets the top page of the lexicography app")
def step_impl(context):
    driver = context.driver
    assert_equal(driver.title, "BTW | Lexicography")


@given("a new document")
def step_impl(context):
    util = context.util
    context.execute_steps(u"""
    When the user loads the top page of the lexicography app
    Then the user gets the top page of the lexicography app
    """)
    new = util.find_clickable_element((By.PARTIAL_LINK_TEXT, "New"))
    new.click()
    wedutil.wait_for_editor(util)

    # Some steps must know what the state of the document was before
    # transformations are applied, so record it.
    if context.require_sense_recording:
        # We gather the btw:english-term text associated with each btw:sense.
        context.initial_sense_terms = btw_util.get_sense_terms(util)

    if context.require_rendition_recording:
        sense_els = btw_util.get_senses(util)
        context.initial_renditions_by_sense = {}
        for sense in context.require_rendition_recording:
            sense_el = sense_els[btw_util.sense_label_to_index(sense)]
            renditions = btw_util.get_rendition_terms_for_sense(sense_el)

            context.initial_renditions_by_sense[sense] = renditions


@given("a context menu is not visible")
@then("a context menu is not visible")
def context_menu_is_not_visible(context):
    wedutil.wait_until_a_context_menu_is_not_visible(context.util)


@when('the user resizes the window so that the editor pane has a vertical '
      'scrollbar')
def step_impl(context):
    util = context.util
    wedutil.set_window_size(util, 683, 741)


@when("the user scrolls the editor pane down")
def step_impl(context):
    driver = context.driver
    util = context.util

    # We must not call it before the body is fully loaded.
    driver.execute_script("""
    delete window.__selenic_scrolled;
    jQuery(function () {
      window.scrollTo(0, document.body.scrollHeight);
      window.__selenic_scrolled = true;
    });
    """)

    def cond(*_):
        return driver.execute_script("""
        return window.__selenic_scrolled;
        """)
    util.wait(cond)

    context.window_scroll_top = util.window_scroll_top()
    context.window_scroll_left = util.window_scroll_left()
