from nose.tools import assert_equal  # pylint: disable=no-name-in-module

step_matcher('re')

OPTION_TO_ID = {
    "Bibliography/Manage": "btw-bibliography-manage-sub"
}


@then(ur'^the user does not have the "(?P<option>.*?)" navigation option$')
def step_impl(context, option):
    driver = context.driver
    assert_equal(len(driver.find_elements_by_id(OPTION_TO_ID[option])), 0)


@then(ur'^the user has the "(?P<option>.*?)" navigation option$')
def step_impl(context, option):
    driver = context.driver
    assert_equal(len(driver.find_elements_by_id(OPTION_TO_ID[option])), 1)
