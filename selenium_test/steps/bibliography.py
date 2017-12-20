from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from nose.tools import assert_equal

import wedutil
from behave import step_matcher

step_matcher("re")


WHICH_TO_TITLE = {
    "with": "Title 3",
    "without": "Title 1"
}

def __get_first_ph_in_etymology(driver):
    return driver.execute_script("""
    var $ = jQuery;
    var etym = $(".head:contains('[etymology]')")[0];
    var $phs = $("._placeholder");
    var found;
    for(var i = 0, limit = $phs.length; !found && i < limit; ++i) {
        var ph = $phs[i];
        if (ph.compareDocumentPosition(etym) & 2) {
            found = ph;
            found.scrollIntoView();
        }
    }

    return found;
    """)


@when(ur'the user adds a reference to an item'
      ur'(?P<which> to the (?:first|second) example)?')
@when(ur'the user adds a reference to an item (?P<which>with|without) a '
      ur'reference title')
def step_impl(context, which=None):
    driver = context.driver
    util = context.util

    order = None
    if which == " to the first example":
        order = 0
        which = "with"
    elif which == " to the second example":
        order = 1
        which = "with"
    elif which is None:
        which = "with"

    if order is None:
        # Obtain the first placeholder after "[etymology]".
        ph = __get_first_ph_in_etymology(driver)

        wedutil.click_until_caret_in(util, ph)
        util.ctrl_equivalent_x("/")
    else:
        # By doing it this way, we avoid being thrown off by possible
        # error markers that could show in front of it.
        driver.execute_script(ur"""
        var order = arguments[0];
        var cits = document.getElementsByClassName("btw:cit");
        var node = cits[order];
        node.scrollIntoView();
        var data_node = jQuery.data(node, "wed_mirror_node");
        if (data_node.childNodes.length) {
            data_node = data_node.firstChild;
        }
        wed_editor.caretManager.setCaret(data_node, 0);
        """, order)

        util.ctrl_equivalent_x("/")

    context.execute_steps(u"""
    When the user clicks the context menu option "Insert a new \
bibliographical reference"
    """)

    title = WHICH_TO_TITLE[which]
    typeahead = util.find_element((By.CSS_SELECTOR,
                                   ".wed-typeahead-popup .tt-input"))
    typeahead.send_keys(title)

    def cond(*_):
        ret = driver.execute_script("""
        var title = arguments[0];
        var $suggestion = jQuery(".wed-typeahead-popup " +
                                 ".tt-suggestion:contains('" + title + "')");
        return $suggestion[0];
        """, WHICH_TO_TITLE[which] if which != "with" else "Foo --- ")
        return ret

    suggestion = util.wait(cond)

    ActionChains(driver) \
        .click(suggestion) \
        .perform()


@when(ur"the user replaces a selection with reference to an item with "
      ur"a reference title")
def step_impl(context):
    driver = context.driver
    util = context.util

    # Obtain the first placeholder after "[etymology]".
    ph = __get_first_ph_in_etymology(driver)

    wedutil.click_until_caret_in(util, ph)
    ActionChains(driver) \
        .send_keys("Foo") \
        .perform()
    wedutil.select_text_of_element_directly(util, r".btw\:etymology>.p")

    util.ctrl_equivalent_x("/")

    context.execute_steps(u"""
    When the user clicks the context menu option "Replace the selection \
with a bibliographical reference"
    """)

    util.find_element((By.CSS_SELECTOR,
                       ".wed-typeahead-popup .tt-input"))

    # We do this rather than send directly to the input element
    # because it should have been focussed automatically.

    ActionChains(driver) \
        .send_keys(Keys.ENTER) \
        .perform()

@then(ur'a new reference is inserted')
@then(ur'the new reference contains the reference title\.?')
def step_impl(context):
    util = context.util
    driver = context.driver

    def cond(*_):
        text = driver.execute_script("""
        return jQuery(".ref ._text").text();
        """)

        return text == "Foo"

    util.wait(cond)


@then(ur"the new reference contains the first author's last name and "
      ur"the date\.?")
def step_impl(context):
    util = context.util
    driver = context.driver

    def cond(*_):
        text = driver.execute_script("""
        return jQuery(".ref ._text").text();
        """)

        return text == "Abelard (Name 1 for Title 1), Date 1"

    util.wait(cond)


@when(ur"the user adds custom text to the (?P<what>new|first) reference")
def step_impl(context, what):
    util = context.util
    driver = context.driver

    if what == "first":
        driver.find_element_by_css_selector(".ref").click()
    elif what == "new":
        # Nothing to do. The caret should already be in the reference.
        pass
    else:
        raise Exception("unexpected what value: " + what)

    util.ctrl_equivalent_x("/")

    context.execute_steps(u"""
    When the user clicks the context menu option "Add custom text \
to reference"
    """)


@then(ur"the new reference contains a placeholder\.?")
def step_impl(context):
    util = context.util

    util.find_element((By.CSS_SELECTOR, ".ref ._placeholder"))


@when(ur"the user brings up the context menu")
def step_impl(context):
    util = context.util

    util.ctrl_equivalent_x("/")


@given(ur"that the user is on the page for performing a general "
       ur"bibliographical search")
def step_impl(context):
    driver = context.driver
    driver.get(context.builder.SERVER + "/bibliography/search/")


@when(ur"the user deletes a reference")
def step_impl(context):
    util = context.util
    driver = context.driver

    el, context.deleted_reference_parent = \
        driver.execute_script(u"""
        var el = document.querySelector(".ref");
        return [el, el.parentNode];
        """)
    # el.click()

    util.ctrl_equivalent_x("/")

    context.execute_steps(u"""
    When the user clicks the context menu option "Delete ref"
    """)


@then(ur"the element that contained the reference no longer contains the "
      ur"space that was added for the reference")
def step_impl(context):
    util = context.util
    parent = context.deleted_reference_parent

    def cond(driver):
        ret = driver.execute_script("""
        var $parent = jQuery(arguments[0]);
        if ($parent.children(".ref").length)
            return [false, "contains a reference"];
        if ($parent.children("._ref_space").length)
            return [false, "contains the space after the reference"];
        return [true, 0];
        """, parent)

        return ret[0]

    util.wait(cond)

@when(ur"the user searches for a bibliographical item that does not exist")
def step_impl(context):
    driver = context.driver
    util = context.util

    # Obtain the first placeholder after "[etymology]".
    ph = __get_first_ph_in_etymology(driver)

    wedutil.click_until_caret_in(util, ph)
    util.ctrl_equivalent_x("/")

    context.execute_steps(u"""
    When the user clicks the context menu option "Insert a new \
bibliographical reference"
    """)

    util.find_element((By.CSS_SELECTOR,
                       ".wed-typeahead-popup .tt-input"))

    # We do this rather than send directly to the input element
    # because it should have been focussed automatically.

    ActionChains(driver) \
        .send_keys("FLFLFL") \
        .perform()


@then(ur"the bibliographical reference typeahead shows that there is no "
      ur"match")
def step_impl(context):
    driver = context.driver
    util = context.util

    text = driver.execute_script("""
    var dropdown = document.querySelector(
        ".wed-typeahead-popup .tt-dropdown-menu");
    return dropdown.textContent.trim();
    """)
    assert_equal(text, "Cited does not contain a match."
                 "Zotero does not contain a match.")
