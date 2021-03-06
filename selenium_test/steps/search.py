from nose.tools import assert_equal, assert_true  # pylint: disable=E0611


from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from behave import step_matcher  # pylint: disable=E0611

from selenic.util import Result, Condition

step_matcher('re')


@given('the search table is loaded')
def step_impl(context):
    assert_true(context.default_table.wait_for_initialized(),
                "the search table should be initialized")


@when('the user searches for lemma "(?P<query>.*?)"')
def step_impl(context, query):
    dt = context.default_table
    dt.setup_redraw_check()
    dt.call_with_search_field("Lemmata only", lambda x: x.click())
    dt.wait_for_redraw()
    dt.fill_field("Search", query)


@when('the user searches for "(?P<query>.*?)"')
def step_impl(context, query):
    dt = context.default_table
    dt.fill_field("Search", query)


@then(r'the search results show '
      r'(?P<count>one entry|(?:\d+) (?:or more )?entries)(?: for '
      r'"(?P<lemma>.*?)")?.?')
def step_impl(context, count, lemma=None):
    test = "=="
    if count == "one entry":
        count = 1
    elif count.endswith("entries"):
        if "or more" in count:
            test = ">="
        count = int(count.split()[0])
    else:
        raise ValueError("can't parse: " + count)

    driver = context.driver
    if lemma is not None:
        hits = driver.execute_script("""
        var lemma = arguments[0];
        var table = document.getElementById("search-table");
        var links = Array.prototype.slice.call(
          table.getElementsByTagName("a"));
        return links.filter(function (x) { return x.textContent === lemma; });
        """, lemma)
    else:
        hits = driver.find_elements_by_css_selector(
            "#{}>tbody>tr[role='row']".format(context.default_table.cssid))

    if test == "==":
        assert_equal(len(hits), count,
                     "there should be " + str(count) + " results")
    elif test == ">=":
        assert_true(len(hits) >= count,
                    "there should be at least " + str(count) + " results")
    else:
        raise ValueError("unexpected test: " + test)


@then(r'the search results (?P<show>show|do not show) hit details')
def step_impl(context, show):
    hits = context.driver.find_elements_by_css_selector(
        "#{} tr.hits".format(context.default_table.cssid))
    if show == "show":
        assert_true(len(hits) > 0)
    elif show == "do not show":
        assert_equal(len(hits), 0)
    else:
        raise ValueError("unexpected show value: " + show)

@then('the search results show '
      '(?P<kind>published and unpublished|(?:un)?published) entries')
def step_impl(context, kind):
    driver = context.driver
    ret = driver.execute_async_script("""
    var $ = jQuery;
    var kind = arguments[0];
    var cb = arguments[1];
    var table = document.getElementById("search-table");
    var published = false; // Whether we've seen a published entry.
    var unpublished = false; // Whether we've seen an unpublished entry.
    // Records whether we've so far passed the test.
    var test;
    switch(kind) {
    case "published and unpublished":
        // Returns true if we can end the test based on what we already know.
        var finished = function () { return test; };
        // Updates the test.
        var testfn = function () { test = unpublished && published; };
        // The value to return if we've hit the end of the table. If we hit
        // the end of the table before we found both unpublished and published
        // entries, then the test has failed.
        var final_value = false;
        break;
    case "unpublished":
    case "published":
        var finished = function () { return !test; };
        var testfn = (kind === "unpublished") ?
                         function () { test = !published; } :
                         function () { test = !unpublished; };
        // If we hit the end of the table, it means we have only entries
        // of one publication kind so that's a success.
        var final_value = true;
        break;
    }
    testfn();
    function processPage() {
        var rows = table.querySelectorAll("tbody>tr");
        for (var i = 0, row; !finished() && (row = rows[i]); ++i) {
            var cells = row.querySelectorAll("td");
            var status = cells[2].textContent.split(/\s+/, 1)[0];
            switch (status) {
            case "No":
                unpublished = true;
                break;
            case "Yes":
                published = true;
                break;
            default:
                throw new Error("unknown value: " + status);
            }
            testfn();
        }
        if (finished()) {
            cb(test);
            return;
        }

        // Get the next page and process it.
        var next = document.getElementById("search-table_next");
        if (next.classList.contains("disabled")) {
            // Nothing else.
            cb(final_value);
            return;
        }
        $(table).on("draw.dt", function () {
            processPage();
        });
        next.click();
    }
    return processPage();
    """, kind)
    assert_true(ret)


@when('the user switches the search to (?P<kind>(?:un)?published) articles')
def step_impl(context, kind):
    util = context.util
    dt = context.default_table
    dt.setup_redraw_check()
    context.driver.execute_script("""
    var collapse = document.getElementById("advanced-search-collapse");
    if (!collapse.classList.contains("show"))
      document.querySelector("a[href='#advanced-search-collapse']").click();
    """)
    # We have to wait until the element is in ...
    util.find_elements((By.CSS_SELECTOR, "#advanced-search-collapse.show"))

    select = Select(util.find_element((By.CLASS_NAME,
                                       "btw-publication-status")))
    select.select_by_visible_text(kind.capitalize())

    dt.wait_for_redraw()


@when('the user sets the search to search all records')
def step_impl(context):
    util = context.util
    dt = context.default_table
    dt.setup_redraw_check()
    context.driver.execute_script("""
    var collapse = document.getElementById("advanced-search-collapse");
    if (!collapse.classList.contains("show"))
      document.querySelector("a[href='#advanced-search-collapse']").click();
    """)
    # We have to wait until the element is in ...
    util.find_elements((By.CSS_SELECTOR, "#advanced-search-collapse.show"))

    control = util.find_element((By.CLASS_NAME, "btw-search-all-history"))
    control.click()
    dt.wait_for_redraw()


@then('there is (?P<existence>no|a) "(?P<name>.*?)" column visible')
def step_impl(context, existence, name):
    util = context.util

    def check(driver):
        # We must wait until the wrapper is present because the table
        # won't be ready for examination until then.
        ret = driver.execute_script("""
        var name = arguments[0];
        var check_for_existence = arguments[1];
        var ths = document.querySelectorAll(
            "#search-table_wrapper #search-table thead th");
        if (ths.length == 0)
            return [false, "no headings"];

        if (check_for_existence) {
            for (var i = 0, th; (th = ths[i]); ++i) {
                if (th.textContent.trim() === name)
                    return [true, undefined];
            }
            return [false, name + " is not present"];
        }

        for (var i = 0, th; (th = ths[i]); ++i) {
            if (th.textContent.trim() === name)
                return [false, name + " is present"];
        }

        return [true, undefined];
        """, name, existence == "a")

        return Result(ret[0], ret[1])

    result = Condition(util, check).wait()
    assert_true(result, result.payload)


@then('the search box is empty and the lemmata only box is unchecked')
def step_impl(context):
    util = context.util
    driver = context.driver

    def cond(driver):
        controls = driver.find_elements_by_css_selector(
            "#search-table_filter input")
        return Result(len(controls) == 2, controls)

    controls = util.wait(cond).payload

    assert_true(driver.execute_script("""
    return arguments[0].value.length === 0 && !arguments[1].checked;
     """, controls[0], controls[1]))
