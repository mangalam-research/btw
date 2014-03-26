from selenium.webdriver.common.action_chains import ActionChains
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.by import By

from behave import step_matcher

step_matcher("re")


WHICH_TO_KEY = {
    "with": 3,
    "without": 1
}


@when(ur'^the user adds a reference to an item (?P<which>with|without) a '
      ur'reference title')
def step_impl(context, which):
    driver = context.driver
    util = context.util
    # Obtain the first placeholder after "[etymology]".
    ph = driver.execute_script("""
    var $ = jQuery;
    var etym = $(".head:contains('[etymology]')")[0];
    var $phs = $("._placeholder");
    var found;
    for(var i = 0, limit = $phs.length; !found && i < limit; ++i) {
        var ph = $phs[i];
        if (ph.compareDocumentPosition(etym) & 2)
            found = ph;
    }
    return found;
    """)

    ActionChains(driver) \
        .context_click(ph) \
        .perform()

    context.execute_steps(u"""
    When the user clicks the context menu option "Insert a new \
bibliographical reference."
    """)

    def cond(*_):
        ret = driver.execute_script("""
        var qs = document.querySelector.bind(document);
        return [qs("#bibliography-table>tbody>tr[data-item-key='{0}']"),
                qs(".modal.in .btn-primary")];
        """.format(WHICH_TO_KEY[which]))
        return ret if ret[0] and ret[1] else None

    row, button = util.wait(cond)

    ActionChains(driver) \
        .click(row) \
        .click(button) \
        .perform()


@then(ur'^the new reference contains the reference title')
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
