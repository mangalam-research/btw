import requests
# pylint: disable=E0611
from nose.tools import assert_is_not_none, \
    assert_equal, assert_true
from selenium.webdriver.common.by import By

step_matcher('re')


@when(r'the user clicks the button to (?P<action>publish|unpublish) '
      r'"(?P<name>.*?)"')
def step_impl(context, action, name):
    util = context.util

    def cond(driver):
        link, text = driver.execute_script("""
        var lemma = arguments[0];
        var table = document.getElementById("search-table");
        var rows = Array.prototype.slice.call(
            table.getElementsByTagName("tr"));
        rows = rows.filter(function (x) {
            var links = Array.prototype.slice.call(
                x.querySelectorAll("td:first-of-type>a"));
            return links.filter(function (l) { return l.textContent ===
                                               lemma; })
                .length;
        });
        if (rows.length !== 1)
            return null;
        var link = rows[0].querySelector("td:nth-of-type(3)>a");
        return [link, link && link.textContent];
        """, name)

        if link is None:
            return False

        # This effectively returns link if the action is what we expect.
        return (text == ("Publish" if action == "publish" else "Unpublish")) \
            and link

    link = util.wait(cond)

    link.click()


@then('there is a message indicating failure to publish')
def step_impl(context):
    util = context.util

    alert = util.find_element((By.CSS_SELECTOR, ".alert.alert-danger"))
    text = util.get_text_excluding_children(alert).strip()
    assert_equal(text, "This change record cannot be published.")


@when('the user dismisses the message')
def step_impl(context):
    util = context.util

    alert_button = util.find_element((By.CSS_SELECTOR, ".alert button"))
    alert_button.click()
    util.wait_until_not(lambda driver: len(driver.find_elements(
        (By.CSS_SELECTOR, ".alert"))) != 0)


@then(r'there is a message indicating that the article was '
      r'(?P<action>published|unpublished)')
def step_impl(context, action):
    util = context.util

    alert = util.find_element((By.CSS_SELECTOR, ".alert.alert-success"))
    text = util.get_text_excluding_children(alert).strip()
    assert_equal(text, "This change record was {0}.".format(action))


@when('the article with lemma "(?P<lemma>.*?)" can be published')
def step_impl(context, lemma):
    driver = context.driver
    r = requests.get(context.builder.SERVER +
                     "/lexicography/entry/{}/testing-mark-valid".format(lemma),
                     cookies={
                         "sessionid":
                         driver.get_cookie("sessionid")["value"]
                     })
    assert_equal(r.status_code, 200)

@then('there is a warning dialog about unpublishing')
def step_impl(context):
    util = context.util

    modal = util.find_element((By.CSS_SELECTOR, ".modal-body"))
    assert_true(modal.is_displayed(), "the modal should be displayed")
    assert_true(modal.text.startswith("Unpublishing should be done"),
                "the modal should be about unpublishing")


@when(r'the user cancels the dialog')
def step_impl(context):
    util = context.util

    button = util.find_element((By.XPATH, "//a[text()='Cancel']"))
    button.click()
    util.wait_until_not(lambda driver:
                        len(driver.find_elements(
                            (By.CSS_SELECTOR, ".modal-body"))) != 0)


@when(r'the user clicks the dialog button that performs the unpublishing')
def step_impl(context):
    util = context.util

    button = util.find_element(
        (By.XPATH, "//a[normalize-space(text())='Yes, I want to unpublish']"))
    button.click()
    util.wait_until_not(lambda driver:
                        len(driver.find_elements(
                            (By.CSS_SELECTOR, ".modal-body"))) != 0)
