import itertools


from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By


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
    ret = []
    for sense in get_senses(util):
        try:
            term = sense.find_element_by_class_name("btw\\:english-term").text
        except NoSuchElementException:
            term = None
        ret.append(term)
    return ret


def get_senses(util):
    return util.find_elements((By.CLASS_NAME, "btw\\:sense"))


def get_rendition_terms_for_sense(sense):
    """
    :param sense: The sense we're interested in.
    :type sense: :class:`selenium.webdriver.remote.webelement.WebElement`
    :returns: A list of rendition terms for the sense.
    :rtype: :class:`list` of strings.

    """
    ret = []
    rends = sense.find_elements(By.CLASS_NAME, "btw\\:english-rendition")
    for rend in rends:
        try:
            term = rend.find_element(By.CLASS_NAME, "btw\\:english-term").text
        except NoSuchElementException:
            term = None
        ret.append(term)
    return ret


def get_subsenses_for_sense(util, sense):
    """
    :param sense: The sense we're interested in.
    :type sense: :class:`selenium.webdriver.remote.webelement.WebElement`
    :returns: A list of subsense information.
    :rtype: :class:`list` of dictionaries. Each dictionary has the key
            ``explanation`` set to the text of the explanation of the
            subsense and the key ``head`` set to the text of the
            subsense's heading. Both values are strings.

    """
    ret = []
    subsenses = sense.find_elements(By.CLASS_NAME, "btw\\:subsense")
    for ss in subsenses:
        try:
            explanation = ss.find_element(By.CLASS_NAME,
                                          "btw\\:explanation")
            explanation = util.get_text_excluding_children(explanation)
        except NoSuchElementException:
            explanation = None

        try:
            head = ss.find_element(By.CLASS_NAME, "head").text
        except NoSuchElementException:
            head = None
        ret.append({"explanation": explanation, "head": head})
    return ret


def sense_label_to_index(label):
    return ord(label) - ord("A")


def get_sense_by_label(util, label):
    sense_ix = sense_label_to_index(label)
    senses = get_senses(util)
    return senses[sense_ix]


def record_document_features(context):
    util = context.util
    # Some steps must know what the state of the document was before
    # transformations are applied, so record it.
    if context.require_sense_recording:
        # We gather the btw:english-term text associated with each btw:sense.
        context.initial_sense_terms = get_sense_terms(util)

    if context.require_rendition_recording:
        sense_els = get_senses(util)
        context.initial_renditions_by_sense = {}
        for sense in context.require_rendition_recording:
            sense_el = sense_els[sense_label_to_index(sense)]
            renditions = get_rendition_terms_for_sense(sense_el)

            context.initial_renditions_by_sense[sense] = renditions

    if context.require_subsense_recording:
        sense_els = get_senses(util)
        context.initial_subsenses_by_sense = {}
        for sense in context.require_subsense_recording:
            sense_el = sense_els[sense_label_to_index(sense)]
            subsenses = get_subsenses_for_sense(util, sense_el)

            context.initial_subsenses_by_sense[sense] = subsenses
