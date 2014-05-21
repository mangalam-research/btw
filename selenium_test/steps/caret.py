from selenium.webdriver.common.by import By

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
