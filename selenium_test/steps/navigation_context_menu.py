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

    def cond(*_):
        ret = driver.execute_script("""
        var item = arguments[0];
        var under = arguments[1];

        var $ = jQuery;

        var $search_point = under ?
            $("a:contains(" + under + ")").parent() : $("#sidebar");

        var $ret = $search_point.find("a:contains(" + item + ")");
        var ret = $ret[0];
        if (ret)
          ret.scrollIntoView(true);
        var offset = $ret.offset();
        return [ret, {'x': offset.left, 'y': offset.top}];
        """, item, under)
        return ret if ret[0] else None

    link, location = util.wait(cond)

    target = location
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
    context.clicked_context_menu_item = item
    link.click()


@then(u'there is no context menu option "{item}"')
def step_impl(context, item):
    driver = context.driver
    util = context.util

    def cond(*_):
        return driver.execute_script("""
        var item = arguments[0];
        var under = arguments[1];

        var $ = jQuery;

        var $menu = $(".wed-context-menu");
        if (!$menu[0])
            return false;

        return $menu.find("a:contains('" + item + "')").length === 0;

        """, item)

    util.wait(cond)
