from nose.tools import assert_equal
# pylint: disable=no-name-in-module
from behave import then, when, given, step_matcher
from selenic.util import Result, Condition

from ..btw_util import register_sf_modal_on_context

step_matcher('re')

__sf_re = ur"the document contains the fields (?P<fields>.*)"
@then(__sf_re)
@given(__sf_re)
def step_impl(context, fields):

    def check(driver):
        field_text = driver.execute_script(r"""
        var selector = arguments[0];
        var els = document.querySelectorAll(selector);
        return Array.prototype.map.call(els, function (x) {
          return x.textContent.trim().replace(/\s+/, ' ');
        });
        """, r".btw\:sf")

        combined = ", ".join('"{}"'.format(text) for text in field_text)
        return Result(combined == fields, combined)

    result = Condition(context.util, check).wait()
    assert_equal(result.payload, fields)


@step("the document does not contain any semantic fields")
def step_impl(context):
    driver = context.driver
    assert_equal(len(driver.find_elements_by_class_name(r"btw\:sf")), 0)

@when("the user brings up the semantic field editing dialog")
def step_impl(context):
    context.execute_steps(u"""
    When the user clicks in the first semantic field list
    And the user brings up the context menu
    And the user clicks the context menu option "Edit semantic fields"
    Then there is a modal dialog titled "Edit Semantic Fields" visible
    """)
    register_sf_modal_on_context(context)
