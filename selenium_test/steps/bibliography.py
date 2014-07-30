from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import wedutil
from behave import step_matcher

step_matcher("re")


WHICH_TO_TITLE = {
    "with": "Title 3",
    "without": "Title 1"
}


@when(ur'^the user adds a reference to an item$')
@when(ur'^the user adds a reference to an item( to the first example)?$')
@when(ur'^the user adds a reference to an item (?P<which>with|without) a '
      ur'reference title$')
def step_impl(context, which=None):
    driver = context.driver
    util = context.util
    seek_etymology = True

    if which == " to the first example":
        which = "with"
        seek_etymology = False

    if which is None:
        which = "with"

    if seek_etymology:
        # Obtain the first placeholder after "[etymology]".
        ph = driver.execute_script("""
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

        wedutil.click_until_caret_in(util, ph)
        util.ctrl_equivalent_x("/")
    else:
        # By doing it this way, we avoid being thrown off by possible
        # error markers that could show in front of it.
        driver.execute_script(ur"""
        var $text = jQuery(".btw\\:cit").contents().filter(function () {
            return this.nodeType === Node.TEXT_NODE;
        });
        var text_node = $text[0];
        wed_editor.setGUICaret(text_node, 0);
        """)

        util.ctrl_equivalent_x("/")

    context.execute_steps(u"""
    When the user clicks the context menu option "Insert a new \
bibliographical reference"
    """)

    def cond(*_):
        ret = driver.execute_script("""
        var title = arguments[0];
        var with_ = arguments[1];

        var qs = document.querySelector.bind(document);
        var $row = jQuery("#bibliography-table>tbody>tr:contains('" + title +
                          "')");
        if (with_) {
            // Open the next row if needed.
            var $next = $row.next("tr");
            if (!$next[0] || $next.is(".odd, .even"))
                $row.find(".open-close-button").click();
            // We can't reuse $next here.
            $row = $row.next("tr").find("table>tbody>tr").first();
        }
        return [$row[0], qs(".modal.in .btn-primary")];
        """, WHICH_TO_TITLE[which], which == "with")
        return ret if ret[0] and ret[1] else None

    row, button = util.wait(cond)

    ActionChains(driver) \
        .click(row) \
        .click(button) \
        .perform()


@then(ur'^a new reference is inserted$')
@then(ur'^the new reference contains the reference title\.?$')
def step_impl(context):
    util = context.util
    driver = context.driver

    def cond(*_):
        text = driver.execute_script("""
        return jQuery(".ref ._text").text();
        """)

        return text == "Foo"

    util.wait(cond)


@then(ur"^the new reference contains the first author's last name and "
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


@when(ur"^the user adds custom text to the (?P<what>new|first) reference$")
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


@then(ur"^the new reference contains a placeholder\.?$")
def step_impl(context):
    util = context.util

    util.find_element((By.CSS_SELECTOR, ".ref ._placeholder"))


@when(ur"^the user brings up the context menu$")
def step_impl(context):
    util = context.util

    util.ctrl_equivalent_x("/")


@given(ur"^that the user is on the page for performing a general "
       ur"bibliographical search")
def step_impl(context):
    driver = context.driver
    config = context.selenic_config
    driver.get(config.SERVER + "/bibliography/search/")


@when(ur"^the user deletes a reference")
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


@then(ur"^the element that contained the reference no longer contains the "
      ur"space that was added for the reference$")
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
