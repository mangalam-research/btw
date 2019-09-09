# -*- coding: utf-8 -*-
import requests
import re
import os
import collections

# pylint: disable=E0611
from nose.tools import assert_equal, assert_true


from selenium.webdriver.common.by import By
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from behave import then, when, given, Given, \
    step_matcher  # pylint: disable=E0611
try:
    from django.middleware.csrf import CSRF_TOKEN_LENGTH
except:
    CSRF_TOKEN_LENGTH = 10

import lexicography.tests.funcs as funcs
import wedutil
from selenium_test import btw_util
from selenic.datatables import Datatable

FAKE_CSRF = "x" * CSRF_TOKEN_LENGTH

@when("the user loads the top page of the lexicography app")
def user_load_lexicography(context):
    driver = context.driver
    driver.get(context.builder.SERVER + "/lexicography")
    context.clear_tables()
    dt = Datatable(context.util, "lexicographical search", "search-table")
    context.register_table(dt, True)


@then("the user gets the top page of the lexicography app")
def step_impl(context):
    util = context.util
    util.wait(lambda driver: re.fullmatch(r"^[A-za-z ]+\| Lexicography$",
                                          driver.title))


@given("that the user has loaded the top page of the lexicography app")
def step_impl(context):
    context.execute_steps("""
    When the user loads the top page of the lexicography app
    Then the user gets the top page of the lexicography app
    """)


@given("a new document")
def step_impl(context):
    util = context.util
    driver = context.driver

    context.execute_steps("""
    Given the user has logged in
    """)
    driver.get(context.builder.SERVER + "/lexicography/entry/new")
    btw_util.wait_for_editor(context)

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


@given("wait {x} seconds")
@when("wait {x} seconds")
def step_impl(context, x):
    import time
    time.sleep(float(x))


step_matcher('re')


@given(r'the window is sized so that the table of contents is expandable')
def step_impl(context):
    driver = context.driver
    driver.set_window_size(683, 741)
    context.execute_steps("Then the table of contents is expandable")


@when("(?:the user )?scrolls the editor pane (?P<choice>completely )?down")
def step_impl(context, choice):
    driver = context.driver
    util = context.util

    if choice == "completely ":
        # We must not call it before the body is fully loaded.
        scroll_by = driver.execute_script("""
        return wed_editor.guiRoot.scrollHeight;
        """)
    else:
        scroll_by = 10

    # We must not call it before the body is fully loaded.
    driver.execute_script("""
    var by = arguments[0];
    delete window.__selenic_scrolled;
    jQuery(function () {
      var top = window.wed_editor.$guiRoot.scrollTop();
      window.wed_editor.$guiRoot.scrollTop(top + by);
      window.__selenic_scrolled = true;
    });
    """, scroll_by)

    def cond(*_):
        return driver.execute_script("""
        return window.__selenic_scrolled;
        """)
    util.wait(cond)
    context.scrolled_editor_pane_by = scroll_by

User = collections.namedtuple("User", ["login", "password"])

foo = User("foo", "foo")
foo2 = User("foo2", "foo")

users = {
    "": foo,
    "without permission to edit primary sources": foo2,
    "without permission to create or edit custom semantic fields": foo2,
    "with permission to create custom semantic fields": foo,
    "with permission to edit custom semantic fields": foo,
}


@given(r"(?:the|a) user(?P<user_desc>| (?:without|with) permission to .*?) "
       r"has logged in")
@when(r"the user (?P<user_desc>) logs in")
def step_impl(context, user_desc):
    driver = context.driver
    util = context.util
    selenic = context.builder
    user_desc = user_desc.strip()

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
        context.session_id = driver.get_cookie("sessionid")["value"]
    else:
        driver.get(selenic.SERVER)
        context.server.write("login " + user.login + " " +
                             user.password + "\n")
        session_key = context.server.read()
        driver.add_cookie({'name': 'sessionid', 'value': session_key})
        driver.add_cookie({'name': 'csrftoken', 'value': FAKE_CSRF})
        context.session_id = session_key
        #
        # There is no need to reload the page right here. If a test
        # fails because the page needs reloading after the credential
        # change, then reload the page **THERE**. Having it be
        # reloaded here impacts performance negatively.
        #
        # driver.get(selenic.SERVER)
    context.is_logged_in = True

@when("the user logs out")
def step_impl(context):
    driver = context.driver
    util = context.util
    selenic = context.builder
    logout_url = selenic.SERVER + "/logout"
    driver.get(logout_url)
    button = driver.find_element_by_css_selector("button[type='submit']")
    button.click()

    # We wait until the logout is processed. Otherwise, the next
    # operation may *cancel* the submit we just started.
    util.wait(lambda driver: driver.current_url != logout_url)


WHAT_TO_TITLE = {
    "unpublished": "pali example",
    "a single sense that has a subsense": "one sense, one subsense",
    "a Pāli example": "pali example",
    "a non-Pāli example": "non-pali example",
    ("a non-Pāli example with a bibliographical reference and a link to "
     "the example"): "non-pali example, with ref and ptr",
    "a Pāli example, explained": "pali explained example",
    "a non-Pāli example, explained": "non-pali explained example",
    "a definition that has been filled": "definition filled",
    "a definition with formatted text": "definition with formatted text",
    "senses and subsenses": "senses and subsenses",
    "some semantic fields": "some semantic fields",
    "an antonym with citations": "antonym with citations",
    "a cognate with citations": "cognate with citations",
    "a conceptual proximate with citations":
    "conceptual proximate with citations",
    "senses, subsenses and hyperlinks": "senses, subsenses and hyperlinks",
    "a sense with explanation": "sense with explanation",
    "a sense with citations": "sense with citations",
    "contrastive elements with one child":
    "contrastive elements with one child",
    "one btw:antonyms with one btw:antonym and no btw:none":
    "contrastive elements with one child",
    "one btw:cognates with one btw:cognate and no btw:none":
    "contrastive elements with one child",
    "one btw:conceptual-proximate with one btw:conceptual-proximate "
    "and no btw:none":
    "contrastive elements with one child",
    "an antonym with citations, followed by another antonym":
    "antonym with citations, followed by another antonym",
    "citations everywhere possible (subsense)":
    "citations everywhere possible (subsense)",
    "an empty surname": "empty surname",
    "a missing editor": "empty surname",
    "a missing author": "no author",
    "a specified semantic field": "article with combined fields",
}


href_url_re = re.compile(r'href\s*=\s*"(.*?)"')

@Given(r"(?:a|an) (?P<what>valid|(?:un)?published) document")
@Given(r"a (?P<what>valid article, .*)")
@Given(r"a document with (?P<what>.*?)")
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
            context.execute_steps("""
            Given a new document
            """)

            result = driver.execute_script("""
            var senses =  \
                wed_editor.guiRoot.getElementsByClassName("btw:sense");
            if (senses.length !== 1)
                return [false, "the document should have exactly one sense"];
            var sub = senses[0].getElementsByClassName("btw:subsense");
            if (sub.length !== 0)
                return [false, "the sense should not contain a subsense"];
            return [true, ""];
            """)
            assert_true(result[0], result[1])
            return

        # For editing we must be logged in. If we are just viewing,
        # then it is better to view as a random user that does not
        # have an account on the system.
        context.execute_steps("""
        Given the user has logged in
        """)

    title = None

    if what in ("published", "valid"):
        what = "valid article"
    elif what in ("bad semantic fields", "good semantic fields"):
        what = "valid article, with " + what

    if what == "valid article" or what.startswith("valid article, "):
        if context.created_documents.get(what) is None:
            context.server.write("create " + what + "\n")
            title = context.server.read()
            context.created_documents[what] = title
        else:
            title = context.created_documents[what]

    if title is None:
        title = WHAT_TO_TITLE[what]

    # We simulate an AJAX query on the search table.
    while True:
        r = requests.get(context.builder.SERVER +
                         "/en-us/lexicography/search-table/",
                         params={
                             "length": -1,
                             "search[value]": title,
                             "lemmata_only": "true",
                             "publication_status": "both",
                         },
                         cookies={
                             "sessionid": context.session_id
                         } if context.session_id else None)
        if r.status_code == 200:
            hits = funcs.parse_search_results(r.text)
            if title in hits:
                break

    if edit:
        driver.get(context.builder.SERVER + hits[title]["edit_url"])
        btw_util.wait_for_editor(context)
        btw_util.record_document_features(context)
    else:
        driver.get(context.builder.SERVER + hits[title]["hits"][0]["view_url"])
        # We must ensure jQuery is loaded because the test suite depends on it.
        driver.execute_async_script("""
        var done = arguments[0];
        require(["jquery"], function () {
            done();
        });
        """)


@Given("a document that has no (?P<what>.*)")
def step_impl(context, what):
    driver = context.driver
    context.execute_steps("""
    Given a document with a single sense
    """)

    # Make a CSS selector out of it
    what = "." + what.replace(":", r"\:")
    els = driver.find_elements_by_css_selector(what)

    assert_equal(len(els), 0)


@Given("the document has no (?P<what>.*)")
def step_impl(context, what):
    driver = context.driver
    # Make a CSS selector out of it
    what = "." + what.replace(":", r"\:")
    els = driver.find_elements_by_css_selector(what)

    assert_equal(len(els), 0)


@When('the user saves the file'
      '(?P<how> using the keyboard| using the toolbar)?')
def step_impl(context, how=None):
    driver = context.driver
    util = context.util

    # We have to wait for the save to happen before moving on.
    driver.execute_script("""
    window.__selenium_saved = false;
    // Loading operators here is a bit onerous so we do the logic
    // manually instead of using first(), etc.
    var subscription = wed_editor.saver.events
      .subscribe(function (ev) {
      // Yes, we handle both the same.
      if (!(ev.name === "Failed" || ev.name === "Saved")) {
        return;
      }
      window.__selenium_saved = true;
      subscription.unsubscribe();
    });
    """)
    if how is None or how == " using the keyboard":
        util.ctrl_equivalent_x("s")
    else:
        context.execute_steps("""
        When the user clicks the save button in the toolbar
        """)

    util.wait(lambda driver: driver.execute_script(
        "return window.__selenium_saved"))


@When("the user reloads the file")
def step_impl(context):
    driver = context.driver

    driver.execute_script("""
    // Overwrite onbeforeunload to prevent the dialog from showing up.
    if (window.wed_editor)
        window.onbeforeunload = function () {};
    """)
    driver.get(driver.current_url)
    btw_util.wait_for_editor(context)


@When("the user reloads the page")
def step_impl(context):
    driver = context.driver

    driver.execute_script("""
    // Overwrite onbeforeunload to prevent the dialog from showing up.
    if (window.wed_editor)
        window.onbeforeunload = function () {};
    """)
    driver.get(driver.current_url)

@when(r"the user clicks the (?P<what>save|quit without saving) button "
      r"in the toolbar")
def step_impl(context, what):
    what = {
        "save": "Save",
        "quit without saving": "Quit without saving"
    }[what]
    button = context.driver.find_element_by_css_selector(
        ".wed-toolbar "
        ".btn[data-original-title='{0}']".format(what))
    button.click()


@when('someone else modifies the file')
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


@then('the user gets a dialog that the file has been modified by '
      'another user')
def step_impl(context):
    header = context.util.find_element((By.CSS_SELECTOR,
                                        ".modal.show .modal-header h5"))
    assert_equal(header.text, "Edited by another!")


@then('the editor is present')
def step_impl(context):
    # This is deliberately brief. This should be used on a page where
    # some work has already been done with the editor. We're just
    # checking that we are still there.
    assert_true(context.driver.execute_script(
        "return window.wed_editor !== undefined"))


@when(r'the user clicks the button named "(?P<name>.*?)"')
def step_impl(context, name):
    path = ("//*[(self::a or self::button) and "
            "(normalize-space(text()) = '{0}')]").format(name)
    button = context.driver.find_element_by_xpath(path)
    button.click()


@when(r'the button named "(?P<name>.*?)" is enabled')
def step_impl(context, name):
    button = context.driver.find_element_by_link_text(name)
    assert_true(button.is_enabled())


@then(r'there is a modal dialog titled "(?P<name>.*?)" visible')
def step_impl(context, name):
    util = context.util

    modal = util.wait(
        EC.visibility_of_element_located((By.CSS_SELECTOR,
                                          ".modal.show")))

    assert_equal(modal.find_element_by_class_name("modal-title").text,
                 name)

@given(r'there is a network slowdown')
def step_impl(context):
    with open("sitestatic/LIMIT", 'w'):
        pass

@given(r'the network slowdown is over')
def step_impl(context):
    os.unlink("sitestatic/LIMIT")

@when(r'fail')
@then(r'fail')
def step_impl(context):
    raise Exception("failing, as requested!")

@when(r'the user clicks on the "(?P<what>.*?)" button in the modal dialog')
def step_impl(context, what):
    util = context.util

    # Searching by class in XPath sucks, and searching by text with a
    # CSS selector sucks too. So here we are.
    modal = util.find_element((By.CSS_SELECTOR, ".modal.show .modal-footer"))
    button = modal.find_element_by_link_text(what)
    button.click()
    util.wait(lambda driver:
              len(driver.find_elements(By.CSS_SELECTOR, ".modal.show")) == 0)

@when(r'the user dismisses the modal by using the close button in the '
      r'modal header')
def step_impl(context):
    util = context.util

    button = util.find_element((By.CSS_SELECTOR,
                                ".modal.show .modal-header .close"))
    button.click()
