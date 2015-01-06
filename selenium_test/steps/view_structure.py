# -*- coding: utf-8 -*-
# pylint: disable=E0611
import re

import lxml.etree

from selenium.webdriver.support.wait import TimeoutException
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.by import By
from nose.tools import assert_equal, assert_true
from behave import step_matcher  # pylint: disable=E0611
from selenic.util import Result, Condition

from selenium_test import btw_util

step_matcher("re")


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
    driver.execute_async_script("""
    var done = arguments[0];
    function check() {
        if (!window.btw_viewer)
            setTimeout(check, 100);
        else
            btw_viewer.whenCondition('done', done);
    }
    check();
    """)

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
    tree = lxml.etree.fromstring(html)
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
    tree = lxml.etree.fromstring(html)
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
