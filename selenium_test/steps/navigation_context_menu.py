from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import selenium.webdriver.support.expected_conditions as EC

from nose.tools import assert_equal  # pylint: disable=E0611

import selenic


@given('that a navigation context menu is open')
def step_impl(context):
    context.execute_steps(u"""
    When the user brings up a context menu on navigation item "[SENSE A]"
    Then a context menu is visible close to where the user clicked
    """)


@when('the user brings up a context menu on navigation item "{item}"')
def step_impl(context, item):
    driver = context.driver
    util = context.util
    sidebar = util.find_element((By.ID, "sidebar"))

    def cond(*_):
        return sidebar.find_element_by_partial_link_text(item)

    link = util.wait(cond)
    context.context_menu_trigger = link

    ActionChains(driver) \
        .context_click(link) \
        .perform()


@then("a context menu is visible close to where the user clicked")
def step_impl(context):
    util = context.util

    menu = util.find_element((By.CLASS_NAME, "wed-context-menu"))
    # The click was in the middle of the trigger.
    trigger = context.context_menu_trigger
    target = trigger.location
    target["x"] += trigger.size["width"] / 2
    target["y"] += trigger.size["height"] / 2
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
