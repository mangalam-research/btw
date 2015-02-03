# -*- coding: utf-8 -*-
# pylint: disable=E0611
import re
from StringIO import StringIO

import lxml.etree

from selenium.webdriver.support.wait import TimeoutException
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.by import By
from nose.tools import assert_equal, assert_true
from behave import step_matcher  # pylint: disable=E0611
from selenic.util import Result, Condition

from selenium_test import btw_util
from ..environment import server_write, server_read

step_matcher("re")


@then(r"^the table of contents is (?P<state>expandable|non-expandable)$")
def step_impl(context, state):
    driver = context.driver

    expandable = state == "expandable"

    selector = "#btw-article-affix" + \
               ".expandable" if expandable else ":not(.expandable)"

    els = driver.find_elements_by_css_selector(selector)

    assert_true(len(els) > 0, "the table of contents should "
                "{0} expandable".format("be" if expandable else "not be"))


@then(r"^the table of contents is (?P<state>expanded|collapsed)$")
def step_impl(context, state):
    util = context.util

    expanded = state == "expanded"

    selector = "#btw-article-affix" + \
               ".expanded" if expanded else ":not(.expanded)"

    try:
        util.find_element((By.CSS_SELECTOR, selector))
    except TimeoutException:
        assert_true(False, "the table of contents should be " + state)


@when(r"^the user clicks on the button to toggle the table of contents$")
def step_impl(context):
    driver = context.driver
    button = driver.find_element_by_css_selector(
        "#btw-article-affix>.expandable-heading .btn")

    button.click()


@when(r"^the user clicks a link in the table of contents$")
def step_impl(context):
    driver = context.driver
    link = driver.find_element_by_css_selector(
        "#btw-article-affix .nav a")

    link.click()


@then("^the senses and subsenses are properly numbered$")
def step_impl(context):
    util = context.util

    def cond(*_):
        try:
            btw_util.assert_senses_in_order(util, True)
            return True
        except AssertionError:
            return False

    try:
        util.wait(cond)
    except TimeoutException:
        # This is more useful than a timeout error.
        btw_util.assert_senses_in_order(util, True)

@given("^the view has finished rendering$")
def step_impl(context):
    driver = context.driver
    timeout_test = getattr(context, 'ajax_timeout_test', None)
    driver.execute_async_script("""
    var timeout_test = arguments[0];
    var done = arguments[1];
    function check() {
        if (!window.btw_viewer)
            setTimeout(check, 100);
        else {
            // We force the timeout to happen immediately.
            if (timeout_test)
                btw_viewer._load_timeout = 0;

            btw_viewer.whenCondition('done', function () {
                done();
            });
        }
    }
    check();
    """, timeout_test)

@given(ur"^that the next document will be loaded by a "
       ur"(?P<condition>failing|timing-out) AJAX call$")
def step_impl(context, condition):
    server_write(context, 'clearcache article_display\n')
    server_read(context)
    cmd = {
        "failing": "fail on ajax",
        "timing-out": "time out on ajax"
    }[condition]
    server_write(context, 'patch changerecord_details to {0}\n'.format(cmd))
    server_read(context)
    if condition == "timing-out":
        context.ajax_timeout_test = True

head_re = re.compile("\bhead\b")

def clean_tree(tree):
    # We want only the first class token.
    for el in tree.iter():
        class_ = el.get("class")
        if class_ is not None:
            el.set("class", class_.split(None, 1)[0] if len(class_) else "")

    # Remove all heads
    for head in [el for el in tree.iter() if el.get("class") == "head"]:
        head.getparent().remove(head)

def extract_text_from_el(el):
    return (el.text or '') + ''.join([extract_text_from_el(sub) for sub in el])

def extract_text(elements):
    return [extract_text_from_el(el) for el in elements]

@then("^the english renditions are reformatted in the correct structure$")
def step_impl(context):
    driver = context.driver
    html = driver.execute_script(ur"""
    return document.querySelector(
        ".btw\\:sense .btw\\:english-renditions").outerHTML;
    """)
    parser = lxml.etree.HTMLParser()
    tree = lxml.etree.parse(StringIO(html), parser)
    clean_tree(tree)

    term_list_terms = tree.xpath(
        "//div[@class='btw:english-term-list']"
        "//div[@class='btw:english-term']")
    semantic_field_collection_terms = tree.xpath(
        "//div[@class='btw:semantic-fields-collection']"
        "//div[@class='btw:english-term']")

    assert_equal(len(term_list_terms), 2)
    assert_equal(extract_text(term_list_terms),
                 extract_text(semantic_field_collection_terms))

@then(ur"^the (?P<what>antonyms|cognates|conceptual proximates) are "
      ur"reformatted in the correct structure$")
def step_impl(context, what):
    driver = context.driver

    class_ = r"btw\:" + what.replace(' ', '-')

    html = driver.execute_script(ur"""
    var class_ = arguments[0];
    return document.querySelector(
        ".btw\\:sense ." + class_).outerHTML;
    """, class_)
    parser = lxml.etree.HTMLParser()
    tree = lxml.etree.parse(StringIO(html), parser)
    clean_tree(tree)

    singular = what[:-1]

    term_list_class = "btw:" + singular.replace(' ', '-') + "-term-list"
    item_class = "btw:" + singular.replace(' ', '-') + "-term-item"

    term_list_terms = tree.xpath(
        "//div[@class='{0}']//div[@class='btw:term']".format(term_list_class))
    citations_terms = tree.xpath(
        "//div[@class='btw:citations-collection']"
        "//div[@class='btw:term']")

    assert_equal(len(term_list_terms), 2, "there should be two terms")
    assert_equal(extract_text(term_list_terms),
                 extract_text(citations_terms))

    term_list_labels = tree.xpath(
        "//div[@class='{0}']//div[@class='{1}']".format(term_list_class,
                                                        item_class))
    citations_labels = tree.xpath(
        "//div[@class='btw:citations-collection']"
        "//div[@class='{0}']".format(item_class))

    assert_equal(len(term_list_labels), 2)
    term_list_labels_text = extract_text(term_list_labels)
    assert_equal(term_list_labels_text,
                 extract_text(citations_labels))

    seq = 1
    for label in term_list_labels_text:
        assert_true(label.startswith(singular + " "),
                    "the label should start with " + singular +
                    " and a space")
        number = label[len(singular) + 1:]
        assert_true(number.startswith(str(seq) + ": "),
                    "the label should have a the sequence number " + str(seq))
        seq += 1

@then(ur'^the citation that starts with "(?P<citation>.*?)" is'
      ur'(?P<not_op> not)? in a collapsed section$')
def step_impl(context, citation, not_op=None):
    def check(driver):
        ret = driver.execute_script(btw_util.GET_CITATION_TEXT + ur"""
    var start = arguments[0];
    var not_op = arguments[1];
    var citations = document.getElementsByClassName("btw:cit");
    var cits = Array.prototype.filter.call(citations, function (cit) {
      var text = getCitationText(cit);
      return text.lastIndexOf(start, 0) === 0;
    });
    if (cits.length !== 1)
      return [false, "there should be exactly one citation"];
    var cit = cits[0];
    var parent = cit.parentNode;
    while (parent && parent.classList) {
      if (parent.classList.contains("collapse") &&
          !parent.classList.contains("in"))
        return [!not_op, "should not be in a collapsed section"];
      if (parent.classList.contains("collapsing"))
        return [false, "should not be in a section that is in the "+
                        "midst of collapsing or expanding"];
      parent = parent.parentNode;
    }
    return [not_op, "should be in a collapsed section"];
        """, citation, not_op is not None)
        return Result(ret[0], ret[1])

    result = Condition(context.util, check).wait()
    assert_true(result, result.payload)

@then(ur'^all collapsible sections are (?P<state>collapsed|expanded)$')
def step_impl(context, state):
    driver = context.driver

    driver.execute_script("""
    var collapsed_desired = arguments[0];
    var collapsing = document.getElementsByClassName("collapsing");
    if (collapsing.length)
      return [false, "no element should be collapsing"];
    var collapse = document.getElementsByClassName("collapse");
    var not_collapsed = Array.prototype.filter.call(collapse, function (x) {
        return x.classList.contains("in");
    });
    return collapsed_desired ?
        [not_collapsed.length === 0, "all sections should be collapsed"] :
        [not_collapsed.length !== collapse.length,
            "all sections should be expanded"];
    """, state == "collapsed")

@when(ur'^the user clicks the (?P<which>expand all|collapse all) button$')
def step_impl(context, which):
    util = context.util

    def check(driver):
        return driver.execute_script(ur"""
        var collapse = document.getElementById("toolbar-collapse");
        // We want to wait until it is collapsed.
        if (collapse.classList.contains("in") ||
            collapse.classList.contains("collapsing"))
           return undefined;
        return document.getElementById("toolbar-heading");
        """)

    toolbar = util.wait(check)

    toolbar.click()

    which = which.replace(" ", "-")

    # We use the .in class to make sure the toolbar is fully expanded
    # before clicking. On FF, not doing this *will* result in Selenium
    # considering the element clickable *but* will fail on the click
    # operation itself complaining that the element cannot be scrolled
    # into view!
    button = util.wait(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "#toolbar-collapse.in .btw-{0}-btn"
         .format(which))))
    button.click()

@then(ur'^the bibliography hyperlink with label "(?P<label>.*)" points '
      ur'to "(?P<url>.*)"$')
def step_impl(context, label, url):
    driver = context.driver

    driver.execute_script("""
    var label = arguments[0];
    var url = arguments[1];
    var as = document.querySelectorAll(".wed-document .ref>a");
    var a;
    for (var i = 0; (a = as[i]); ++i) {
        if (a.textContent.trim() === label)
            break;
    }
    if (!a)
        return [false, "there should be a link with label " + label];
    return [a.href === url, "the link should point to " + url];
    """)

@then(ur'^the (?P<what>first collapsible section) titled '
      ur'"(?P<title>.*?)" contains$')
@then(ur'^the (?P<what>cognate) "(?P<title>.*?)" has the semantic '
      ur'fields$')
@then(ur'^the (?P<what>article) has the semantic '
      ur'fields$')
def step_impl(context, what, title=None):
    driver = context.driver

    if what == "article":
        what = "first collapsible section"
        title = "all semantic fields"

    result = driver.execute_script(ur"""
    var what = arguments[0];
    var title = arguments[1];

    var panel_title;
    switch(what) {
    case "cognate":
        var cognate = Array.prototype.slice.call(
          document.querySelectorAll(
          ".btw\\:cognate-term-list>.btw\\:cognate-term-item>" +
          ".btw\\:term"))
         .filter(function (x) {
            return x.textContent.trim() === title;
        })[0];
        if (cognate)
            panel_title = cognate.parentNode.nextElementSibling
                .getElementsByClassName("panel-title")[0];
        break;
    case "first collapsible section":
        panel_title = Array.prototype.slice.call(
          document.getElementsByClassName("panel-title"))
          .filter(function (x) {
            return x.textContent.trim() === title;
        })[0];
        break;
    default:
        return [false, "invalid value for 'what'"];
    }
    if (!panel_title)
        return [false, "there should be a collapsible section"];

    var panel = panel_title.parentNode.parentNode;
    var collapse = panel.getElementsByClassName("collapse")[0];
    return [collapse.textContent.trim(), ""];
    """, what, title)
    assert_true(result[0], result[1])
    assert_equal(result[0], context.text.strip(),
                 "the semantic fields should be equal")

@then(ur'^the navigation link "(?P<text>.*?)" points to the fourth subsense$')
def step_impl(context, text):
    driver = context.driver

    result = driver.execute_script("""
    var text = arguments[0];
    var link = Array.prototype.filter.call(
        document.querySelectorAll("#btw-article-affix a"), function (x) {
        return x.textContent === text;
    })[0];
    if (!link)
        return [false, "there should be a link"];

    var subsense = document.getElementsByClassName("btw:subsense")[3];
    if (!subsense)
        return [false, "there should be a fourth subsense"];
    return [link.getAttribute("href").slice(1) === subsense.id,
        "the link should point to the right subsense (" +
        link.getAttribute("href").slice(1) + " !== " + subsense.id + ")"];
    """, text)

    assert_true(result[0], result[1])

@then(ur"^the (?P<what>loading|time out) error message is visible$")
def step_impl(context, what):
    util = context.util

    alert = util.wait(
        EC.visibility_of_element_located((By.CSS_SELECTOR,
                                          ".alert.alert-danger")))
    msg = {
        "loading": "Cannot load the document.",
        "time out": "The server has not sent the required data within "
        "a reasonable time frame."
    }[what]
    assert_equal(alert.text.strip(), msg)
