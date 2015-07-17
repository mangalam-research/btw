from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from behave import step_matcher

step_matcher("re")


@when(ur'the user types "(?P<text>.*?)"')
def step_impl(context, text):
    driver = context.driver
    ActionChains(driver)\
        .send_keys(text)\
        .perform()


@when(ur'the user types (?P<choice>ENTER|ESCAPE|DELETE|BACKSPACE)')
def step_impl(context, choice):
    driver = context.driver
    key = getattr(Keys, choice)
    ActionChains(driver)\
        .send_keys(key)\
        .perform()
