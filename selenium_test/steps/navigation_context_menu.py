from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import selenium.webdriver.support.expected_conditions as EC

from nose.tools import assert_equal  # pylint: disable=E0611
from behave import then, when, given, step_matcher  # pylint: disable=E0611

from selenium_test import btw_util

import selenic
import wedutil


@given('that a navigation context menu is open')
def step_impl(context):
    context.execute_steps("""
    When the user brings up a context menu on navigation item "[SENSE A]"
    Then a context menu is visible close to where the user clicked
    """)


step_matcher("re")


@when(r'the user brings up a context menu on navigation item '
      r'"(?P<item>.*?)"(?: under "(?P<under>.*?)")?')
def step_impl(context, item, under):
    driver = context.driver
    util = context.util

    def cond(*_):
        ret = driver.execute_script("""
        const [item, under] = arguments;
        const $ = jQuery;

        const $search_point = under ?
          $(`a:contains(${under})`).parent() : $(".wed-sidebar");

        const ret = $search_point.find(`a:contains(${item})`)[0];
        let rect = {};
        if (ret) {
          ret.scrollIntoView(true);
          rect = ret.getBoundingClientRect();
        }
        console.log("XXX", rect);
        return [ret, {
          x: rect.left + 10,
          y: rect.top + 10,
        }];
        """, item, under)
        return ret if ret[0] else None

    link, location = util.wait(cond)

    context.context_menu_location = location
    ActionChains(driver) \
        .move_to_element_with_offset(context.origin_object, location["x"],
                                     location["y"]) \
        .context_click() \
        .perform()


step_matcher("parse")


@then("a context menu is visible close to where the user clicked")
def step_impl(context):
    util = context.util

    menu = util.find_element((By.CLASS_NAME, "wed-context-menu"))
    # The click was in the middle of the trigger.
    target = context.context_menu_location
    rect = context.driver.execute_script("""
    const rect = arguments[0].getBoundingClientRect();
    return { x: rect.left, y: rect.top };
    """, menu)
    assert_equal(selenic.util.locations_within(rect, target, 15), '')


@when('the user clicks the second context menu option')
def step_impl(context):
    util = context.util

    link = util.wait(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, ".wed-context-menu a.dropdown-item:nth-of-type(2)")))
    link.click()


@when('the user clicks the context menu option "{item}"')
def step_impl(context, item):
    util = context.util

    link = util.find_element((By.LINK_TEXT, item))
    btw_util.scroll_into_view(context.driver, link)
    util.wait(EC.visibility_of(link))
    #
    # The following code prevents a problem in IE 10. Without this
    # code, the scenarios "adding custom text to a reference" and
    # "adding custom text to a reference when there is already text"
    # both fail in IE 10 because Selenium clicks on the menu item that
    # shows the element's documentation.
    #
    # Facts:
    #
    # 1. The problem cannot be reproduced manually.
    #
    # 2. Adding time.sleep([x seconds]) before the wait call above or
    # between the wait call and the link.click() call does not fix the
    # issue.
    #
    # 3. Upgrading Selenium does not fix the issue.
    #
    # 4. Scrolling the editor pane all the way down before excuting
    # this step does not fix the issue.
    #
    # 5. An empty execute_script or an execute_script that does not
    # change the link does not fix the issue.
    #
    # We do not put borders on links. Hypothesis: the CSS modification
    # causes IEDriver to recompute or recache the element's location
    # so that the next click works.
    #
    # A bug report should be submitted for this.
    #
    if util.ie and context.driver.desired_capabilities["version"] == "10":
        context.driver.execute_script("""
        arguments[0].style.border = "0px";
        """, link)
    link.click()


@then('there is no context menu option "{item}"')
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


@then('the heading for the first btw:explanation element is not '
      'actionable')
def step_impl(context):
    util = context.util

    heading = util.find_element((By.CSS_SELECTOR,
                                 r".btw\:explanation>.head"))

    # This is necessary to prevent the next test form happening too early.
    wedutil.wait_for_first_validation_complete(util)
    assert_equal(
        len(heading.find_elements_by_css_selector("i")), 0)
