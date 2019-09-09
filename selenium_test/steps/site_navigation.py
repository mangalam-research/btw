# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true
import wedutil

from selenic.util import Condition, Result

from selenium_test import btw_util

step_matcher('re')

OPTION_TO_ID = {
    "Bibliography/Manage": "btw-bibliography-manage-sub"
}

@when(r'the user navigates to page "(?P<page>.*?)"')
def step_impl(context, page):
    driver = context.driver
    if page == "Home":
        driver.get(context.builder.SERVER)
    else:
        driver.get(context.builder.SERVER)
        for part in page.split("/"):
            driver.find_element_by_link_text(part).click()

@then(r'the menu for "(?P<page>.*>?)" is marked active')
def step_impl(context, page):
    driver = context.driver
    parts = page.split("/")

    def check(driver):
        active = driver.execute_script("""
        var actives = document.querySelectorAll(
            "#btw-site-navigation .active>a");
        return Array.prototype.map.call(actives, function (active) {
            var ret = [];
            Array.prototype.forEach.call(active.childNodes,
            function (node) {
                if (node.nodeType === Node.TEXT_NODE)
                    ret.push(node.textContent.trim());
            });
            return ret.join('');
        });
        """)
        return Result(active == parts, [active, parts])

    result = Condition(context.util, check).wait()
    if not result:
        active, parts = result.payload
        assert_equal(active, parts)

    # We need this, otherwise the page will be reloaded too fast.
    if page == "Lexicography/New Article":
        btw_util.wait_for_editor(context.util)

@then(r'the user does not have the "(?P<option>.*?)" navigation option')
def step_impl(context, option):
    driver = context.driver
    assert_equal(len(driver.find_elements_by_id(OPTION_TO_ID[option])), 0)


@then(r'the user has the "(?P<option>.*?)" navigation option')
def step_impl(context, option):
    driver = context.driver
    assert_equal(len(driver.find_elements_by_id(OPTION_TO_ID[option])), 1)
