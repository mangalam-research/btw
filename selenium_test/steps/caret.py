from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

import wedutil

import btw_util

step_matcher('re')


@when(r"the user clicks on the btw:none element of (?P<parent>.*)")
def step_impl(context, parent):
    util = context.util

    parent = "." + parent.replace(":", r"\:")
    element = util.find_element((By.CSS_SELECTOR, parent + r">.btw\:none"))
    btw_util.scroll_into_view(context.driver, element)

    # Rendering can screw up our click... so check that it is where we
    # want it.
    wedutil.click_until_caret_in(util, element)


@when("the user clicks on the end label of the last foreign element")
def step_impl(context):
    driver = context.driver

    # Faster than using 4 Selenium operations.
    button = driver.execute_script("""
    var selector = arguments[0];

    var button = jQuery(selector)[0];
    var parent = button.parentNode;
    var parent_text = jQuery(parent).contents().filter(function() {
       return this.nodeType == Node.TEXT_NODE;
    }).text();
    return button;
    """, ".__end_label._foreign_label:last")

    button.click()


@when("(?:the user )?hits the (?P<choice>right|left) arrow")
def step_impl(context, choice):
    driver = context.driver

    context.caret_position_before_arrow = wedutil.caret_screen_pos(driver)

    key = Keys.ARROW_RIGHT if choice == "right" else Keys.ARROW_LEFT
    ActionChains(driver)\
        .send_keys(key)\
        .perform()
