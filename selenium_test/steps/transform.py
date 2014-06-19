# -*- coding: utf-8 -*-
import re

from selenium.webdriver.support.wait import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium_test.btw_util import record_senses, record_renditions_for, \
    record_subsenses_for
# pylint: disable=E0611
from nose.tools import assert_equal, assert_raises, assert_true
from behave import then, when, step_matcher  # pylint: disable=E0611

from selenium_test import btw_util

import wedutil

sense_re = re.compile(r"sense (.)\b")


def senses_in_order(util):
    senses = util.driver.execute_script("""
    var $senses = jQuery(".btw\\\\:sense");
    var ret = [];
    for(var i = 0, limit = $senses.length; i < limit; ++i) {
        var $heads = $senses.eq(i).find(".head");
        var heads = [];
        for(var j = 0, j_limit = $heads.length; j < j_limit; ++j)
            heads.push($heads.eq(j).text());
        ret.push(heads);
    }
    return ret;
    """)
    label_ix = ord("A")

    for sense in senses:
        for head in sense:
            if head.startswith("[SENSE"):
                assert_equal(head.strip(),
                             "[SENSE {0}]".format(chr(label_ix)),
                             "head text")
            elif "sense" in head:
                match = sense_re.search(head)
                assert_equal(match.group(1), chr(label_ix).lower(),
                             "subhead text")
        label_ix += 1


@record_senses
@then(u'sense {first} becomes sense {second}')
def step_impl(context, first, second):
    util = context.util

    initial_senses = context.initial_senses
    first_ix = ord(first) - ord("A")
    second_ix = ord(second) - ord("A")

    senses = btw_util.get_senses(util)

    assert_equal(initial_senses[first_ix].term, senses[second_ix].term,
                 "relative order of the senses")

    senses_in_order(util)


@record_senses
@then(u'sense {label} remains the same')
def step_impl(context, label):
    context.execute_steps(u"""
    Then sense {0} becomes sense {0}
    """.format(label))


@record_senses
@then(u'a new sense {label} is created')
def step_impl(context, label):
    util = context.util

    initial_senses = context.initial_senses
    ix = ord(label) - ord("A")

    senses = btw_util.get_senses(util)

    assert_equal(len(initial_senses) + 1, len(senses), "number of terms")
    assert_equal(senses[ix].term, '', "the new sense has no term yet")


@when(u'the user undoes')
def step_impl(context):
    driver = context.driver
    util = context.util

    undo = util.find_clickable_element((By.CLASS_NAME, "icon-undo"))
    ActionChains(driver) \
        .click(undo) \
        .perform()


@record_senses
@then(u'the senses are the same as originally')
def step_impl(context):
    util = context.util
    senses_in_order(util)

    initial_senses = context.initial_senses

    util.wait(lambda *_: initial_senses == btw_util.get_senses(util))


@record_renditions_for("A")
@then(u'the first english rendition becomes second')
def step_impl(context):
    util = context.util
    initial_renditions = context.initial_renditions_by_sense["A"]

    def cond(*_):
        renditions = btw_util.get_rendition_terms_for_sense(util, "A")
        return renditions if len(renditions) == len(initial_renditions) + 1 \
            else None

    renditions = util.wait(cond)

    assert_equal(initial_renditions[0], renditions[1], "renditions")


@record_renditions_for("A")
@then(u'a new first english rendition is created')
def step_impl(context):
    util = context.util

    initial_renditions = context.initial_renditions_by_sense["A"]
    renditions = btw_util.get_rendition_terms_for_sense(util, "A")
    assert_equal(len(renditions), len(initial_renditions) + 1, "length")
    assert_equal(renditions[0], '', "first rendition is new")


@record_renditions_for("A")
@then(u'the first english rendition remains the same')
def step_impl(context):
    util = context.util
    initial_renditions = context.initial_renditions_by_sense["A"]

    def cond(*_):
        renditions = btw_util.get_rendition_terms_for_sense(util, "A")
        return renditions if len(renditions) == len(initial_renditions) + 1 \
            else None

    renditions = util.wait(cond)

    assert_equal(initial_renditions[0], renditions[0], "renditions")


@record_renditions_for("A")
@then("a new english rendition is created after the first")
def step_impl(context):
    util = context.util

    initial_renditions = context.initial_renditions_by_sense["A"]
    renditions = btw_util.get_rendition_terms_for_sense(util, "A")
    assert_equal(len(renditions), len(initial_renditions) + 1, "length")
    assert_equal(renditions[1], '', "second rendition is new")


@then("the single sense contains a single subsense")
def step_impl(context):
    util = context.util

    subsenses = btw_util.get_subsenses_for_sense(util, "A")

    assert_equal(len(subsenses), 1, "there is one subsense")
    assert_equal(subsenses[0]["head"], "[brief explanation of sense a1]",
                 "correct heading")

step_matcher('re')


@record_subsenses_for("A")
@then(ur"^the single sense contains an additional subsense "
      ur"(?P<where>after|before) the one that was already there\.?$")
def step_impl(context, where):
    util = context.util

    initial_subsenses = context.initial_subsenses_by_sense["A"]
    subsenses = btw_util.get_subsenses_for_sense(util, "A")
    assert_equal(len(subsenses), len(initial_subsenses) + 1,
                 "one new subsense")

    if where == "after":
        assert_equal(subsenses[0],
                     {"explanation": u"sense a1",
                      "head": u"[brief explanation of sense a1]"})
        assert_equal(subsenses[1],
                     {"explanation": u'',
                      "head": u"[brief explanation of sense a2]"})
    elif where == "before":
        assert_equal(subsenses[0],
                     {"explanation": u'',
                      "head": u"[brief explanation of sense a1]"})
        assert_equal(subsenses[1],
                     {"explanation": u"sense a1",
                      "head": u"[brief explanation of sense a2]"})
    else:
        raise ValueError("unexpected value for where: " + where)


@then("^a new (?P<what>.*?) is created(?: in (?P<inside>.*))?$")
def step_impl(context, what, inside=None):
    util = context.util

    selector = ""
    if inside:
        selector = "." + inside.replace(":", r"\:")

    selector += " ." + what.replace(":", r"\:")

    util.find_element((By.CSS_SELECTOR, selector))


@when(ur"^the user clicks on the visible absence for (?P<what>.*?)"
      ur"(?: in (?P<inside>.*))?$")
def step_impl(context, what, inside=None):
    driver = context.driver

    button = driver.execute_script(ur"""
    var what = arguments[0];
    var inside = arguments[1];

    var selector = "._va_instantiator:contains('Create new " + what + "')";
    if (inside)
        selector = "." + inside.replace(":", "\\:") + " " + inside;

    return jQuery(selector)[0];
    """, what, inside)
    ActionChains(driver) \
        .click(button) \
        .perform()


@then("^there is (?P<assertion>a|no) visible absence for (?P<what>.*)$")
def step_impl(context, assertion, what):
    driver = context.driver

    def cond(*_):
        button = driver.execute_script("""
        var what = arguments[0];
        return jQuery("._va_instantiator:contains('Create new " + what +
                      "')")[0];
        """, what)

        is_none = button is None
        return is_none if assertion == "no" else not is_none

    context.util.wait(cond)


hyperlink_re = re.compile(ur'"(.*?)"')


@then("^there is no (?P<what>.*)$")
def step_impl(context, what):
    util = context.util

    if what.startswith("hyperlink with the label "):
        match = hyperlink_re.search(what)
        label = match.group(1)

        def cond(*_):
            links = btw_util.get_sense_hyperlinks(context.util)
            return any(l for l in links if l["text"] == label)

        assert_raises(TimeoutException, util.wait, cond)
    else:
        what = "." + what.replace(":", r"\:")

        assert_raises(TimeoutException, util.find_element,
                      (By.CSS_SELECTOR, what))


@then(ur"^the (?P<what>btw:example|btw:example-explained|"
      ur"btw:explanation in btw:example-explained) has a Wheel of Dharma$")
def step_impl(context, what):
    util = context.util

    if what == "btw:explanation in btw:example-explained":
        what = r".btw\:example-explained>.btw\:explanation " \
               r"._phantom._explanation_bullet"
    else:
        what = "." + what.replace(":", r"\:") + " ._phantom._cit_bullet"

    util.find_element((By.CSS_SELECTOR, what))


@then(ur"^the (?P<what>btw:example|btw:example-explained|"
      ur"btw:explanation in btw:example-explained) does not have a Wheel "
      ur"of Dharma$")
def step_impl(context, what):
    util = context.util

    if what == "btw:explanation in btw:example-explained":
        what = r".btw\:example-explained>.btw\:explanation " \
               r"._phantom._explanation_bullet"
    else:
        what = "." + what.replace(":", r"\:") + " ._phantom._cit_bullet"

    util.wait_until_not(lambda driver: driver.find_element_by_css_selector(
        what))


@when(ur"^the user removes the language from the "
      ur"(?:btw:example|btw:example-explained)$")
def step_impl(context):
    util = context.util
    util.ctrl_equivalent_x("]")
    context.execute_steps(u"""
    When the user clicks on the end label of the last foreign element
    And the user brings up the context menu
    And the user clicks the context menu option "Unwrap the content of \
this element"
    """)


__EXAMPLE_SELECTORS = {
    u"btw:example": ur".btw\:example .btw\:cit:first",
    u"btw:example-explained": ur".btw\:example-explained .btw\:cit:first"
}


@when(ur"^the user adds the Pāli language to the "
      ur"(?P<what>btw:example|btw:example-explained)$")
def step_impl(context, what):
    util = context.util

    selector = __EXAMPLE_SELECTORS[what]

    btw_util.select_text_of_element_directly(context, selector)

    assert_equal(context.expected_selection, "foo")
    context.execute_steps(u"""
    When the user clicks the Pāli button
    """)


@given(ur"^the btw:definition does not contain foreign text")
def step_impl(context):
    driver = context.driver

    el = driver.find_elements_by_css_selector(r".btw\:definition .foreign")
    assert_equal(len(el), 0, "there should be no elements")


@when(ur'the user marks the text "prasāda" as (?P<lang>Pāli|Sanskrit|Latin) '
      ur'in btw:definition')
def step_impl(context, lang):
    driver = context.driver
    util = context.util

    p = driver.execute_script(u"""
    var $p = jQuery(".p");
    var $text = $p.contents().filter(function () {
        return this.nodeType === Node.TEXT_NODE;
    });
    var text_node = $text[0];
    var offset = text_node.nodeValue.indexOf("prasāda");
    wed_editor.setGUICaret(text_node, offset);
    return $p[0];
    """)

    util.send_keys(p,
                   [Keys.SHIFT] + [Keys.ARROW_RIGHT] * len(u"prasāda") +
                   [Keys.SHIFT])

    context.execute_steps(u"""
    When the user clicks the {0} button
    """.format(lang))


@when(ur'the user wraps the text "(?P<text>.*?)" in a (?P<wrapper>.*?) '
      ur'in (?P<where>.*)')
def step_impl(context, text, wrapper, where):
    driver = context.driver
    util = context.util

    selector = "." + where.replace(":", ur"\:")

    if where == "btw:definition":
        selector += " .p"

    p = driver.execute_script(ur"""
    var text = arguments[0];
    var selector = arguments[1];
    var $text = jQuery(selector).contents().filter(function () {
        return this.nodeType === Node.TEXT_NODE;
    });
    var text_node = $text[0];
    var offset = text_node.data.indexOf(text);
    wed_editor.setGUICaret(text_node, offset);
    return text_node.parentNode;
    """, text, selector)

    util.send_keys(p,
                   [Keys.SHIFT] + [Keys.ARROW_RIGHT] * len(text) +
                   [Keys.SHIFT])

    context.execute_steps(u"""
    When the user brings up the context menu
    And the user clicks the context menu option "Wrap in {0}"
    """.format(wrapper))


@then(ur'^the text "(?P<text>.*?)" is wrapped in a (?P<wrapper>.*)')
def step_impl(context, text, wrapper):
    util = context.util

    selector = "." + wrapper.replace(":", ur"\:")

    if wrapper == "btw:sense-emphasis":
        selector = r".btw\:definition .p " + selector

    util.wait(lambda driver:
              driver.execute_script(ur"""
              var text = arguments[0];
              var selector = arguments[1];
              return jQuery(selector).first().contents().filter(function () {
                      return this.nodeType === Node.TEXT_NODE;
                  }).text() === text;
              """, text, selector))


@when(ur"^the user clicks the (?P<lang>Pāli|Sanskrit|Latin) button$")
def step_impl(context, lang):
    button = context.driver.execute_script(u"""
    return jQuery("#toolbar .btn:contains('{0}')")[0];
    """.format(lang))
    button.click()

LANG_TO_CODE = {
    u"Pāli": u"pi-Latn",
    u"Sanskrit": u"sa-Latn",
    u"Latin": u"la"
}


@then(ur'^the text "prasāda" is marked as (?P<lang>Pāli|Sanskrit|Latin) '
      ur'in btw:definition$')
def step_impl(context, lang):
    driver = context.driver
    util = context.util

    test = driver.execute_script(ur"""
    var $el = jQuery(".btw\\:definition .foreign:contains('prasāda')");
    if (!$el[0])
        return [false, undefined];
    return [true, $el.attr('data-wed-xml---lang')];
    """)
    assert_true(test[0])
    assert_equal(test[1], LANG_TO_CODE[lang])


@when(ur"^the user clears formatting from the (?P<what>first paragraph"
      ur"(?: and second paragraph)?) in btw:definition$")
def step_impl(context, what):
    driver = context.driver
    util = context.util

    if what == "first paragraph":
        wedutil.select_contents_directly(util, r".btw\:definition .p")
    else:
        paras = driver.execute_script(ur"""
        var $p = jQuery(".btw\\:definition .p");
        var last = $p.last()[0];
        return [ $p[0], last, last.childNodes.length ];
        """)
        wedutil.select_directly(util, paras[0], 0, paras[1], paras[2])

    button = context.driver.execute_script(u"""
    var $buttons = jQuery("#toolbar .btn");
    return $buttons.has("i.icon-eraser")[0];
    """)
    button.click()


@then(ur"^the first paragraph in btw:defintion (?P<test>does not contain"
      ur"|contains) formatted text$")
def step_impl(context, test):
    util = context.util

    selector = r".btw\:definition .p ._real"
    if test == "does not contain":
        util.wait(
            lambda driver: len(driver.find_elements_by_css_selector(
                selector)) == 0)
    elif test == "contains":
        util.find_element((By.CSS_SELECTOR, selector))
    else:
        raise ValueError("unknown test: " + test)


@then(ur"^the user gets a dialog saying that the selection is straddling$")
def step_impl(context):
    util = context.util
    modal = util.find_element((By.CSS_SELECTOR, ".modal.in"))
    assert_true(modal.text.find("The text selected straddles") > -1)

__PARAGRAPH_COUNT_RE = ur"^the definition contains (?P<number>\d+) paragraphs?"


@then(__PARAGRAPH_COUNT_RE)
@given(__PARAGRAPH_COUNT_RE)
def step_impl(context, number):
    ps = context.util.find_elements((By.CSS_SELECTOR, r".btw\:definition .p"))
    assert_equal(len(ps), int(number),
                 "there should be " + number + " paragraphs")


@when(ur"^the user clicks in the first paragraph of the definition")
def step_impl(context):
    ps = context.util.find_element((By.CSS_SELECTOR, r".btw\:definition .p"))
    ps.click()


@when(ur"^the user clicks at the start of the second paragraph of the "
      ur"definition")
def step_impl(context):
    ps = context.util.find_elements((By.CSS_SELECTOR, r".btw\:definition .p"))
    ActionChains(context.driver) \
        .move_to_element_with_offset(ps[1], 1, 2) \
        .click() \
        .perform()

__SF_COUNT_RE = ur"^the document contains (?P<number>\d+) semantic fields?$"


@then(__SF_COUNT_RE)
@given(__SF_COUNT_RE)
def step_impl(context, number):
    sfs = context.util.find_elements((By.CSS_SELECTOR, r".btw\:sf"))
    assert_equal(len(sfs), int(number),
                 "there should be " + number + " semantic fields")


@when(ur"^the user clicks in the first semantic field")
def step_impl(context):
    sfs = context.util.find_element((By.CSS_SELECTOR, r".btw\:sf"))
    sfs.click()


@when(ur"^the user clicks at the start of the second semantic field")
def step_impl(context):
    sfs = context.util.find_elements((By.CSS_SELECTOR, r".btw\:sf"))
    ActionChains(context.driver) \
        .move_to_element_with_offset(sfs[1], 1, 2) \
        .click() \
        .perform()


@when(ur'^the user adds the text "blip" in btw:tr$')
def step_impl(context):
    driver = context.driver

    tr = driver.find_element_by_css_selector(r".__start_label._btw\:tr_label")

    tr.click()
    context.execute_steps(u"""
    When the user hits the right arrow
    And the user types "blip"
    """)
