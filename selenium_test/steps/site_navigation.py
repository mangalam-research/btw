# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true
import wedutil

from selenic.util import Condition, Result

step_matcher('re')

OPTION_TO_ID = {
    "Bibliography/Manage": "btw-bibliography-manage-sub"
}

@when(ur'the user navigates to page "(?P<page>.*?)"')
def step_impl(context, page):
    driver = context.driver
    if page == "Home":
        driver.get(context.selenic.SERVER)
    else:
        driver.get(context.selenic.SERVER)
        for part in page.split("/"):
            driver.find_element_by_link_text(part).click()

@then(ur'the menu for "(?P<page>.*>?)" is marked active')
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
        wedutil.wait_for_editor(context.util)

@then(ur'the user does not have the "(?P<option>.*?)" navigation option')
def step_impl(context, option):
    driver = context.driver
    assert_equal(len(driver.find_elements_by_id(OPTION_TO_ID[option])), 0)


@then(ur'the user has the "(?P<option>.*?)" navigation option')
def step_impl(context, option):
    driver = context.driver
    assert_equal(len(driver.find_elements_by_id(OPTION_TO_ID[option])), 1)
