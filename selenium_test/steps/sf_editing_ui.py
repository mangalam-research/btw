from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from nose.tools import assert_equal
# pylint: disable=no-name-in-module
from behave import then, given, when, step_matcher

from ..btw_util import velocity_mock, NavigatorCollection, get_add_button_in, \
    get_combine_button_in, register_sf_modal_on_context

step_matcher('re')

@given(ur"the sf_editor_test page is loaded")
def step_impl(context):
    driver = context.driver
    util = context.util
    driver.get(context.builder.SERVER + "/lexicography/sf_editor_test/")

    # Mark the fact that we are on this page in the context.
    context.sf_editor_test = True

    # Don't wait for animations.
    velocity_mock(driver, True)

    register_sf_modal_on_context(context)

@when(ur"the user deletes a field in the "
      "(?P<collection>chosen semantic fields|combinator elements)")
def step_impl(context, collection):
    collection = context.semantic_field_collections[collection]
    collection.delete(0)

@when(ur"the user clicks on the (?P<what>add|combine) button in the "
      ur"(?P<where>first result|first detail pane|combinator)")
def step_impl(context, what, where):
    util = context.util
    if where == "first result":
        table = context.default_table
        scope = table.get_result(0)
    elif where == "first detail pane":
        navs = NavigatorCollection(util)
        scope = navs.navigators[0]
    elif where == "combinator":
        scope = util.find_element((By.CLASS_NAME, "combinator-results"))
    else:
        raise ValueError("unexpected where value: " + where)

    if what == "add":
        button = get_add_button_in(util, scope)
    elif what == "combine":
        button = get_combine_button_in(util, scope)
    else:
        raise ValueError("unexpected what value: " + what)

    button.click()

field_count_re = (
    ur"there (?:are|is) (?P<count>\d+|no|one) fields? in the "
    ur"(?P<collection>combinator elements|chosen semantic fields)")
@given(field_count_re)
@then(field_count_re)
def step_impl(context, count, collection):
    collection = context.semantic_field_collections[collection]
    collection.reset()

    if count == "no":
        count = 0
    elif count == "one":
        count = 1
    else:
        count = int(count)

    assert_equal(collection.count(), count)

chosen_field_label_re = ur"the chosen semantic fields are (?P<fields>.*)"
@given(chosen_field_label_re)
@then(chosen_field_label_re)
def step_impl(context, fields):
    collection = context.semantic_field_collections["chosen semantic fields"]

    labels = collection.get_field_labels()
    assert_equal(", ".join('"{}"'.format(label) for label in labels), fields)

# This does not actually work.
@when(ur"the user swaps the first and second chosen semantic fields by "
      ur"drag and drop")
def step_impl(context):
    raise Exception("this step is not working")

    collection = context.semantic_field_collections["chosen semantic fields"]
    first_field = collection.fields[0]
    second_field = collection.fields[1]
    third_field = collection.field[2]
    third_field_rect = context.util.element_screen_coordinates(third_field)

    ActionChains(context.driver) \
        .click_and_hold(first_field) \
        .move_to_element_with_offset(second_field) \
        .move_to_element_with_offset(third_field) \
        .release() \
        .perform()
