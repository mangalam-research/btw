from selenium.webdriver.common.by import By
# pylint: disable=E0611
from nose.tools import assert_equal
from behave import step_matcher  # pylint: disable=E0611

import wedutil

step_matcher('re')


@then(r'the btw:explanation for the (?P<parent>btw:sense|btw:subsense) '
      r'(?P<has>has(?: no)?) numbering')
def step_impl(context, parent, has):
    util = context.util
    prefix = "." + parent.replace(":", r"\:") + r">.btw\:explanation"

    if has == "has":
        util.find_element((By.CSS_SELECTOR, prefix + ">._explanation_number"))
    else:
        expl = util.find_element((By.CSS_SELECTOR, prefix))
        wedutil.wait_for_first_validation_complete(util)
        assert_equal(
            len(expl.find_elements_by_css_selector("._explanation_number")), 0)
