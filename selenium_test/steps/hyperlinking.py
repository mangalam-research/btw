from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true

from selenium_test import btw_util
import wedutil

step_matcher('re')


@when(ur"^the user brings up a context menu in the text in the definition")
def step_impl(context):
    driver = context.driver

    p = driver.find_element_by_css_selector(".p")
    ActionChains(driver) \
        .context_click(p) \
        .perform()


@then(ur"the hyperlinkig modal dialog comes up\.?")
def step_impl(context):
    header = context.util.find_element((By.CSS_SELECTOR,
                                        ".modal.in .modal-header h3"))
    assert_equal(header.text, "Insert hyperlink to sense")


@then(ur"the hyperlinking choices are")
def step_impl(context):
    driver = context.driver

    choices = driver.execute_script("""
    return jQuery(".modal.in .modal-body input").next("span").toArray();
    """)

    for (row, choice) in zip(context.table, choices):
        assert_equal(row['choice'], choice.text)


@when(ur'^the user clicks the hyperlinking choice for "(?P<what>.*?)"$')
def step_impl(context, what):
    driver = context.driver
    context.hyperlinks_before_insertion = \
        btw_util.get_sense_hyperlinks(context.util)

    choice = driver.execute_script(ur"""
    var choice = arguments[0];

    var re = new RegExp('\\b' + choice + '\\b');
    return jQuery(".modal.in .modal-body input").filter(function () {
        return re.test(jQuery(this).next('span').text());
    })[0];
    """, what)

    choice.click()
    driver.find_element_by_css_selector(".modal.in .btn-primary").click()


@then(ur'^a new hyperlink with the label "(?P<what>.*?)" is inserted\.?$')
def step_impl(context, what):
    links = btw_util.get_sense_hyperlinks(context.util)

    assert_equal(len(links), len(context.hyperlinks_before_insertion) + 1)

    for x in context.hyperlinks_before_insertion:
        links.remove(x)

    assert_equal(links[0]["text"], what)


@then(ur'^there are hyperlinks with labels "\[a\]" and "\[a2\]"\.?$')
def step_impl(context):
    links = btw_util.get_sense_hyperlinks(context.util)

    assert_equal(len(links), 2)

    expect = ["[a]", "[a2]"]

    for l in links:
        expect.remove(l["text"])

    assert_equal(expect, [], "all expected links should have been found")

__LINK_RE1 = \
    (ur'^the (?P<example>example) hyperlink with label "(?P<label>.*?)" '
     ur'points to the (?P<term>first) example\.?$')
__LINK_RE2 = \
    (ur'^the (?P<example>)hyperlink with label "(?P<label>.*?)" points '
     ur'to "(?P<term>.*?)"\.?$')


@given(__LINK_RE1)
@given(__LINK_RE2)
@then(__LINK_RE1)
@then(__LINK_RE2)
def step_impl(context, example, label, term):

    id_selector = "#BTW-E." if example else "#BTW-S."

    def cond(driver):
        ret = driver.execute_script(ur"""
        var label = arguments[0];
        var term = arguments[1];
        var id_selector = arguments[2];
        var $ = jQuery;

        var $link = $(".wed-document a[href^='" + id_selector + "']").filter(
            function (x) { return $(this).text() === label; });
        if (!$link[0])
            return [false, "there should be a link"];

        var $target = $($link.attr("href").replace(/\./g, "\\."));
        if (!$target[0])
            return [false, "there should be a target"];

        var $data_target = $($target.data("wed_mirror_node"));
        if (!$data_target[0])
            return [false, "there should be a data target"];

        var test = false;
        var actual_term, desc;
        if ($data_target.is(".btw\\:sense")) {
            actual_term = $data_target.find(".btw\\:english-term").text();
            test = term === actual_term;
            desc = actual_term + " should match " + term;
        }
        else if ($data_target.is(".btw\\:subsense")) {
            actual_term = $data_target.children(".btw\\:explanation").text();
            test = term === actual_term;
            desc = actual_term + " should match " + term;
        }
        else if ($data_target.is(".btw\\:example, .btw\\:example-explained")) {
            test = wed_editor.$data_root.find(
                ".btw\\:example, .btw\\:example-explained").first()[0]
                === $data_target[0];
            desc = "link should point to " + term + " example";
        }
        else
            return [false, "unexpected target"];

        return [test, desc];
        """, label, term, id_selector)

        return ret[0]

    context.util.wait(cond)


@then(ur'^the sense hyperlink with label "(?P<label>.*?)" has a tooltip '
      ur'that says "(?P<tooltip>.*)"')
def step_impl(context, label, tooltip):

    id_selector = "#BTW-S."

    def cond(driver):
        ret = driver.execute_script(ur"""
        var label = arguments[0];
        var tooltip = arguments[1];
        var id_selector = arguments[2];
        var $ = jQuery;

        var $link = $(".wed-document a[href^='" + id_selector + "']").filter(
            function (x) { return $(this).text() === label; });
        if (!$link[0])
            return [false, "there should be a link"];

        var tt = $link.parent().data("bs.tooltip");
        var title = $(tt.getTitle()).text();
        return [title === tooltip,
                "tooltip should have text: '" + tooltip + "' but has '" +
        title + "'"];
        """, label, tooltip, id_selector)

        return ret[0]

    context.util.wait(cond)

__CHOICE_TO_SELECTOR = {
    u"in the last btw:citations": r".btw\:citations>._placeholder",
    u"on the start label of the first example":
    r".__start_label._btw\:example_label, "
    r".__start_label._btw\:example-explained_label"
}


@when(ur"^the user brings up a context menu "
      ur"(?P<choice>in the last btw:citations|on the start label of the "
      ur"first example)")
def step_impl(context, choice):
    driver = context.driver
    util = context.util

    selector = __CHOICE_TO_SELECTOR[choice]

    el = driver.find_elements_by_css_selector(selector)

    index = 0
    if choice.find("last") != -1:
        index = -1

    # Earlier code would use context_click but that was fragile due to
    # the asynchronous nature of the editor. In effect, Selenium could
    # "miss" the target element if decorations were added while it was
    # trying to click, and the click would end up in the wrong place.
    while True:
        ActionChains(driver) \
            .click(el[index]) \
            .perform()

        if wedutil.is_caret_in(util, el[index]):
            util.ctrl_equivalent_x("/")
            break


@when(ur"^the user deletes the first example")
def step_impl(context):
    util = context.util
    driver = context.driver

    el = driver.find_element_by_css_selector(
        r".__start_label._btw\:example_label, "
        r".__start_label._btw\:example-explained_label")

    wedutil.click_until_caret_in(util, el)
    context.execute_steps(u"""
    When the user brings up the context menu
    And the user clicks the context menu option "Delete this element"
    """)


@then(ur"^there are no example hyperlinks")
def step_impl(context):

    id_selector = "#BTW-E."

    def cond(driver):
        ret = driver.execute_script(ur"""
        var $ = jQuery;
        var id_selector = arguments[0];
        var $links = $(".wed-document a[href^='" + id_selector + "']");
        return !$links[0];
        """, id_selector)

        return ret

    context.util.wait(cond)
