# -*- coding: utf-8 -*-
# pylint: disable=E0611
from selenium.webdriver.support.wait import TimeoutException
from nose.tools import assert_equal, assert_raises, assert_true
from behave import then, when, step_matcher  # pylint: disable=E0611

from selenium_test import btw_util

import wedutil

step_matcher("re")


@then("^the senses and subsenses are properly numbered$")
def step_impl(context):
    util = context.util

    def cond(*_):
        try:
            btw_util.assert_senses_in_order(util)
            return True
        except AssertionError:
            return False

    try:
        util.wait(cond)
    except TimeoutException:
        # This is more useful than a timeout error.
        btw_util.assert_senses_in_order(util)
