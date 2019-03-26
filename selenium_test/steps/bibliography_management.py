# -*- encoding: utf-8 -*-

# pylint: disable=no-name-in-module
from behave import then, when, step_matcher
from selenium.webdriver.common.action_chains import ActionChains

step_matcher('re')


@when(r"the user clicks the button for refreshing the bibliography")
def step_impl(context):
    driver = context.driver

    context.prev_refresh_date = \
        driver.find_element_by_id("btw-prev-refreshed").text
    driver.find_element_by_id("btw-refresh").click()

@then(r"the bibliography is refreshed")
def step_impl(context):
    util = context.util
    driver = context.driver

    span = driver.find_element_by_id("btw-prev-refreshed")

    with util.local_timeout(10):
        util.wait(lambda *_: context.prev_refresh_date != span.text)
