import itertools


from selenium.webdriver.common.by import By
import wedutil


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
            [senses for f, senses in self.iteritems() if f in funcs]))

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


def get_sense_terms(util):
    return util.driver.execute_script("""
    var $senses = jQuery(".btw\\\\:sense");
    var ret = [];
    for(var i = 0, limit = $senses.length; i < limit; ++i) {
        var $term = $senses.eq(i).find(".btw\\\\:english-term");
        if ($term.length > 1)
            throw new Error("too many terms!");
        var $clone = $term.clone();
        $clone.find("._phantom").remove();
        ret.push($clone[0] ? $clone.text().trim() : undefined);
    }
    return ret;
    """)


def get_senses(util):
    return util.find_elements((By.CLASS_NAME, "btw\\:sense"))


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

            sss.push({ explanation: expl, head: $head[0] && $head.text()});
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
        context.initial_sense_terms = get_sense_terms(util)

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
