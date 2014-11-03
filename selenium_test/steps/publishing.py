import requests
# pylint: disable=E0611
from nose.tools import assert_is_not_none, \
    assert_equal
from selenium.webdriver.common.by import By

step_matcher('re')


@when('^the user clicks the button to publish "(?P<name>.*?)"$')
def step_impl(context, name):
    driver = context.driver
    link = driver.execute_script("""
    var lemma = arguments[0];
    var table = document.getElementById("search-table");
    var rows = Array.prototype.slice.call(table.getElementsByTagName("tr"));
    rows = rows.filter(function (x) {
        var links = Array.prototype.slice.call(
            x.querySelectorAll("td:first-of-type>a"));
        return links.filter(function (l) { return l.textContent ===
                                           lemma; })
            .length;
    });
    if (rows.length !== 1)
        return null;
    return rows[0].querySelector("td:nth-of-type(2)>a")
    """, name)

    assert_is_not_none(link, "could not find a button to click")

    link.click()


@then('^there is a message indicating failure to publish$')
def step_impl(context):
    util = context.util

    alert = util.find_element((By.CSS_SELECTOR, ".alert.alert-danger"))
    text = util.get_text_excluding_children(alert).strip()
    assert_equal(text, "This change record cannot be published.")


@then('^there is a message indicating that the article was published$')
def step_impl(context):
    util = context.util

    alert = util.find_element((By.CSS_SELECTOR, ".alert.alert-success"))
    text = util.get_text_excluding_children(alert).strip()
    assert_equal(text, "This change record was published.")


@when('^the article with lemma "foo" can be published$')
def step_impl(context):
    driver = context.driver
    r = requests.get(context.selenic.SERVER +
                     "/lexicography/entry/foo/testing-mark-valid",
                     cookies={
                         "sessionid":
                         driver.get_cookie("sessionid")["value"]
                     })
    assert_equal(r.status_code, 200)
