from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

require_sense_recording = {}
require_rendition_recording = {}


def record_senses(f):
    """
    This is a decorator used to mark a step as requiring that senses
    be recorded. This decorator must come **before** the ``@then``,
    ``@when``, etc. decorators.

    By the time the step is executed the ``context`` object will have
    an ``initital_sense_terms`` field that lists all the sense terms
    **text** in order. (And not the *entire* sense.)
    """
    require_sense_recording[f] = True
    return f


def record_renditions_for(*senses):
    """
    This is a decorator used to mark a step as requiring recording the
    renditions for a specific sense.

    It is used as ``@record_renditions_for("A", "C", ...)``. The list
    of parameters are sense labels.

    By the time the step is executed, the ``context`` object will have
    an ``initial_renditions_by_sense`` field that contains a mapping
    from sense label (A, B, C) to a list of rendition term **text**.
    """
    def inner_record_renditions_for(f):
        require_rendition_recording[f] = senses
        return f
    return inner_record_renditions_for


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
    ret = []
    rends = sense.find_elements(By.CLASS_NAME, "btw\\:english-rendition")
    for rend in rends:
        try:
            term = rend.find_element(By.CLASS_NAME, "btw\\:english-term").text
        except NoSuchElementException:
            term = None
        ret.append(term)
    return ret


def sense_label_to_index(label):
    return ord(label) - ord("A")


def get_sense_by_label(util, label):
    sense_ix = sense_label_to_index(label)
    senses = get_senses(util)
    return senses[sense_ix]
