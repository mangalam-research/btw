# -*- coding: utf-8 -*-
# pylint: disable=E0611
import re

import lxml.etree

from selenium.webdriver.support.wait import TimeoutException
from nose.tools import assert_equal, assert_true
from behave import step_matcher  # pylint: disable=E0611

from selenium_test import btw_util

step_matcher("re")


@then("^the senses and subsenses are properly numbered$")
def step_impl(context):
    util = context.util

    def cond(*_):
        try:
            btw_util.assert_senses_in_order(util)
            return True
        except AssertionError:
            return False

    try:
        util.wait(cond)
    except TimeoutException:
        # This is more useful than a timeout error.
        btw_util.assert_senses_in_order(util)

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
