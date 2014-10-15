# pylint: disable=E0611
from nose.tools import assert_equal, assert_true

step_matcher('re')


@given('^the document is completely validated$')
def step_impl(context):
    driver = context.driver
    driver.execute_async_script("""
    var done = arguments[0];
    wed_editor.whenCondition("first-validation-complete", function () {
        done()
    });
    """)

@then('^there are no errors$')
def step_impl(context):
    driver = context.driver

    count = driver.execute_script("""
    return wed_editor._validation_errors.length;
    """)

    assert_equal(count, 0)


@then(r'^there is an error reporting that sense (?P<label>.*?) is '
      r'without semantic fields$')
def step_impl(context, label):
    driver = context.driver

    label = "[SENSE " + label + "]"

    assert_true(driver.execute_script("""
    var label = arguments[0];
    var errors = wed_editor._validation_errors;
    for (var i = 0, error; (error = errors[i]); ++i) {
        if (error.error.toString() === "sense without semantic fields") {
            var node = error.node.childNodes[error.index];
            var gui_node = jQuery.data(node, "wed_mirror_node");
            var head = gui_node.getElementsByClassName("head")[0]
                .textContent.trim();
            console.log(head);
            if (head === label)
                return true;
        }
    }
    return false;
    """, label))

@then(r'^there is an error reporting that a cognate is without semantic '
      r'fields$')
def step_impl(context):
    driver = context.driver

    assert_true(driver.execute_script("""
    var errors = wed_editor._validation_errors;
    for (var i = 0, error; (error = errors[i]); ++i) {
        if (error.error.toString() === "cognate without semantic fields") {
            var node = error.node.childNodes[error.index];
            var gui_node = jQuery.data(node, "wed_mirror_node");
            if (gui_node.classList.contains("btw:cognate"))
                return true;
        }
    }
    return false;
    """))
