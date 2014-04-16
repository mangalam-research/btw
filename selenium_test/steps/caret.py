from selenium.webdriver.common.by import By

step_matcher('re')


@when(r"^the user clicks on the btw:none element of (?P<parent>.*)$")
def step_impl(context, parent):

    parent = "." + parent.replace(":", r"\:")
    element = context.util.find_element((By.CSS_SELECTOR,
                                         parent + r">.btw\:none"))
    element.click()
