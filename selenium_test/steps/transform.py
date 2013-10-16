import re

from selenium_test.btw_util import record_senses
from nose.tools import assert_equal, assert_is_none  # pylint: disable=E0611
from behave import then  # pylint: disable=E0611

import wedutil

sense_re = re.compile(r"sense (.)\b")


@record_senses
@then(u'sense {first} becomes sense {second}')
def step_impl(context, first, second):
    util = context.util

    initial_terms = context.initial_sense_terms
    first_ix = ord(first) - ord("A")
    second_ix = ord(second) - ord("A")

    terms = wedutil.get_sense_terms(util)

    assert_equal(initial_terms[first_ix], terms[second_ix],
                 "relative order of the senses")

    senses = wedutil.get_senses(util)
    label_ix = ord("A")
    for sense in senses:
        heads = sense.find_elements_by_class_name("head")
        for head in heads:
            text = head.text
            if text.startswith("[SENSE"):
                assert_equal(text, "[SENSE {0}]".format(chr(label_ix)),
                             "head text")
            elif "sense" in text:
                match = sense_re.search(text)
                assert_equal(match.group(1), chr(label_ix).lower(),
                             "subhead text")
        label_ix += 1


@record_senses
@then(u'a new sense {label} is created')
def step_impl(context, label):
    util = context.util

    initial_terms = context.initial_sense_terms
    ix = ord(label) - ord("A")

    terms = wedutil.get_sense_terms(util)

    assert_equal(len(initial_terms) + 1, len(terms), "number of terms")
    assert_is_none(terms[ix], "the new sense has no term yet")
