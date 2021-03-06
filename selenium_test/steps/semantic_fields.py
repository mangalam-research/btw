from nose.tools import assert_equal, assert_true

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import selenium.webdriver.support.expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenic.datatables import Datatable
from selenic.util import Condition, Result

from selenium_test.btw_util import velocity_mock

step_matcher('re')

@given(r"(?P<user>.+?) has loaded the main page of the semantic "
       r"field application")
def step_impl(context, user):
    context.execute_steps("""
    Given {0} has logged in
    """.format(user))

    driver = context.driver
    driver.get(context.builder.SERVER + "/semantic-fields")

    dt = Datatable(context.util, "semantic field search",
                   "semantic-field-table")
    context.register_table(dt, True)
    velocity_mock(driver, True)


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

    ActionChains(driver) \
        .move_to_element_with_offset(toggle, 1, 1) \
        .click() \
        .perform()


@when(r"the user clicks on the help for the (?P<what>search field|"
      r"aspect combo box|scope combo box|root combo box)")
def step_impl(context, what):
    util = context.util

    if what == "search field":
        selector = "p.search-help"
        index = 0
    elif what == "aspect combo box":
        selector = "p.aspect-help"
        index = 1
    elif what == "scope combo box":
        selector = "p.scope-help"
        index = 2
    elif what == "root combo box":
        selector = "p.root-help"
        index = 3
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

@then("the help for the (?:search field|aspect combo box|"
      "scope combo box|root combo box) "
      "is visible")
def step_impl(context):
    util = context.util

    def check(driver):
        popover_text = util.find_element((By.CSS_SELECTOR, "div.popover")).text
        return popover_text == context.expected_popover_text

    util.wait(check)


@when(r'the user searches (?P<mode>literally |)for "(?P<search>.*?)"')
def step_impl(context, mode, search):
    dt = context.default_table

    if mode == "literally ":
        search = '"' + search + '"'

    dt.fill_field("Search", search)


@then(r"there is one result")
def step_impl(context):
    actual = context.default_table.wait_for_results(1)
    assert_equal(actual, 1)


@then(r"there are (?P<count>\d+|no) results")
def step_impl(context, count):
    count = 0 if count == "no" else int(count)
    actual = context.default_table.wait_for_results(count)
    assert_equal(actual, count)


@then(r"the first result shows: (?P<result>.*)")
def step_impl(context, result):
    row = context.default_table.get_result(0)
    text = row.find_element_by_class_name("sf-breadcrumbs").text
    assert_equal(text, result)


@when(r"the user changes the search to search for lexemes")
def step_impl(context):
    context.default_table.set_select_option("in", "lexemes")

@when(r"the user changes the search to search for (?P<what>BTW|HTE|all) "
      r"fields")
def step_impl(context, what):
    if what == "BTW":
        value = "custom BTW fields"
    elif what == "HTE":
        value = "HTE fields"
    elif what == "all":
        value = "all fields"
    else:
        raise ValueError("unexpected value: " + what)

    context.default_table.set_select_option("among", value)


@when(r"the user changes the search to search for fields under "
      r"(?P<what>all roots|Society \(03\))")
def step_impl(context, what):
    if what == "all roots":
        value = "all fields"
    elif what == "Society (03)":
        value = "Society (03)"
    else:
        raise ValueError("unexpected value: " + what)

    context.default_table.set_select_option("under", value)


@when(r'the user clicks on "(?P<what>.*)" in the (?P<which>first|second) '
      r'result')
def step_impl(context, what, which):
    util = context.util
    result_ix = {
        "first": 0,
        "second": 1
    }[which]
    result = context.default_table.get_result(result_ix)

    def find(*_):
        links = result.find_elements_by_link_text(what)
        link = links[0] if len(links) else None
        return Result(link is not None, link)

    result = Condition(util, find).wait()
    assert_true(result, "there should be a link")

    result.payload.click()


def get_panes(driver):
    panes = driver.execute_script("""
    var panes = document.querySelectorAll("div.semantic-field-details-card");
    return Array.prototype.filter.call(panes, function (x) {
      return x.style.display !== "none";
    });
    """)
    return panes


@when(r'the user clicks on "(?P<what>.*)" in the first detail pane')
def step_impl(context, what):
    panes = get_panes(context.driver)
    pane = panes[0]
    link = pane.find_element_by_link_text(what)
    link.click()


@then(r'there (?:is|are) (?P<count>one|no|\d+) detail panes?')
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


@then(r'the first detail pane shows: (?P<what>.*)')
def step_impl(context, what):
    util = context.util
    card = util.find_element((By.CSS_SELECTOR,
                              "div.semantic-field-details-card .card-body"))

    stale = object()

    def check(*_):
        crumbs = card.find_elements_by_class_name("sf-breadcrumbs")
        # The check can be done so fast that we can a
        # StaleElementReferenceException. We'll just retry.
        try:
            text = crumbs[0].text if len(crumbs) > 0 else None
        except StaleElementReferenceException:
            return Result(False, stale)

        return Result(text == what, text)

    result = Condition(util, check).wait()

    if result.payload is stale:
        raise ValueError(
            "kept getting StaleElementReferenceException, somehow")

    assert_equal(result.payload, what)

@when(r'the user clicks on the first pane\'s navigation button '
      r'to go to the (?P<what>first|last|previous|next) page')
def step_impl(context, what):
    util = context.util

    button = util.find_element((By.CSS_SELECTOR,
                                "div.semantic-field-details-card .btn." +
                                what))
    button.click()


@when(r'the user clicks on the first pane\'s button '
      r'to (?P<what>close the pane|close all panes)')
def step_impl(context, what):
    util = context.util

    if context.sf_editor_test:
        selectors = {
            "close the pane": "close-navigator",
            "close all panes": "close-all-navigators"
        }
    else:
        selectors = {
            "close the pane": "close-card",
            "close all panes": "close-all-cards"
        }

    selector = selectors[what]

    button = util.find_element(
        (By.CSS_SELECTOR, "div.semantic-field-details-card .btn." + selector))
    button.click()


@when(r'the user clicks on the (?P<which>edit|"Create Child"|'
      r'"Create New POS") button in the first detail pane')
def step_impl(context, which):
    util = context.util
    selector = {
        '"Create Child"': "create-child",
        '"Create New POS"': "create-related-by-pos",
        'edit': 'edit-field'
    }[which]

    button = util.wait(EC.visibility_of_element_located(
        (By.CSS_SELECTOR,
         "div.semantic-field-details-card .btn." + selector)))
    button.click()


@then(r'there is no (?P<which>edit|"Create Child"|'
      r'"Create New POS") button in the first detail pane')
def step_impl(context, which):
    util = context.util
    selector = {
        '"Create Child"': "create-child",
        '"Create New POS"': "create-related-by-pos",
        'edit': 'edit-field'
    }[which]

    util.wait_until_not(EC.visibility_of_element_located(
        (By.CSS_SELECTOR,
         "div.semantic-field-details-card .btn." + selector)))


@when(r'the user clicks on the "Create Field" button under the table')
def step_impl(context):
    util = context.util
    button = util.find_element((By.CSS_SELECTOR, ".btn.create-field"))
    button.click()


@then(r'there is no "Create Field" button under the table')
def step_impl(context):
    util = context.util
    util.wait_until_not(EC.visibility_of_element_located(
        (By.CSS_SELECTOR, ".btn.create-field")))


@then(r'there is (?P<present>a|no) form for '
      r'(?P<which>creating|editing) a custom field in '
      r'the first detail pane')
def step_impl(context, present, which):
    util = context.util
    css_class = {
        "creating": "add-child",
        "editing": "edit-field"
    }[which]

    selector = (By.CSS_SELECTOR,
                "div.semantic-field-details-card form.{0}-form"
                .format(css_class))

    if present == "a":
        util.find_element(selector)
    elif present == "no":
        util.wait_until_not(EC.presence_of_element_located(selector))
    else:
        raise ValueError("present has an unexpected value: " + present)

@then(r'there is a form for creating a custom field under the table')
def step_impl(context):
    context.util.find_element(
        (By.CSS_SELECTOR, "form.add-child-form"))


@when(r'the user cancels the form for (?:editing|creating) a custom '
      r'field in the first detail pane')
def step_impl(context):
    util = context.util
    button = util.find_element(
        (By.CSS_SELECTOR, "div.semantic-field-details-card .btn.cancel"))
    button.click()


@then(r'the "Heading" field in the first form contains the text "CUSTOM"')
def step_impl(context):
    util = context.util
    field = util.find_element(
        (By.CSS_SELECTOR, "form textarea[name='heading']"))
    assert_equal(field.get_attribute("value"), "CUSTOM")

@when(r'the user types "FOO" in the "Heading" field in the first form')
def step_impl(context):
    util = context.util
    field = util.find_element(
        (By.CSS_SELECTOR, "form textarea[name='heading']"))
    field.send_keys("FOO")

@when(r'the user clears the "Heading" field in the first form')
def step_impl(context):
    util = context.util
    driver = context.driver

    field = util.find_element(
        (By.CSS_SELECTOR, "form textarea[name='heading']"))
    field.clear()


@when(r'the user clicks the "(?:Create|Submit)" button in the first form')
def step_impl(context):
    util = context.util
    button = util.find_element(
        (By.CSS_SELECTOR, "form .btn.submit"))
    button.click()


@then(r'the first form\'s heading field has an error')
def step_impl(context):
    util = context.util

    def cond(driver):
        return driver.execute_script("""
        return jQuery("form *[name='heading']").next(".invalid-feedback")
          .text() !== "";
        """)

    util.wait(cond)


@then(r'the first detail pane shows the child "FOO"')
def step_impl(context):
    def check(driver):
        texts = driver.execute_script("""
        var children = document.querySelectorAll(
          "div.semantic-field-details-card .sf-children .sf-link");
        return Array.prototype.map.call(children, function (x) {
          return x.textContent;
        });
        """)

        return Result("FOO" in texts, texts)

    result = Condition(context.util, check).wait()

    assert_true(result)

@then(r'the first detail pane shows the other part of speech "FOO \(None\)"')
def step_impl(context):
    def check(driver):
        texts = driver.execute_script("""
        var children = document.querySelectorAll(
          "div.semantic-field-details-card .sf-other-pos .sf-link");
        return Array.prototype.map.call(children, function (x) {
          return x.textContent;
        });
        """)

        return Result("FOO (None)" in texts, texts)

    result = Condition(context.util, check).wait()

    assert_true(result)

@then(r'the (?P<button>edit|"Create Field"|"Create"|"Submit") button '
      r'(?P<visible>does not show|shows) a spinner')
def step_impl(context, button, visible):
    selector = {
        '"Create Field"': ".btn.create-field",
        '"Create"': ".btn.submit",
        '"Submit"': ".btn.submit",
        'edit': '.btn.edit-field',
    }[button]

    cond = EC.invisibility_of_element_located if visible == "does not show" \
        else EC.visibility_of_element_located
    context.util.wait(cond((By.CSS_SELECTOR, selector + " .fa-spinner")))

@then(r'the (?P<button>edit|"Create Field"|"Create Child") button '
      r'(?P<visible>is|is not) visible')
def step_impl(context, button, visible):
    selector = {
        '"Create Field"': ".btn.create-field",
        '"Create Child"': ".btn.create-child",
        'edit': '.btn.edit-field',
    }[button]
    cond = EC.invisibility_of_element_located if visible == "is not" \
        else EC.visibility_of_element_located
    context.util.wait(cond((By.CSS_SELECTOR, selector)))
