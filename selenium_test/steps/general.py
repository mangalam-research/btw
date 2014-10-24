# -*- coding: utf-8 -*-
import requests
import re
import os
import urllib
# pylint: disable=E0611
from nose.tools import assert_equal, assert_raises, \
    assert_true


from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from behave import then, when, given, Given, \
    step_matcher  # pylint: disable=E0611
from selenium.common.exceptions import NoSuchElementException

import lexicography.tests.funcs as funcs
import wedutil
from selenium_test import btw_util


@when("the user loads the top page of the lexicography app")
def user_load_lexicography(context):
    driver = context.driver
    driver.get(context.selenic.SERVER + "/lexicography")


@then("the user gets the top page of the lexicography app")
def step_impl(context):
    driver = context.driver
    assert_equal(driver.title, "BTW | Lexicography")


@given("that the user has loaded the top page of the lexicography app")
def step_impl(context):
    context.execute_steps(u"""
    When the user loads the top page of the lexicography app
    Then the user gets the top page of the lexicography app
    """)


def setup_editor(context):
    util = context.util
    driver = context.driver

    wedutil.wait_for_editor(util)

    # Turning off tooltips makes the tests much easier to handle.
    driver.execute_script("""
    // Turn off tooltips
    wed_editor.preferences.set("tooltips", false);

    // Delete all tooltips.
    jQuery(".tooltip").remove();
    """)


@given("a new document")
def step_impl(context):
    util = context.util
    driver = context.driver

    context.execute_steps(u"""
    Given the user has logged in
    """)
    driver.get(context.selenic.SERVER + "/lexicography/entry/new")
    setup_editor(context)

    btw_util.record_document_features(context)


@given("a context menu is not visible")
@then("a context menu is not visible")
def context_menu_is_not_visible(context):
    wedutil.wait_until_a_context_menu_is_not_visible(context.util)


@when('the user resizes the window so that the editor pane has a vertical '
      'scrollbar')
def step_impl(context):
    util = context.util
    wedutil.set_window_size(util, 683, 741)


@when("the user scrolls the window down")
def step_impl(context):
    driver = context.driver
    util = context.util

    # We must not call it before the body is fully loaded.
    driver.execute_script("""
    delete window.__selenic_scrolled;
    jQuery(function () {
      window.scrollTo(0, document.body.scrollHeight);
      window.__selenic_scrolled = true;
    });
    """)

    def cond(*_):
        return driver.execute_script("""
        return window.__selenic_scrolled;
        """)
    util.wait(cond)

    context.window_scroll_top = util.window_scroll_top()
    context.window_scroll_left = util.window_scroll_left()


@given(u"wait {x} seconds")
@when(u"wait {x} seconds")
def step_impl(context, x):
    import time
    time.sleep(float(x))


step_matcher('re')


@when("^(?:the user )?scrolls the editor pane (?P<choice>completely )?down$")
def step_impl(context, choice):
    driver = context.driver
    util = context.util

    if choice == "completely ":
        # We must not call it before the body is fully loaded.
        scroll_by = driver.execute_script("""
        return wed_editor.gui_root.scrollHeight;
        """)
    else:
        scroll_by = 10

    # We must not call it before the body is fully loaded.
    driver.execute_script("""
    var by = arguments[0];
    delete window.__selenic_scrolled;
    jQuery(function () {
      var top = window.wed_editor.$gui_root.scrollTop();
      window.wed_editor.$gui_root.scrollTop(top + by);
      window.__selenic_scrolled = true;
    });
    """, scroll_by)

    def cond(*_):
        return driver.execute_script("""
        return window.__selenic_scrolled;
        """)
    util.wait(cond)
    context.scrolled_editor_pane_by = scroll_by

import collections

User = collections.namedtuple("User", ["login", "password"])

users = {
    "the user": User("foo", "foo"),
    "a user without permission to edit primary sources": User("foo2", "foo")
}


@given(ur"^(?P<user_desc>the user|a user without permission to edit "
       ur"primary sources) has logged in$")
@when(ur"^(?P<user_desc>the user) logs in$")
def step_impl(context, user_desc):
    driver = context.driver
    util = context.util
    selenic = context.selenic

    user = users[user_desc]
    if not util.can_set_cookies:
        if context.is_logged_in:
            # Log out first...
            driver.get(selenic.SERVER + "/logout")
            button = driver.find_element_by_css_selector(
                "button[type='submit']")
            button.click()

        driver.get(selenic.SERVER + "/login")
        name = util.find_element((By.NAME, "login"))
        pw = util.find_element((By.NAME, "password"))
        form = util.find_element((By.TAG_NAME, "form"))

        ActionChains(driver) \
            .click(name) \
            .send_keys(user.login) \
            .click(pw) \
            .send_keys(user.password) \
            .perform()

        form.submit()
    else:
        driver.get(selenic.SERVER)
        with open(context.server_write_fifo, 'w') as fifo:
            fifo.write("login " + user.login + " " + user.password + "\n")
        with open(context.server_read_fifo, 'r') as fifo:
            session_key = fifo.read().strip()
            driver.add_cookie({'name': 'sessionid',
                               'value': session_key})
            driver.add_cookie({'name': 'csrftoken',
                               'value': 'foo'})
        driver.get(selenic.SERVER)
    context.is_logged_in = True

@when("^the user logs out$")
def step_impl(context):
    driver = context.driver
    selenic = context.selenic
    driver.get(selenic.SERVER + "/logout")
    button = driver.find_element_by_css_selector("button[type='submit']")
    button.click()


WHAT_TO_TITLE = {
    u"a single sense that has a subsense": "one sense, one subsense",
    u"a Pāli example": "pali example",
    u"a non-Pāli example": "non-pali example",
    (u"a non-Pāli example with a bibliographical reference and a link to "
     u"the example"): "non-pali example, with ref and ptr",
    u"a Pāli example, explained": "pali explained example",
    u"a non-Pāli example, explained": "non-pali explained example",
    u"a definition that has been filled": "definition filled",
    u"a definition with formatted text": "definition with formatted text",
    u"senses and subsenses": "senses and subsenses",
    u"some semantic fields": "some semantic fields",
    u"an antonym with citations": "antonym with citations",
    u"a cognate with citations": "cognate with citations",
    u"a conceptual proximate with citations":
    "conceptual proximate with citations",
    u"senses, subsenses and hyperlinks": "senses, subsenses and hyperlinks",
    u"a sense with explanation": "sense with explanation",
    u"a sense with citations": "sense with citations",
    u"one btw:antonyms with one btw:antonym and no btw:none":
    "contrastive elements with one child",
    u"one btw:cognates with one btw:cognate and no btw:none":
    "contrastive elements with one child",
    u"one btw:conceptual-proximate with one btw:conceptual-proximate "
    u"and no btw:none":
    "contrastive elements with one child",
    u"an antonym with citations, followed by another antonym":
    u"antonym with citations, followed by another antonym"
}


href_url_re = re.compile(r'href\s*=\s*"(.*?)"')

@Given(ur"^(?P<what>a valid document)$")
@Given(ur"^a document with (?P<what>.*?)$")
def step_impl(context, what):
    feature = context.feature
    util = context.util
    driver = context.driver

    # This step will work differently depending whether it executed
    # from a feature named "view" or "view_structure", or not. In the
    # former case, it is assumed that the user only wants to view the
    # document. In the later case, it is assumed that the user wants
    # to edit the document.
    name = os.path.splitext(os.path.basename(feature.filename))[0]
    edit = name not in ("view", "view_structure")

    if edit:
        if what in ("a single sense",
                    "a single sense that does not have a subsense"):
            context.execute_steps(u"""
            Given a new document
            """)

            sense = util.find_element((By.CSS_SELECTOR, r".btw\:sense"))
            assert_raises(NoSuchElementException,
                          sense.find_element,
                          (By.CSS_SELECTOR, r".btw\:subsense"))
            return

        # For editing we must be logged in. If we are just viewing,
        # then it is better to view as a random user that does not
        # have an account on the system.
        context.execute_steps(u"""
        Given the user has logged in
        """)

    title = None
    if what == "a valid document" and not context.valid_document_created:
        with open(context.server_write_fifo, 'w') as fifo:
            fifo.write("create valid article\n")
        with open(context.server_read_fifo, 'r') as fifo:
            title = fifo.read().strip().decode('utf-8')
        context.valid_document_created = True

    if title is None:
        title = WHAT_TO_TITLE[what]

    # We simulate an AJAX query on the search table.
    while True:
        r = requests.get(context.selenic.SERVER +
                         "/lexicography/search-table/",
                         params={
                             "length": -1,
                             "search[value]": title,
                             "headwords_only": "true",
                             "publication_status": "both",
                         },
                         cookies={
                             "sessionid":
                             driver.get_cookie("sessionid")["value"]
                         } if edit else None)

        hits = funcs.parse_search_results(r.text)
        if title in hits:
            break

    if edit:
        driver.get(context.selenic.SERVER + hits[title]["edit_url"])
        setup_editor(context)
        btw_util.record_document_features(context)
    else:
        driver.get(context.selenic.SERVER + hits[title]["hits"][0]["view_url"])
        # We must ensure jQuery is loaded because the test suite depends on it.
        driver.execute_async_script("""
        var done = arguments[0];
        require(["jquery"], function () {
            done();
        });
        """)


@Given("^a document that has no (?P<what>.*)$")
def step_impl(context, what):
    driver = context.driver
    context.execute_steps(u"""
    Given a document with a single sense
    """)

    # Make a CSS selector out of it
    what = "." + what.replace(":", r"\:")
    els = driver.find_elements_by_css_selector(what)

    assert_equal(len(els), 0)


@Given("^the document has no (?P<what>.*)$")
def step_impl(context, what):
    driver = context.driver
    # Make a CSS selector out of it
    what = "." + what.replace(":", r"\:")
    els = driver.find_elements_by_css_selector(what)

    assert_equal(len(els), 0)


@When('^the user saves the file'
      '(?P<how> using the keyboard| using the toolbar)?$')
def step_impl(context, how=None):
    driver = context.driver
    util = context.util

    # We have to wait for the save to happen before moving on.
    driver.execute_script("""
    window.__selenium_saved = false;
    wed_editor._saver.addOneTimeEventListener("saved", function () {
        window.__selenium_saved = true;
    });
    wed_editor._saver.addOneTimeEventListener("failed", function () {
        // Yes, we do the same thing.
        window.__selenium_saved = true;
    });
    """)
    if how is None or how == " using the keyboard":
        util.ctrl_equivalent_x("S")
    else:
        context.execute_steps(u"""
        When the user clicks the save button in the toolbar
        """)

    util.wait(lambda driver: driver.execute_script(
        "return window.__selenium_saved"))


@When("^the user reloads the file$")
def step_impl(context):
    driver = context.driver

    driver.execute_script("""
    // Overwrite onbeforeunload to prevent the dialog from showing up.
    if (window.wed_editor)
        window.onbeforeunload = function () {};
    """)
    driver.get(driver.current_url)
    setup_editor(context)


@when(ur"^the user clicks the (?P<what>save) button in the toolbar$")
def step_impl(context, what):
    button = context.driver.execute_script(u"""
    return jQuery("#toolbar .btn[name='{0}']")[0];
    """.format(what))
    button.click()


@when('^someone else modifies the file$')
def step_impl(context, how=None):
    driver = context.driver
    util = context.util

    url = driver.current_url
    assert_true(url.endswith("/update"))
    url = url[:-6] + "mod"

    driver.execute_script("""
    var url = arguments[0];
    var $ = jQuery;
    window.__btw_test_waiting_for_mod = true;
    $.ajax({
        type: "GET",
        url: url
    }).done(function () {
      delete window.__btw_test_waiting_for_mod;
    }).fail(function (jqXHR, textStatus, errorThrown) {
      window.selenium_log = [textStatus, errorThrown];
    });
    """, url)

    # We have to wait for the save to happen before moving on.
    util.wait(lambda driver: driver.execute_script(
        "return !window.__btw_test_waiting_for_mod"))


@then('^the user gets a dialog that the file has been modified by '
      'another user$')
def step_impl(context):
    header = context.util.find_element((By.CSS_SELECTOR,
                                        ".modal.in .modal-header h3"))
    assert_equal(header.text, "Edited by another!")
