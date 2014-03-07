from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import selenium.webdriver.support.expected_conditions as EC

from nose.tools import assert_equal  # pylint: disable=E0611
from behave import then, when, given, step_matcher  # pylint: disable=E0611

import selenic


@given('that a navigation context menu is open')
def step_impl(context):
    context.execute_steps(u"""
    When the user brings up a context menu on navigation item "[SENSE A]"
    Then a context menu is visible close to where the user clicked
    """)


step_matcher("re")


@when(ur'the user brings up a context menu on navigation item '
      ur'"(?P<item>.*?)"(?:under "(?P<under>.*?)")?')
def step_impl(context, item, under):
    driver = context.driver
    util = context.util
    search_point = util.find_element((By.ID, "sidebar"))

    if under:
        search_point = util.wait(
            lambda: search_point.find_element_by_partial_link_text(under)).\
            find_element_by_xpath("..")

    def cond(*_):
        return search_point.find_element_by_partial_link_text(item)

    link = util.wait(cond)

    # We must do this to make sure that the element is completely
    # visible.
    driver.execute_script("""
    var el = arguments[0];
    el.scrollIntoView(true);
    """, link)

    target = link.location
    target["x"] += 10
    target["y"] += 10
    context.context_menu_location = target

    ActionChains(driver) \
        .move_to_element_with_offset(link, 10, 10) \
        .context_click() \
        .perform()


step_matcher("parse")


@then("a context menu is visible close to where the user clicked")
def step_impl(context):
    util = context.util

    menu = util.find_element((By.CLASS_NAME, "wed-context-menu"))
    # The click was in the middle of the trigger.
    target = context.context_menu_location
    assert_equal(selenic.util.locations_within(menu.location, target, 10), '')


@when(u'the user clicks the first context menu option')
def step_impl(context):
    util = context.util

    link = util.wait(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, ".wed-context-menu li>a")))
    context.clicked_context_menu_item = \
        util.get_text_excluding_children(link).strip()
    link.click()


@when(u'the user clicks the context menu option "{item}"')
def step_impl(context, item):
    util = context.util

    link = util.wait(EC.element_to_be_clickable((By.LINK_TEXT, item)))
    context.clicked_context_menu_item = \
        util.get_text_excluding_children(link).strip()
    link.click()
