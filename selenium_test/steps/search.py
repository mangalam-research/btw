from nose.tools import assert_equal  # pylint: disable=E0611


from selenium.webdriver.common.by import By
from behave import Then, When, step_matcher  # pylint: disable=E0611

step_matcher('re')


@When('^the user searches for headword "(?P<query>.*?)"')
def step_impl(context, query):
    util = context.util
    controls = util.find_elements((By.CSS_SELECTOR,
                                   "#search-table_filter input"))
    controls[0].send_keys(query)
    controls[1].click()


@Then('^the search results show one entry for "(?P<headword>.*?)"')
def step_impl(context, headword):
    util = context.util
    hits = util.find_elements((By.LINK_TEXT, headword))
    assert_equal(len(hits), 1, "one result")
