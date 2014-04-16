from nose.tools import assert_equal, assert_raises  # pylint: disable=E0611


from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from behave import then, when, given, Given, \
    step_matcher  # pylint: disable=E0611
from selenium.common.exceptions import NoSuchElementException

import wedutil
from selenium_test import btw_util


@when("the user loads the top page of the lexicography app")
def user_load_lexicography(context):
    driver = context.driver
    config = context.selenic_config
    driver.get(config.SERVER + "/lexicography")


@then("the user gets the top page of the lexicography app")
def step_impl(context):
    driver = context.driver
    assert_equal(driver.title, "BTW | Lexicography")


@given("that the user has loaded the top page of the lexicography app")
def step_impl(context):
    context.execute_steps(u"""
    When the user loads the top page of the lexicography app
    Then the user gets the top page of the lexicography app
    """)


def setup_editor(context):
    util = context.util
    driver = context.driver

    wedutil.wait_for_editor(util)

    # Turning off tooltips makes the tests much easier to handle.
    driver.execute_script("""
    // Turn off tooltips
    wed_editor.preferences.set("tooltips", false);

    // Delete all tooltips.
    jQuery(".tooltip").remove();
    """)


@given("a new document")
def step_impl(context):
    util = context.util
    context.execute_steps(u"""
    When the user loads the top page of the lexicography app
    Then the user gets the top page of the lexicography app
    """)
    new = util.find_clickable_element((By.PARTIAL_LINK_TEXT, "New"))
    new.click()
    setup_editor(context)

    btw_util.record_document_features(context)


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


@given(u"wait {x} seconds")
@when(u"wait {x} seconds")
def step_impl(context, x):
    import time
    time.sleep(float(x))


step_matcher('re')

import collections

User = collections.namedtuple("User", ["login", "password"])

users = {
    "the user": User("foo", "foo"),
    "a user without permission to edit titles": User("foo2", "foo")
}


@given(ur"^(?P<user_desc>the user|a user without permission to edit titles) "
       ur"has logged in$")
@when(ur"^(?P<user_desc>the user) logs in$")
def step_impl(context, user_desc):
    driver = context.driver
    util = context.util
    config = context.selenic_config

    user = users[user_desc]
    if not util.can_set_cookies:
        driver.get(config.SERVER + "/login")
        name = util.find_element((By.NAME, "login"))
        pw = util.find_element((By.NAME, "password"))
        form = util.find_element((By.TAG_NAME, "form"))

        ActionChains(driver) \
            .click(name) \
            .send_keys(user.login) \
            .click(pw) \
            .send_keys(user.password) \
            .perform()

        form.submit()
    else:
        driver.get(config.SERVER)
        with open(context.server_write_fifo, 'w') as fifo:
            fifo.write("login " + user.login + " " + user.password + "\n")
        with open(context.server_read_fifo, 'r') as fifo:
            session_key = fifo.read().strip()
            driver.add_cookie({'name': 'sessionid',
                               'value': session_key})
            driver.add_cookie({'name': 'csrftoken',
                               'value': 'foo'})


@Given("^a document with a single sense(?: that does not have a subsense)?$")
def step_impl(context):
    context.execute_steps(u"""
    Given the user has logged in
    And a new document
    """)

    util = context.util

    sense = util.find_element((By.CSS_SELECTOR, r".btw\:sense"))
    assert_raises(
        NoSuchElementException,
        sense.find_element,
        (By.CSS_SELECTOR, r".btw\:subsense"))


@Given("^a document with a single sense that has a subsense$")
def step_impl(context):
    util = context.util
    context.execute_steps(u"""
    Given the user has logged in
    And that the user has loaded the top page of the lexicography app
    When the user searches for "one sense, one subsense"
    Then the search results show one entry for "one sense, one subsense"
    """)

    view_link = util.find_element((By.LINK_TEXT, "one sense, one subsense"))
    edit_link = view_link.find_element_by_xpath("../a[2]")

    edit_link.click()
    setup_editor(context)

    btw_util.record_document_features(context)


@Given("^a document that has no (?P<what>.*)$")
def step_impl(context, what):
    driver = context.driver
    context.execute_steps(u"""
    Given a document with a single sense that has a subsense
    """)

    # Make a CSS selector out of it
    what = "." + what.replace(":", r"\:")
    els = driver.find_elements_by_css_selector(what)

    assert_equal(len(els), 0)
