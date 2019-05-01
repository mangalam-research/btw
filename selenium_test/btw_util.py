import itertools
import re
import collections


from selenium.webdriver.support.wait import TimeoutException
from selenium.webdriver.common.by import By
import wedutil

# pylint: disable=no-name-in-module
from nose.tools import assert_equal, assert_true

from selenic.tables import Table
from selenic.util import Condition, Result


GET_CITATION_TEXT = r"""
function getCitationText(cit) {
  var data_cit = jQuery.data(cit, "wed_mirror_node");
  var clone = data_cit.cloneNode(true);
  var child = clone.firstElementChild;
  while (child) {
    var next = child.nextElementSibling;
    if (child.classList.contains("ref"))
      clone.removeChild(child);
    child = next;
  }
  return clone.textContent.trim();
}
"""


class PlainRecorder(dict):

    def decorator(self, f):
        self[f] = True
        return f


class SenseRecorder(dict):

    def decorator(self, *senses):
        def inner(f):
            self[f] = senses
            return f
        return inner

    def get_senses_for_functions(self, funcs):
        """
        :param funcs: List of functions for which we want to get senses.
        :type funcs: :class:`list`
        :returns: A set of sense labels.
        :rtype: :class:`set`
        """
        return set(itertools.chain.from_iterable(
            [senses for f, senses in self.items() if f in funcs]))

require_sense_recording = PlainRecorder()
require_rendition_recording = SenseRecorder()
require_subsense_recording = SenseRecorder()

record_senses = require_sense_recording.decorator
"""
   This is a decorator used to mark a step as requiring that senses be
   recorded. This decorator must come **before** the ``@then``,
   ``@when``, etc. decorators.

   By the time the step is executed the ``context`` object will have
   an ``initital_sense_terms`` field that lists all the sense terms
   **text** in order. (And not the *entire* sense.)

"""  # pylint: disable=W0105

record_renditions_for = require_rendition_recording.decorator
"""
   This is a decorator used to mark a step as requiring recording the
   renditions for one or more senses.

   It is used as ``@record_renditions_for("A", "C", ...)``. The list
   of parameters are sense labels.

   By the time the step is executed, the ``context`` object will have
   an ``initial_renditions_by_sense`` field that contains a mapping
   from sense label (A, B, C) to a list of rendition term **text**.

"""  # pylint: disable=W0105

record_subsenses_for = require_subsense_recording.decorator
"""
   This is a decorator used to mark a step as requiring recording the
   subsenses for one or more senses.

   It is used as ``@record_subsenses_for("A", "C", ...)``. The list of
   parameters are sense labels.

   By the time the step is executed, the ``context`` object will have
   an ``initial_subsenses_by_sense`` field that contains a mapping
   from sense label (A, B, C) to a list of subsense explanation
   **text**.

"""  # pylint: disable=W0105

SenseInfo = collections.namedtuple('SenseInfo', ('term', 'id'))


def get_senses(util):
    return [SenseInfo(**info) for info in util.driver.execute_script("""
    var $senses = jQuery(".btw\\\\:sense");
    var ret = [];
    for(var i = 0, limit = $senses.length; i < limit; ++i) {
        var $sense = $senses.eq(i);
        var $term = $sense.find(".btw\\\\:english-term");
        if ($term.length > 1)
            throw new Error("too many terms!");
        var $clone = $term.clone();
        $clone.find("._phantom").remove();
        ret.push({term: $clone[0] ? $clone.text().trim() : null,
                  id: $sense.attr("data-wed-xml---id-") || null});
    }
    return ret;
    """)]


def get_rendition_terms_for_sense(util, label):
    """
    :param label: The label of the sense we're interested in.
    :type label: :class:`str`
    :returns: A list of rendition terms for the sense.
    :rtype: :class:`list` of strings.

    """
    return get_rendition_terms_for_senses(util, [label])[label]


def get_rendition_terms_for_senses(util, labels):
    """
    :param labels: The labesl of the sense we're interested in.
    :type labels: :class:`list` of strings.
    :returns: A dictionary of rendition terms.
    :rtype: :class:`dict` whose keys are term labels and the values are
            the rendition terms, as strings.

    """
    return util.driver.execute_script("""
    var labels = arguments[0];

    var ret = {};
    for(var lix = 0, lix_limit = labels.length; lix < lix_limit; ++lix) {
        var label = labels[lix];

        var $sense = jQuery(".btw\\\\:sense")
            .eq(label.charCodeAt(0) - "A".charCodeAt(0));

        var $rends = $sense.find(".btw\\\\:english-rendition");
        var rends = [];
        for(var i = 0, limit = $rends.length; i < limit; ++i) {
            var $term = $rends.eq(i).find(".btw\\\\:english-term");
            if ($term.length > 1)
                throw new Error("too many terms!");
            var $clone = $term.clone();
            $clone.find("._phantom").remove();
            rends.push($clone[0] ? $clone.text().trim() : undefined);
        }
        ret[label] = rends;
    }
    return ret;
    """, labels)


def get_subsenses_for_sense(util, label):
    """
    :param label: The label of the sense we're interested in.
    :type label: :class:`str`
    :returns: A dictionary of subsense information.
    :rtype: :class:`dict` whose keys are sense labels and whose values are
            :class:`list` of dictionaries. Each dictionary has the key
            ``explanation`` set to the text of the explanation of the
            subsense and the key ``head`` set to the text of the
            subsense's heading. Both values are strings.

    """
    return get_subsenses_for_senses(util, [label])[label]


def get_subsenses_for_senses(util, labels):
    """
    :param labels: The labels of the sense we're interested in.
    :type labels: :class:`list` of strings.
    :returns: A list of subsense information.
    :rtype: :class:`list` of dictionaries. Each dictionary has the key
            ``explanation`` set to the text of the explanation of the
            subsense and the key ``head`` set to the text of the
            subsense's heading. Both values are strings.

    """

    return util.driver.execute_script("""
    var labels = arguments[0];

    var $ = jQuery;

    var ret = {};

    for(var lix = 0, lix_limit = labels.length; lix < lix_limit; ++lix) {
        var label = labels[lix];
        var $sense = $(".btw\\\\:sense")
            .eq(label.charCodeAt(0) - "A".charCodeAt(0));
        var $sss = $sense.find(".btw\\\\:subsense");
        var sss = [];
        for(var i = 0, limit = $sss.length; i < limit; ++i) {
            var $ss = $sss.eq(i);
            var $expl = $ss.find(".btw\\\\:explanation");
            if ($expl.length > 1)
                throw new Error("too many explanations!");

            var $head = $expl.children(".head");
            if ($head.length > 1)
                throw new Error("too many heads!");

            var expl = $expl[0] &&
                $expl.contents().filter(function() {
                    return this.nodeType == Node.TEXT_NODE;
                }).text();

            sss.push({ explanation: expl,
                       head: $head[0] && $head.text().trim()});
        }
        ret[label] = sss;
    }
    return ret;
    """, labels)


def record_document_features(context):
    util = context.util
    # Some steps must know what the state of the document was before
    # transformations are applied, so record it.
    if context.require_sense_recording:
        # We gather the btw:english-term text associated with each btw:sense.
        context.initial_senses = get_senses(util)

    if context.require_rendition_recording:
        context.initial_renditions_by_sense = \
            get_rendition_terms_for_senses(
                util, list(context.require_rendition_recording))

    if context.require_subsense_recording:
        context.initial_subsenses_by_sense = \
            get_subsenses_for_senses(
                util, list(context.require_subsense_recording))


def select_text_of_element_directly(context, selector):
    """
    This function is meant to be used to select text by direct
    manipulation of the DOM. This is meant for tests where we want to
    select text but we are not testing selection per se.

    .. warning:: This function will fail if an element has more than a
                 single text node.
    """
    text = wedutil.select_text_of_element_directly(context.util, selector)

    context.expected_selection = text


SENSE_LINK_RE = re.compile(r"\[.*?\]")


def get_sense_hyperlinks(util):
    def cond(driver):
        ret = driver.execute_script(r"""
        return jQuery(".wed-document a[href^='#BTW-S.']").toArray().map(
            function (x) {
            return { el: x, text: jQuery(x).text() };
        });
        """)

        # Always check that the hyperlinks are of the right form.  A
        # hyperlink may be incorrect for a small amount of time, so we
        # use a condition here rather than fail immediately.
        if any(l for l in ret if not SENSE_LINK_RE.match(l["text"])):
            return False

        # We can't return just ``ret`` because if there are no
        # hyperlinks it is a False value.
        return [ret]

    try:
        return util.wait(cond)[0]
    except TimeoutException:
        raise Exception("cannot get sense hyperlinks")


sense_re = re.compile(r"sense (.).?\b")
subsense_re = re.compile(r"sense (..)\b")


def assert_senses_in_order(util, viewing=False):
    """
    Verifies that all senses are properly labeled and that all
    occurrences of the word "sense" in headers that appear in a sense
    are followed by a proper sense label.
    """
    senses = util.driver.execute_script("""
    var senses = document.getElementsByClassName("btw:sense");
    var ret = [];
    for(var i = 0, limit = senses.length; i < limit; ++i) {
        var heads = senses[i].querySelectorAll(".head");
        var head_texts = [];
        for(var j = 0, j_limit = heads.length; j < j_limit; ++j)
            head_texts.push(heads[j].textContent);

        var subsenses = senses[i].querySelectorAll(".btw\\\\:subsense");
        var subsense_info = [];
        for(var j = 0, j_limit = subsenses.length; j < j_limit; ++j) {
            var subheads = subsenses[j].querySelectorAll(".head");
            var subhead_texts = [];
            for(var q = 0, q_limit = subheads.length; q < q_limit; ++q)
                subhead_texts.push(subheads[q].textContent);
            subsense_info.push(subhead_texts);
        }
        ret.push({heads: head_texts, subsenses: subsense_info});
    }
    return ret;
    """)
    sense_label_ix = ord("A")

    assert_true(len(senses) > 0)

    for sense in senses:
        saw_main_head = False
        assert_true(len(sense["heads"]) > 0, "there should be heads")
        if viewing:
            head = sense["heads"][0]
            assert_equal(head.strip(),
                         chr(sense_label_ix) + ".",
                         "the head label of the sense should be correct")
        else:
            for head in sense["heads"]:
                if head.startswith("[SENSE"):
                    saw_main_head = True
                    assert_equal(head.strip(),
                                 "[SENSE {0}]".format(chr(sense_label_ix)),
                                 "the head text should be correct")
                elif "sense" in head:
                    # This test in effect tests the heads that appear
                    # inside subsenses twice, but that's okay. (Here it
                    # tests that it is of the form "sense [abcdef]" and
                    # may have a number after it. The later test checks
                    # for the letter and the number.)
                    match = sense_re.search(head)
                    assert_equal(
                        match and match.group(1), chr(sense_label_ix).lower(),
                        "the subhead text should be correct for head " + head)
            subsense_label_ix = 1
            assert_true(saw_main_head, "should have seen the main head")
            for subsense in sense["subsenses"]:
                assert_true(len(subsense) > 0, "there should be heads in the "
                            "subsense")
                for head in subsense:
                    if "sense" in head:
                        match = subsense_re.search(head)
                        assert_equal(match and match.group(1),
                                     chr(sense_label_ix).lower() +
                                     str(subsense_label_ix),
                                     "subsense head text")
                subsense_label_ix += 1
        sense_label_ix += 1

def velocity_mock(driver, value):
    driver.execute_async_script("""
    var value = arguments[0];
    var done = arguments[1];
    require(["velocity"], function (velocity) {
      velocity.mock = value;
      done();
    });
    """, value)

info_re = re.compile(r"^Showing (\d+) to (\d+) of (\d+) entries")

class SFModalTable(Table):

    def __init__(self, *args, **kwargs):
        super(SFModalTable, self).__init__(*args, **kwargs)
        # The table is initialized as soon as it is in the DOM.
        self.initialized_locator = (By.ID, self.cssid)
        self.field_selectors = [".sf-search .search-form"]

    def setup_redraw_check(self):
        self.util.driver.execute_script("""
        var cssid = arguments[0];
        var table = document.getElementById(cssid);
        var viewEl = table.closest("[data-backbone-view]");
        var view = viewEl.backboneView;
        view.__seleniumTestingRefreshed = false;
        view.collection.once("update reset", function () {
          view.__seleniumTestingRefreshed = true;
        });
        """, self.cssid)

    def wait_for_redraw(self):
        self.util.driver.execute_async_script("""
        var cssid = arguments[0];
        var done = arguments[1];
        var table = document.getElementById(cssid);
        var viewEl = table.closest("[data-backbone-view]");
        var view = viewEl.backboneView;
        function check() {
          if (view.__seleniumTestingRefreshed) {
            delete view.__seleniumTestingRefreshed;
            return done();
          }
          setTimeout(check, 100);
        }
        check();
        """, self.cssid)

    def wait_for_results(self, expected_total):
        def check(driver):
            infos = driver.find_elements_by_css_selector(
                "#" + self.cssid + " .footer-information")

            if len(infos) == 0:
                total = 0
            else:
                text = infos[0].text

                match = info_re.match(text)
                if not match:
                    return Result(False, 0)

                total = int(match.group(3))
            return Result(total == expected_total, total)

        result = Condition(self.util, check).wait()

        return result.payload

    def get_result(self, number):
        return self.util.find_elements(
            (By.CSS_SELECTOR, "#" + self.cssid + ">table>tbody>tr"))[number]


class SemanticFieldCollection(object):
    top_selector = ""

    def __init__(self, util):
        self.util = util
        self._fields = None

    @property
    def field_selector(self):
        return self.top_selector + " .field-view"

    def reset(self):
        self._fields = None

    @property
    def fields(self):
        if self._fields is not None:
            return self._fields

        self._fields = self.util.driver.find_elements_by_css_selector(
            self.field_selector)
        return self._fields

    def count(self):
        return len(self.fields)

    def delete(self, index):
        if index != 0:
            raise ValueError("index other than 0 not implemented yet")

        orig_count = self.count()
        button = self.util.find_element(
            (By.CSS_SELECTOR, self.field_selector + " .delete-button"))
        self.reset()
        button.click()
        self.util.wait(lambda *_: self.count() < orig_count)

    def add(self, index):
        if index != 0:
            raise ValueError("index other than 0 not implemented yet")

    def get_field_labels(self):
        return self.util.driver.execute_script(r"""
        var selector = arguments[0];
        var els = document.querySelectorAll(selector);
        return Array.prototype.map.call(els, function (x) {
          return x.textContent.trim().replace(/\s+/, ' ');
        });
        """, self.field_selector)


class ChosenSemanticFields(SemanticFieldCollection):
    top_selector = ".sf-field-list"

class CombinatorElements(SemanticFieldCollection):
    top_selector = ".combinator-elements"

class NavigatorCollection(object):
    top_selector = ".sf-navigators"

    def __init__(self, util):
        self.util = util
        self._navigators = None

    def reset(self):
        self._navigators = None

    @property
    def navigators(self):
        if self._navigators is not None:
            return self._navigators

        self._navigators = self.util.find_elements(
            (By.CSS_SELECTOR,
             self.top_selector + " .semantic-field-details-card"))
        return self._navigators

    def count(self):
        return len(self.navigators)

def get_add_button_in(util, top):
    return util.wait(lambda *_: top.find_element_by_css_selector(".sf-add"))

def get_combine_button_in(util, top):
    return util.wait(lambda *_:
                     top.find_element_by_css_selector(".sf-combine"))

def register_sf_modal_on_context(context):
    util = context.util
    driver = context.driver

    # We have to wait for the table before moving on.
    table_el = util.find_element((By.CSS_SELECTOR,
                                  ".results [data-backbone-view]"))

    # The table does not get an id by default. We assign one to it.
    cssid = driver.execute_script("""
    var table = arguments[0];
    var id = "selenium-test-id-" + Date.now();
    table.id = id;
    return id;
    """, table_el)

    table = SFModalTable(util, "semantic field search",
                         cssid)
    context.register_table(table, True)

    context.semantic_field_collections = {
        "chosen semantic fields": ChosenSemanticFields(util),
        "combinator elements": CombinatorElements(util),
    }
