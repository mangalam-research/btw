step_matcher("re")

@given('the user goes to the page for citing BTW as a whole')
def step_impl(context):
    driver = context.driver
    driver.get(context.builder.SERVER + "/cite")
