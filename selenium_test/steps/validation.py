# pylint: disable=E0611
from nose.tools import assert_equal, assert_true, assert_false

from lexicography.tests.data import invalid_sf_cases

step_matcher('re')


@given('the document is completely validated')
def step_impl(context):
    driver = context.driver
    driver.execute_async_script("""
    var done = arguments[0];
    wed_editor.firstValidationComplete.then(function () {
        done();
    });
    """)

@then('there are no errors')
def step_impl(context):
    driver = context.driver

    count = driver.execute_script("""
    return wed_editor.validationController.copyErrorList().length;
    """)

    assert_equal(count, 0)


@then(r'there is an error reporting that sense (?P<label>.*?) is '
      r'without semantic fields')
def step_impl(context, label):
    driver = context.driver

    label = "[SENSE " + label + "]"

    assert_true(driver.execute_script("""
    var label = arguments[0];
    var errors = wed_editor.validationController.copyErrorList();
    for (var i = 0, error; (error = errors[i]); ++i) {
        var ev = error.ev;
        if (ev.error.toString() === "sense without semantic fields") {
            var node = ev.node.childNodes[ev.index];
            var gui_node = wed_editor.fromDataNode(node);
            var head = gui_node.getElementsByClassName("head")[0]
                .textContent.trim();
            if (head === label)
                return true;
        }
    }
    return false;
    """, label))

def check_error(context, expected_error_text, expected_tag=None, child=True,
                existing=True):
    """
    Generic function for finding errors.

    :param expected_error_text: The expected text of the error.
    :param expected_tag: The expected tag to which the error belongs.
    :param child: Whether or not the expected tag is that of the node
                  associated with the error message or that of the
                  child of that node found at the index provided by
                  the error message. (Error objects on the JavaScript
                  side have three fields: ``error`` which is the error
                  message, and ``node`` and ``index`` which identify
                  the DOM node to which the error belongs.)

    """
    driver = context.driver

    test = assert_true if existing else assert_false

    test(driver.execute_script("""
    var expected_error_text = arguments[0];
    var expected_tag = arguments[1];
    var child = arguments[2];
    var errors = wed_editor.validationController.copyErrorList();
    for (var i = 0, error; (error = errors[i]); ++i) {
        var ev = error.ev;
        if (ev.error.toString() === expected_error_text) {
            if (!expected_tag) {
                return true;
            }

            var node = child ? ev.node.childNodes[ev.index]: ev.node;
            var gui_node = wed_editor.fromDataNode(node);
            if (gui_node.classList.contains(expected_tag)) {
                return true;
            }
        }
    }
    return false;
    """, expected_error_text, expected_tag, child))


@then(r'there is an error reporting that a cognate is without semantic '
      r'fields')
def step_impl(context):
    check_error(context, "cognate without semantic fields", "btw:cognate")


@then(r'there are errors reporting the bad semantic fields')
def step_impl(context):
    check_error(
        context, "semantic field is not in a recognized format", "btw:sf")


@then(r'there is an error reporting an empty surname')
def step_impl(context):
    check_error(context, "surname cannot be empty", "surname", False)


@then(r'there is an error reporting a missing editor')
def step_impl(context):
    check_error(context, "there must be at least one editor",
                "btw:credits", False)

@then(r'there is an error reporting a missing author')
def step_impl(context):
    check_error(context, "there must be at least one author",
                "btw:credits", False)

@then(r'there are no errors reporting a bad semantic field')
def step_impl(context):
    check_error(
        context, "semantic field is not in a recognized format",
        existing=False)
