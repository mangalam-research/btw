from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true

from selenium_test import btw_util

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


@then(ur'^the hyperlink with label "(?P<label>.*?)" points '
      ur'to "(?P<term>.*?)"\.?$')
def step_impl(context, label, term):
    def cond(driver):
        ret = driver.execute_script(ur"""
        var label = arguments[0];
        var term = arguments[1];
        var $ = jQuery;

        var $link = $(".wed-document a[href^='#BTW-S.']").filter(
            function (x) { return $(this).text() === label; });
        if (!$link[0])
            return [false, "there should be a link"];

        var $target = $($link.attr("href").replace(/\./g, "\\."));
        if (!$target[0])
            return [false, "there should be a target"];

        var $data_target = $($target.data("wed_mirror_node"));
        if (!$data_target[0])
            return [false, "there should be a data target"];

        var actual_term;
        if ($data_target.is(".btw\\:sense"))
            actual_term = $data_target.find(".btw\\:english-term").text();
        else
            actual_term = $data_target.find(".btw\\:explanation").text();

        return [actual_term === term,
                actual_term + " should match " + term];
        """, label, term)

        return ret[0]

    context.util.wait(cond)
