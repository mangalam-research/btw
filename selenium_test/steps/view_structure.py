# -*- coding: utf-8 -*-
# pylint: disable=E0611
import re
import os
import datetime
from io import StringIO

import lxml.etree
import requests

from selenium.webdriver.support.wait import TimeoutException
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from nose.tools import assert_equal, assert_true, assert_false
from behave import step_matcher  # pylint: disable=E0611
from selenic.util import Result, Condition

from lexicography.tests import funcs
from selenium_test import btw_util

step_matcher("re")


@then(r"the table of contents is (?P<state>expandable|non-expandable)")
def step_impl(context, state):
    util = context.util

    expandable = state == "expandable"

    selector = "#btw-article-affix" + \
               ".expandable" if expandable else ":not(.expandable)"

    els = util.find_elements((By.CSS_SELECTOR, selector))

    assert_true(len(els) > 0, "the table of contents should "
                "{0} expandable".format("be" if expandable else "not be"))


@then(r"the table of contents is (?P<state>expanded|collapsed)")
def step_impl(context, state):
    util = context.util

    expanded = state == "expanded"

    selector = "#btw-article-affix" + \
               ".expanded" if expanded else ":not(.expanded)"

    try:
        util.find_element((By.CSS_SELECTOR, selector))
    except TimeoutException:
        assert_true(False, "the table of contents should be " + state)


@when(r"the user clicks on the button to toggle the table of contents")
def step_impl(context):
    driver = context.driver
    button = driver.find_element_by_css_selector(
        "#btw-article-affix>.expandable-heading .btn")

    button.click()


@when(r"the user clicks a link in the table of contents")
def step_impl(context):
    driver = context.driver
    link = driver.find_element_by_css_selector(
        "#btw-article-affix .nav a")

    link.click()


@then("the senses and subsenses are properly numbered")
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

@given("the view has finished rendering")
def step_impl(context):
    driver = context.driver
    timeout_test = getattr(context, 'ajax_timeout_test', None)

    # This step does not care whether the rendering was successful or
    # not.
    driver.execute_async_script("""
    var timeout_test = arguments[0];
    var done = arguments[1];
    function check() {
        if (!window.btw_viewer) {
            setTimeout(check, 100);
        }
        else {
            // We force the timeout to happen immediately.
            if (timeout_test) {
                btw_viewer.loadTimeout = 0;
            }

            btw_viewer.done.then(function success() {
              done();
            }, function failure(err) {
              done();
            });
        }
    }
    check();
    """, timeout_test)


@given(r"that the next document will be loaded by a "
       r"(?P<condition>failing|timing-out) AJAX call")
def step_impl(context, condition):
    context.server.write('clearcache article_display\n')
    context.server.read()
    cmd = {
        "failing": "fail on ajax",
        "timing-out": "time out on ajax"
    }[condition]
    context.server.write('patch changerecord_details to {0}\n'.format(cmd))
    context.server.read()
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

@then("the english renditions are reformatted in the correct structure")
def step_impl(context):
    driver = context.driver
    html = driver.execute_script(r"""
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

@then(r"the (?P<what>antonyms|cognates|conceptual proximates) are "
      r"reformatted in the correct structure")
def step_impl(context, what):
    driver = context.driver

    class_ = r"btw\:" + what.replace(' ', '-')

    html = driver.execute_script(r"""
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

@then(r'the citation that starts with "(?P<citation>.*?)" is'
      r'(?P<not_op> not)? in a collapsed section')
def step_impl(context, citation, not_op=None):
    def check(driver):
        ret = driver.execute_script(btw_util.GET_CITATION_TEXT + r"""
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
          !parent.classList.contains("show"))
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

@then(r'all collapsible sections are (?P<state>collapsed|expanded)')
def step_impl(context, state):
    driver = context.driver

    driver.execute_script("""
    var collapsed_desired = arguments[0];
    var collapsing = btw_viewer.root.getElementsByClassName("collapsing");
    if (collapsing.length)
      return [false, "no element should be collapsing"];
    var collapse = btw_viewer.root.getElementsByClassName("collapse");
    var not_collapsed = Array.prototype.filter.call(collapse, function (x) {
        return x.classList.contains("show");
    });
    return collapsed_desired ?
        [not_collapsed.length === 0, "all sections should be collapsed"] :
        [not_collapsed.length !== collapse.length,
            "all sections should be expanded"];
    """, state == "collapsed")

@when(r'the user clicks the (?P<which>expand all|collapse all) button')
def step_impl(context, which):
    util = context.util

    def check(driver):
        return driver.execute_script(r"""
        var collapse = document.getElementById("toolbar-collapse");
        // We want to wait until it is collapsed.
        if (collapse.classList.contains("show") ||
            collapse.classList.contains("collapsing"))
           return undefined;
        return document.getElementById("toolbar-heading");
        """)

    toolbar = util.wait(check)

    toolbar.click()

    which = which.replace(" ", "-")

    # We use the .show class to make sure the toolbar is fully expanded
    # before clicking. On FF, not doing this *will* result in Selenium
    # considering the element clickable *but* will fail on the click
    # operation itself complaining that the element cannot be scrolled
    # into view!
    button = util.wait(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "#toolbar-collapse.show .btw-{0}-btn"
         .format(which))))
    button.click()

@then(r'the bibliography hyperlink with label "(?P<label>.*)" points '
      r'to "(?P<url>.*)"')
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

@then(r'the (?P<what>first collapsible section) titled '
      r'"(?P<title>.*?)" contains')
@then(r'the (?P<what>cognate) "(?P<title>.*?)" has the semantic fields')
@then(r'the (?P<what>article) has the semantic fields')
def step_impl(context, what, title=None):
    driver = context.driver

    if what == "article":
        what = "first collapsible section"
        title = "all semantic fields"

    result = driver.execute_script(r"""
    var what = arguments[0];
    var title = arguments[1];

    var card_title;
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
            card_title = cognate.parentNode.nextElementSibling
                .getElementsByClassName("card-header")[0];
        break;
    case "first collapsible section":
        card_title = Array.prototype.slice.call(
          document.getElementsByClassName("card-header"))
          .filter(function (x) {
            return x.textContent.trim() === title;
        })[0];
        break;
    default:
        return [false, "invalid value for 'what'"];
    }
    if (!card_title)
        return [false, "there should be a collapsible section"];

    var card = card_title.closest(".card");
    var collapse = card.getElementsByClassName("collapse")[0];
    var text = Array.prototype.reduce.call(
      collapse.getElementsByClassName("btw:sf"),
      function (prev, current) {
        return prev + " " + current.textContent.trim().replace(/\s+/g, " ");
    }, "");

    return [text.trim(), ""];
    """, what, title)
    assert_true(result[0], result[1])
    assert_equal(result[0], context.text.strip(),
                 "the semantic fields should be equal")

@then(r'the table of contents contains')
def step_impl(context):
    driver = context.driver
    text = context.text.strip()
    expected_nav = {
        "text": "",
        "children": []
    }
    stack = [expected_nav]
    for line in text.split("\n"):
        parts = line.split(">")
        level = len(parts) - 1
        item = {
            "text": parts[-1],
            "children": []
        }

        stack_level = len(stack) - 2

        # If the level of this item is lower than the level of
        # item on the top of the stack, pop so that we can add this
        # item to the right place.
        if level < stack_level:
            del stack[0:stack_level - level]
            stack_level = level

        if level == stack_level:
            # The item is a child of the one which is at position 1 in
            # the stack.
            stack[1]["children"].append(item)
            stack[0] = item
        elif level > stack_level:
            # The item is a child of the one at the top of the stack.
            stack[0]["children"].append(item)
            stack[0:0] = [item]

    # Drop the top level element as it is useless.
    expected_nav = expected_nav["children"]

    nav = driver.execute_script("""
    var nav = document.querySelector("#btw-article-affix ul.nav");
    function grab(li) {
        var a = li.querySelector("a");
        var children = [];
        var ret = { text: a ? a.textContent : "", children: children };
        var lis = Array.prototype.filter.call(li.querySelectorAll("ul>li"),
           function (el) { return el.parentNode.parentNode === li; });

        for (var i = 0, child; (child = lis[i]); ++i)
            children.push(grab(child));
        return ret;
    }
    var ret = grab(nav.parentNode);

    // The algorithm above returns an incorrect result for the top
    // level element, and we actually do not need it. So...
    return ret.children;
    """)
    assert_equal(nav, expected_nav)

@then(r'the navigation link "(?P<text>.*?)" points to the fourth subsense')
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

@then(r"the (?P<what>loading|time out) error message is visible")
def step_impl(context, what):
    util = context.util

    if what == "loading":
        # We don't care what the modal contains. We just want it to be up.
        util.wait(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "div.modal.btw-fatal-modal")))
    elif what == "timeout":
        alert = util.wait(
            EC.visibility_of_element_located((By.CSS_SELECTOR,
                                              ".alert.alert-danger")))
        msg = ("The server has not sent the required data within "
               "a reasonable time frame.")
        assert_equal(alert.text.strip(), msg)


@then(r"there is (?P<exists>an|no) alert indicating the document "
      r"is unpublished")
def step_impl(context, exists):
    util = context.util

    def check(driver):
        text = driver.execute_script("""
        var el = document.querySelector(".alert.alert-danger");
        return el && el.textContent;
        """)

        if exists == "an":
            return text.strip().startswith(
                "You are looking at an unpublished version of the "
                "article.")
        else:
            return text is None

    util.wait(check)


@then(r'there is a hyperlink with label "(?P<label>.*?)" that points to the '
      r'article for the same lemma')
def step_impl(context, label):
    driver = context.driver

    r = requests.get(context.builder.SERVER +
                     "/en-us/lexicography/search-table/",
                     params={
                         "length": -1,
                         "search[value]": label,
                         "lemmata_only": "true",
                         "publication_status": "both",
                     },
                     cookies={
                         "sessionid": context.session_id
                     } if context.session_id else None)
    hits = funcs.parse_search_results(r.text)
    url = hits[label]["hits"][0]["view_url"]

    context.server.write(
        "changerecord link to entry link {0}\n".format(url))
    entry_url = context.server.read()

    links = driver.execute_script("""
    var url = arguments[0];
    var links = btw_viewer.root.querySelectorAll("a[href='" + url + "']");
    var ret = [];
    for (var i = 0, link; (link = links[i]); ++i) {
        ret.push(link.textContent);
    }
    return ret;
    """, entry_url)

    assert_true(len(links) > 0, "there should be a link")

    for link in links:
        assert_equal(link, label, "the link label should be " + label)


@when(r'the user clicks in the access date field')
def step_impl(context):
    field = context.util.find_element((By.ID, "access-date"))
    field.click()


@then(r'there is a date picker visible')
def step_impl(context):
    picker = context.util.find_element((By.CLASS_NAME, "datepicker"))
    assert_true(picker.is_displayed())


@when(r'the user changes the date')
def step_impl(context):
    util = context.util
    field = util.find_element((By.ID, "access-date"))

    initial = field.get_attribute("value")

    prev = util.find_element((By.CSS_SELECTOR, ".datepicker .prev"))
    prev.click()
    day = util.find_element((By.CSS_SELECTOR, ".datepicker .day"))
    day.click()

    util.wait(lambda *_: field.get_attribute("value") != initial)


def is_in_article(feature):
    name = os.path.splitext(os.path.basename(feature.filename))[0]
    return name in ("view", "view_structure")

@then(r'the citations show the date from the access date field')
def step_impl(context):
    in_article = is_in_article(context.feature)

    accessed_selector = "#cite-modal .accessed" if in_article else \
                        ".cite-form .accessed"

    util = context.util
    driver = context.driver

    field = util.find_element((By.ID, "access-date"))

    value = util.wait(lambda *_: field.get_attribute("value"))

    # We use this rather than strftime so that we can have a day
    # number without a leading zero. On the internet there are those
    # who suggest using %-d but with strftime it this does not seem to
    # be portable.
    formatted = "{0:%B} {0.day} {0:%Y}".format(
        datetime.datetime.strptime(value, "%Y-%m-%d"))

    accessed_spans = driver.execute_script("""
    var selector = arguments[0];
    return Array.prototype.map.call(
        document.querySelectorAll(selector),
        function (x) {
            return x.textContent;
    });
    """, accessed_selector)
    assert_true(len(accessed_spans) > 0,
                "there should be some spans")
    for span in accessed_spans:
        assert_equal(span, formatted)


def get_permalinks(driver):
    # We grab the values of the links in the links modal. This allows
    # finding the URL values we need without having to query the
    # server. The correctness of these values is tested in a nose
    # unittest that tests the view directly.
    links = driver.execute_script("""
    return Array.prototype.map.call(
        document.querySelectorAll("#link-modal .modal-body a"),
        function (x) {
            return x.href;
    });
    """)
    return {"non-version-specific": links[0],
            "version-specific": links[1]}

@then(r'the MODS data has the correct (?P<what>access date field|url)')
def step_impl(context, what):
    in_article = is_in_article(context.feature)

    form_selector = '#cite-modal .modal-body form' if in_article else \
                    '.cite-form form'

    driver = context.driver
    util = context.util

    data = driver.execute_async_script("""
    var selector = arguments[0];
    var done = arguments[1];
    var $ = jQuery;
    var $form = $(selector);
    $.ajax({
        url: $form[0].action,
        data: $form.serialize(),
        dataType: "text"
    }).done(done).fail(function (jqXHR, textStatus, errorThrown) {
      done([textStatus]);
    });
    """, form_selector)
    assert_false(isinstance(data, list),
                 "there should be no protocol error ({0})".format(data[0]))

    tree = lxml.etree.fromstring(data)
    if what == "access date field":
        field = util.find_element((By.ID, "access-date"))
        value = field.get_attribute("value")

        date = tree.xpath("//mods:url/@dateLastAccessed",
                          namespaces={
                              "mods": "http://www.loc.gov/mods/v3"
                          })
        assert_equal(date[0], value)
    elif what == "url":
        field = util.find_element((By.ID, "version-specific"))
        value = field.is_selected()
        urls = tree.xpath("//mods:url",
                          namespaces={
                              "mods": "http://www.loc.gov/mods/v3"
                          })
        assert_true(len(urls) == 1, "there should be exactly one url")

        permalinks = get_permalinks(driver)

        assert_equal(''.join(urls[0].itertext()),
                     permalinks['version-specific' if value
                                else 'non-version-specific'],
                     "the url value should be correct")
    else:
        raise ValueError("unknown value for ``what`` parameter")


@then(r'the citations show the url specified by the version-specific '
      r'checkbox')
def step_impl(context):
    util = context.util
    driver = context.driver

    field = util.find_element((By.ID, "version-specific"))

    value = field.is_selected()

    permalinks = get_permalinks(driver)
    expected_url = permalinks['version-specific' if value
                              else 'non-version-specific']

    url_spans = driver.execute_script("""
    return Array.prototype.map.call(
        document.querySelectorAll("#cite-modal a.url"),
        function (x) {
            return {href: x.href, text: x.textContent};
    });
    """)

    assert_true(len(url_spans) > 0, "there should be some spans")
    for span in url_spans:
        assert_equal(span["href"], expected_url,
                     "the link href should match the expected URL")
        assert_equal(span["text"], expected_url,
                     "the link text should match the expected URL")


@when(r'the user clicks the version-specific checkbox')
def step_impl(context):
    util = context.util
    field = util.find_element((By.ID, "version-specific"))
    field.click()


@then(r'the MODS data is downloaded')
def step_impl(context):
    util = context.util
    download_dir = context.download_dir
    if download_dir is not None:
        mods_path = os.path.join(download_dir, "mods")
        util.wait(lambda *_: os.path.exists(mods_path))
        # This test is not meant to check the data's structure so we
        # read the file and make sure it parses.
        with open(mods_path, 'r') as f:
            data = f.read()
        lxml.etree.fromstring(data)
    #
    # else: skip this step
    #
    # Practically this means doing nothing. However, behave does not
    # give us the option to mark this step as skipped. The closest
    # would be: context.scenario.skip() but it marks the whole
    # scenario as skipped, which is not true. (The earlier steps have
    # run and have tested something.)

@then(r'the (?P<style>Chicago|MLA) author names are "(?P<names>.*?)"')
def step_impl(context, style, names):
    driver = context.driver

    selector = {
        "Chicago": "#chicago_authors",
        "MLA": "#mla_authors"
    }[style]

    authors = driver.execute_script("""
    var selector = arguments[0];
    return document.querySelector("#cite-modal " + selector).textContent
    """, selector)

    assert_equal(names, authors)

@then(r'the editor names are "(?P<names>.*?)"')
def step_impl(context, names):
    driver = context.driver

    editors = driver.execute_script("""
    return document.querySelector("#cite-modal #mla_editors").textContent
    """)

    assert_equal(names, editors)

@when(r'the user clicks the first semantic field button')
def step_impl(context):
    util = context.util
    button = util.find_element(
        (By.CSS_SELECTOR, r".field-view .popover-button"))
    button.click()

@when(r'the user clicks outside the semantic field popover')
def step_impl(context):
    util = context.util
    popover = util.find_element((By.CLASS_NAME, "sf-popover"))
    # We click outside the popover
    coords = util.element_page_coordinates(popover)
    x = -5 if coords["left"] > 5 else coords["width"] + 5
    # We used to also vary the y coordinate. The tests we currently
    # have don't actually **require** it. And it eventually caused
    # problems. It so happens that our popup has space outside of it
    # to the left/right but up/down so y ends up outside the
    # window. Earlier versions of Chrome/Chromedriver/Selenium would
    # be fine with it, but later versions have a problem if the
    # coordinate is outside the window. So for now we leave y to
    # 0. We'll change as needed if necessary in the future.
    y = 0
    ActionChains(context.driver) \
        .move_to_element_with_offset(popover, x, y) \
        .click() \
        .perform()


@then(r'a semantic field popover is (?P<visibility>(?:not )?visible)')
def step_impl(context, visibility):
    util = context.util
    condition = EC.visibility_of_element_located((By.CLASS_NAME, "sf-popover"))
    if visibility == "visible":
        util.wait(condition)
    else:
        util.wait_until_not(condition)
