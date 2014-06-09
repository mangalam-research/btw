from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

import wedutil

step_matcher('re')


@when(r"^the user clicks on the btw:none element of (?P<parent>.*)$")
def step_impl(context, parent):

    parent = "." + parent.replace(":", r"\:")
    element = context.util.find_element((By.CSS_SELECTOR,
                                         parent + r">.btw\:none"))
    element.click()


@when(u"^the user clicks on the end label of the last foreign element$")
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


@when(u"^(?:the user )?hits the (?P<choice>right|left) arrow$")
def step_impl(context, choice):
    driver = context.driver

    context.caret_position_before_arrow = wedutil.caret_pos(driver)

    key = Keys.ARROW_RIGHT if choice == "right" else Keys.ARROW_LEFT
    ActionChains(driver)\
        .send_keys(key)\
        .perform()
