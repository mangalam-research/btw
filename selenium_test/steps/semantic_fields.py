from nose.tools import assert_equal, assert_true

from selenium.webdriver.common.by import By
import selenium.webdriver.support.expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenic.datatables import Datatable
from selenic.util import Condition, Result

step_matcher('re')

@given("the user has loaded the main page of the semantic field application")
def step_impl(context):
    context.execute_steps(u"""
    Given the user has logged in
    """)

    driver = context.driver
    driver.get(context.builder.SERVER + "/semantic-fields")

    dt = Datatable("semantic field search", "semantic-field-table",
                   context.util)
    context.register_datatable(dt, True)
    # driver.execute_async_script("""
    # var done = arguments[0];
    # require(["velocity"], function (velocity) {
    #   velocity.mock = true;
    #   done();
    # });
    # """)


@then("no popovers are visible")
def step_impl(context):
    util = context.util

    def check(driver):
        return len(driver.find_elements_by_css_selector("div.popover")) == 0

    util.wait(check)


@when("the user closes the open popover")
def step_impl(context):
    driver = context.driver

    toggle = driver.execute_script("""
    var popover = document.querySelector("div.popover");
    var toggle = document.querySelector("[aria-describedby="+popover.id + "]");
    return toggle
    """)

    toggle.click()


@when(ur"the user clicks on the help for the (?P<what>search field|"
      ur"aspect combo box|scope combo box)")
def step_impl(context, what):
    util = context.util

    if what == "search field":
        selector = ".semantic-field-search-help .search-help"
        index = 0
    elif what == "aspect combo box":
        selector = ".semantic-field-search-help .aspect-help"
        index = 1
    elif what == "scope combo box":
        selector = ".semantic-field-search-help .scope-help"
        index = 2
    else:
        raise ValueError("unexpected value for ``what``: " + what)

    # We have to use execute_script because the elements are invisible.
    context.expected_popover_text = context.driver.execute_script(r"""
    return document.querySelector(arguments[0]).textContent
      .split(/\s+/).join(" ").trim();
    """, selector)

    popover = util.find_elements((By.CSS_SELECTOR,
                                  "i.fa-question-circle.text-info"))[index]

    popover.click()

@then("the help for the (?:search field|aspect combo box|scope combo box) "
      "is visible")
def step_impl(context):
    util = context.util

    def check(driver):
        popover_text = util.find_element((By.CSS_SELECTOR, "div.popover")).text
        return popover_text == context.expected_popover_text

    util.wait(check)


@when(ur'the user searches (?P<mode>literally |)for "(?P<search>.*?)"')
def step_impl(context, mode, search):
    dt = context.default_datatable

    if mode == "literally ":
        search = '"' + search + '"'

    dt.fill_field("Search", search)


@then(ur"there is one result")
def step_impl(context):
    actual = context.default_datatable.wait_for_results(1)
    assert_equal(actual, 1)


@then(ur"there are (?P<count>\d+|no) results")
def step_impl(context, count):
    count = 0 if count == "no" else int(count)
    actual = context.default_datatable.wait_for_results(count)
    assert_equal(actual, count)


@then(ur"the first result shows: (?P<result>.*)")
def step_impl(context, result):
    row = context.default_datatable.get_result(0)
    text = row.find_element_by_class_name("sf-breadcrumbs").text
    assert_equal(text, result)


@when(ur"the user changes the search to search for lexemes")
def step_impl(context):
    context.default_datatable.set_select_option("in", "lexemes")

@when(ur"the user changes the search to search for (?P<what>BTW|HTE|all) "
      ur"fields")
def step_impl(context, what):
    if what == "BTW":
        value = "custom BTW fields"
    elif what == "HTE":
        value = "HTE fields"
    elif what == "all":
        value = "all fields"
    else:
        raise ValueError("unexpected value: " + what)

    context.default_datatable.set_select_option("among", value)


@when(ur'the user clicks on "(?P<what>.*)" in the (?P<which>first|second) '
      ur'result')
def step_impl(context, what, which):
    util = context.util
    result_ix = {
        "first": 0,
        "second": 1
    }[which]
    result = context.default_datatable.get_result(result_ix)

    def find(*_):
        links = result.find_elements_by_link_text(what)
        link = links[0] if len(links) else None
        return Result(link is not None, link)

    result = Condition(util, find).wait()
    assert_true(result, "there should be a link")

    result.payload.click()


def get_panes(driver):
    panes = driver.execute_script("""
    var panes = document.querySelectorAll(
      "div.semantic-field-details-panel");
    return Array.prototype.filter.call(panes, function (x) {
      return x.style.display !== "none";
    });
    """)
    return panes


@when(ur'the user clicks on "(?P<what>.*)" in the first detail pane')
def step_impl(context, what):
    panes = get_panes(context.driver)
    pane = panes[0]
    link = pane.find_element_by_link_text(what)
    link.click()


@then(ur'there (?:is|are) (?P<count>one|no|\d+) detail panes?')
def step_impl(context, count):
    # We need to remove the template, which remains undisplayed...
    if count == "one":
        count = 1
    elif count == "no":
        count = 0
    else:
        count = int(count)

    def check(driver):
        panes = get_panes(driver)
        return Result(len(panes) == count, len(panes))

    result = Condition(context.util, check).wait()

    assert_equal(result.payload, count)


@then(ur'the first detail pane shows: (?P<what>.*)')
def step_impl(context, what):
    util = context.util
    panel = util.find_element((By.CSS_SELECTOR,
                               "div.semantic-field-details-panel .panel-body"))

    def check(*_):
        crumbs = panel.find_elements_by_class_name("sf-breadcrumbs")
        # The check can be done so fast that we can a
        # StaleElementReferenceException. We'll just retry.
        try:
            text = crumbs[0].text if len(crumbs) > 0 else None
        except StaleElementReferenceException:
            return Result(False, None)

        return Result(text == what, text)

    result = Condition(util, check).wait()

    if result.payload is None:
        raise ValueError(
            "kept getting StaleElementReferenceException, somehow")

    assert_equal(result.payload, what)

@when(ur'the user clicks on the first pane\'s navigation button '
      ur'to go to the (?P<what>first|last|previous|next) page')
def step_impl(context, what):
    util = context.util

    button = util.find_element((By.CSS_SELECTOR,
                                "div.semantic-field-details-panel .btn." +
                                what))
    button.click()


@when(ur'the user clicks on the first pane\'s button '
      ur'to (?P<what>close the pane|close all panes)')
def step_impl(context, what):
    util = context.util

    selector = {
        "close the pane": "close-panel",
        "close all panes": "close-all-panels"
    }[what]

    button = util.find_element(
        (By.CSS_SELECTOR, "div.semantic-field-details-panel .btn." + selector))
    button.click()


@when(ur'the user clicks on the "Create Child" button in the first detail '
      ur'pane')
def step_impl(context):
    util = context.util
    button = util.find_element(
        (By.CSS_SELECTOR,
         "div.semantic-field-details-panel .btn.create-child"))
    button.click()


@then(ur'there is a form for creating a custom field in the first detail pane')
def step_impl(context):
    context.util.find_element(
        (By.CSS_SELECTOR,
         "div.semantic-field-details-panel form.add-child-form"))


@when(ur'the user cancels the form for creating a custom field in the '
      ur'first detail pane')
def step_impl(context):
    util = context.util
    button = util.find_element(
        (By.CSS_SELECTOR, "div.semantic-field-details-panel .btn.cancel"))
    button.click()


@then(ur'there is no form for creating a custom field in the first detail '
      ur'pane')
def step_impl(context):
    context.util.wait_until_not(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR,
             "div.semantic-field-details-panel form.add-child-form")))


@when(ur'the user types "FOO" in the "Heading" field in the first form')
def step_impl(context):
    util = context.util
    field = util.find_element(
        (By.CSS_SELECTOR,
         "div.semantic-field-details-panel form.add-child-form "
         "textarea[name='heading']"))
    field.send_keys("FOO")


@when(ur'the user clicks the "Create" button in the first form')
def step_impl(context):
    util = context.util
    button = util.find_element(
        (By.CSS_SELECTOR,
         "div.semantic-field-details-panel .btn[type='submit']"))
    button.click()


@then(ur'the first detail pane shows the child "FOO"')
def step_impl(context):
    def check(driver):
        texts = driver.execute_script("""
        var children = document.querySelectorAll(
          "div.semantic-field-details-panel .sf-children .sf-link");
        return Array.prototype.map.call(children, function (x) {
          return x.textContent;
        });
        """)

        return Result("FOO" in texts, texts)

    result = Condition(context.util, check).wait()

    assert_true(result)
