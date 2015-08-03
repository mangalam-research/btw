# -*- encoding: utf-8 -*-
import collections

# pylint: disable=no-name-in-module
from behave import given, then, when, step_matcher
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains

from nose.tools import assert_equal

step_matcher('re')

COLUMNS = {
    "buttons": 0,
    "creators": 1,
    "original titles": 2,
    "dates": 3
}

SUBCOLUMNS = {
    "buttons": 0,
    "reference_title": 1,
    "genre": 2
}

NUMBER_OF_ROWS = 3

load_re = ur'(?:that )?the user (?:is on|reloads) the page for '\
          ur'(?:editing primary sources|managing bibliographical items)'


@given(load_re)
@when(load_re)
def step_impl(context):
    driver = context.driver
    driver.get(context.builder.SERVER + "/bibliography/manage/")


title_re = ur'(?:that )?the items are sorted by ' \
           ur'(?P<order>ascending|descending) ' \
           ur'(?P<what>creators|dates|original titles)\.?'
Order = collections.namedtuple('Order', ('op', 'class_'))
ORDERS = {
    "descending": Order(lambda a, b: a > b, 'sorting_desc'),
    "ascending": Order(lambda a, b: a < b, 'sorting_asc')
}


@given(title_re)
@then(title_re)
def step_impl(context, order, what):
    driver = context.driver
    util = context.util
    column = COLUMNS[what]
    op = ORDERS[order].op

    def cond(*_):

        cells = driver.execute_script("""
        if (typeof jQuery === "undefined")
            return false;

        var colno = arguments[0];
        var class_ = arguments[1];
        var number_of_rows = arguments[2];

        var $ = jQuery;
        var $table = $("#bibliography-table");
        var $header = $table.find("thead>tr").first().find("th").eq(colno);
        if (!$header[0] || !$header[0].classList.contains(class_))
            return false;

        var $rows = $table.find("tbody>tr");
        if ($rows.length != number_of_rows)
            return false;

        var cells = [];
        for(var i = 0, limit = $rows.length; i < limit; ++i) {
            var $row = $rows.eq(i);
            cells.push($row.children("td").eq(colno).text());
        }

        return cells;
        """, column, ORDERS[order].class_, NUMBER_OF_ROWS)

        if not cells:
            return False

        for i in xrange(0, len(cells) - 1):
            if not op(cells[i], cells[i + 1]):
                return False

        return True

    util.wait(cond)


@when(ur'the user clicks on the icon for sorting '
      ur'(?P<what>creators|dates|original titles)')
def step_impl(context, what):
    util = context.util
    column = COLUMNS[what]

    header = util.find_element((
        By.XPATH,
        "//table[@id='bibliography-table']/thead/tr[1]/th[{0}]".format(
            column + 1)))
    header.click()


@when(ur'the user clicks on the button to add a primary source of row '
      ur'(?P<row_n>\d+)')
def step_impl(context, row_n):
    util = context.util
    column = COLUMNS["buttons"]

    def cond(driver):
        try:
            button = driver.execute_script("""
            var row = arguments[0];
            var column = arguments[1];
            var proc = document.getElementById(
                "bibliography-table_processing");

            // Still processing...
            if (proc.style.display !== "none")
                return undefined;
            return jQuery("table#bibliography-table>tbody>tr")
                .filter(".odd, .even").eq(row).children("td")
                .eq(column).children("div.add-button")[0];

            """, int(row_n), column)

            if button is None:
                return False

            ActionChains(driver) \
                .click(button) \
                .perform()
            return True
        except StaleElementReferenceException:
            return False

    util.wait(cond)


@when(ur'the user submits the dialog with reference title of '
      ur'"(?P<title>.*?)" and a genre of "(?P<genre>.*?)"')
def step_impl(context, title, genre):
    driver = context.driver
    util = context.util

    def fill(*_):
        return driver.execute_script("""
        var title = arguments[0];
        var genre = arguments[1];
        var $ = jQuery;
        var $form = $(".primary-source-form");
        if (!$form.parents(".modal.in")[0])
            return false;
        $form.find("textarea[name='reference_title']")[0].value
            = title;
        var $select = $form.find("select[name='genre']");
        var $option = $select.find("option:contains('" + genre + "')");
        $select[0].value = $option[0].value;
        $form.parents(".modal").first().find(".btn-primary").click();
        return true;
        """, title, genre)

    util.wait(fill)


@then(ur"the modal dialog to add a primary source (?:comes up|is visible)")
def step_impl(context):
    context.util.find_element((By.CLASS_NAME, "primary-source-form"))


@then(ur"the modal dialog to add a primary source disappears")
def step_impl(context):
    util = context.util

    def cond(driver):
        return driver.execute_script("""
        return !jQuery(".primary-source-form").parents(".modal.in")[0];
        """)

    util.wait(cond)


@then(ur'the modal dialog shows the error "(?P<error>.*?)" for the '
      'reference title field')
def step_impl(context, error):
    util = context.util

    def cond(driver):
        return driver.execute_script("""
        var error = arguments[0];
        var $ = jQuery;
        var $msg = $(".primary-source-form *[name='reference_title']")
            .next(".error-msg");
        return $msg.text() === error;
        """, error)

    util.wait(cond)


@then(ur"row (?P<row>\d+) shows there (?:are|is) (?P<sources>\d+) "
      ur"primary sources?")
def step_impl(context, row, sources):
    util = context.util

    def cond(driver):
        try:
            text = driver.execute_script("""
            var row = arguments[0];
            return jQuery("table#bibliography-table>tbody>tr")
                       .eq(row).find(".primary-source-count").text();
            """, row)
            return text == (sources if int(sources) > 0 else "")
        except StaleElementReferenceException:
            return False

    util.wait(cond)


@then(ur'row (?P<row>\d+) shows a primary source in subtable row '
      ur'(?P<subrow>\d+) with reference title of '
      ur'"(?P<title>.*?)" and a genre of "(?P<genre>.*?)"')
def step_impl(context, row, subrow, title, genre):
    util = context.util

    context.execute_steps(u"""
    When the user opens row {0}
    """.format(row))

    def cond(driver):
        ret = driver.execute_script("""
        var row = arguments[0];
        var subrow = arguments[1];
        var title = arguments[2];
        var genre = arguments[3];
        var SUBCOLUMNS = arguments[4];
        var $ = jQuery;
        var $row = $("table#bibliography-table>tbody>tr")
            .filter(".odd, .even").eq(row).next();
        var $subtable = $row.find("table");
        if (!$subtable[0])
            return "no subtable";

        var $subrow = $subtable.find("tbody>tr").eq(subrow);
        if (!$subrow[0])
            return "no subrow";

        var $title = $subrow.find("td").eq(SUBCOLUMNS["reference_title"]);
        if ($title.text() !== title)
            return "title differs";

        var $genre = $subrow.find("td").eq(SUBCOLUMNS["genre"]);
        if ($genre.text() !== genre)
            return "genre differs";

        return 1;
        """, int(row), int(subrow), title, genre, SUBCOLUMNS)
        return ret == 1

    util.wait(cond)


@then(ur'row (?P<row>\d+) shows a subtable that has (?P<num>\d+) row')
def step_impl(context, row, num):
    util = context.util

    context.execute_steps(u"""
    When the user opens row {0}
    """.format(row))

    def cond(driver):
        ret = driver.execute_script("""
        var row = arguments[0];
        var num = arguments[1];
        var $ = jQuery;
        var $row = $("table#bibliography-table>tbody>tr")
            .filter(".odd, .even").eq(row).next();
        var $subtable = $row.find("table");
        if (!$subtable[0])
            return "no subtable";

        if ($subtable.find("tbody>tr").length !== num)
            return "bad length";

        return 1
        """, int(row), int(num))
        return ret == 1

    util.wait(cond)


def desired_row_state(driver, row, state):
    ret = driver.execute_script("""
    var row = arguments[0];
    var $next = jQuery("table#bibliography-table>tbody>tr")
    .filter(".odd, .even").eq(row).next();
    if (!$next[0] || $next.is(".odd, .even"))
        return false;
    var $proc = $next.find("div.dataTables_processing");
    // If it is not present, the table is not even initialized.
    if (!$proc[0])
        return false;
    return ($proc[0].style.display === "none");
    """, int(row))
    return ret if state == "open" else not ret


@when(ur'the user (?P<action>opens|closes) row (?P<row>\d+)')
def step_impl(context, action, row):
    util = context.util
    column = COLUMNS["buttons"]

    desired_state = "open" if action == "opens" else "closed"
    # We are already in the desired state
    if desired_row_state(context.driver, row, desired_state):
        return

    def button_clicked(driver):
        try:
            button = driver.execute_script("""
            var row = arguments[0];
            var column = arguments[1];

            var proc = document.getElementById(
                "bibliography-table_processing");

            // Not ready (i.e. element does not exist yet) or still
            // processing...
            if (!proc || proc.style.display !== "none")
                return undefined;

            return jQuery("table#bibliography-table>tbody>tr")
                       .filter(".odd, .even").eq(row).children("td")
                       .eq(column).children("div.open-close-button")[0];
            """, int(row), column)
            button.click()
            return True
        except StaleElementReferenceException:
            return False

    util.wait(button_clicked)

    util.wait(lambda driver: desired_row_state(driver, row, desired_state))


@then(ur'row (?P<row>\d+) is (?P<state>open|closed)')
def step_impl(context, row, state):
    util = context.util
    column = COLUMNS["buttons"]

    util.wait(lambda driver: desired_row_state(driver, row, state))


@when(ur'the user (?P<action>opens|closes) all rows')
def step_impl(context, action):
    util = context.util
    column = COLUMNS["buttons"]

    def button_clicked(driver):
        try:
            button = driver.execute_script("""
            var column = arguments[0];
            var button_index = arguments[1];

            var proc = document.getElementById(
                "bibliography-table_processing");

            // Not ready or still processing...
            if (!proc || proc.style.display !== "none")
                return undefined;

            return jQuery("table#bibliography-table>thead>tr>th")
                       .eq(column).children("div.btn")
                       .eq(button_index)[0];
            """, column, 0 if action == "closes" else 1)

            if button is None:
                return False

            button.click()
            return True
        except StaleElementReferenceException:
            return False

    util.wait(button_clicked)


@when(ur'the user enters "(?P<text>.*?)" in the reference title field')
def step_impl(context, text):
    context.driver.execute_script("""
    var text = arguments[0];
    jQuery(".primary-source-form textarea[name='reference_title']")[0].value
        = text;
    """, text)


@when(ur'the user sets the genre to "(?P<value>.*?)"')
def step_impl(context, value):
    context.driver.execute_script("""
    var value = arguments[0];
    var $select = jQuery(".primary-source-form select[name='genre']");
    var $option = $select.find("option:contains('" + value + "')");
    $select[0].value = $option[0].value;
    """, value)


@when(ur'the user clicks on the button to edit the first primary source of '
      ur'row (?P<row>\d+)')
def step_impl(context, row):
    util = context.util

    context.execute_steps(u"""
    When the user opens row {0}
    """.format(row))

    def cond(driver):
        ret = driver.execute_script("""
        var row = arguments[0];
        var subrow = arguments[1];
        var button_subcolumn = arguments[2];
        var $ = jQuery;
        var $row = $("table#bibliography-table>tbody>tr").eq(row + 1);
        var $subtable = $row.find("table");
        if (!$subtable[0])
            return "no subtable";

        var $subrow = $subtable.find("tbody>tr").eq(subrow);
        if (!$subrow[0])
            return "no subrow";

        return $subrow.find("td").eq(button_subcolumn).find(".btn").first()[0];
        """, int(row), 0, SUBCOLUMNS["buttons"])
        return ret if isinstance(ret, WebElement) else False

    button = util.wait(cond)
    button.click()


@given("all rows are loaded\.?")
def step_impl(context):
    context.execute_steps(u"""
    Given there are {0} rows.
    """.format(NUMBER_OF_ROWS))

rows_re = ur'there (?:is|are) (?P<number>\d+) rows?\.?'


def wait_until_datatable_has_n_rows(util, selector_or_element, number):
    def cond(driver):
        return driver.execute_script("""
        if (typeof jQuery === "undefined")
            return false;

        var selector = arguments[0];
        var no = arguments[1];

        var $ = jQuery;
        var $rows = $(selector);

        // When there are no records, the table contains a single row
        // that states so.
        if (no === 0)
            return $rows.text() === "No matching records found";

        if ($rows.length !== no)
            return false;

        if (no === 1)
            return $rows.text() !== "No matching records found";

        return true;
        """, selector_or_element, number)
    util.wait(cond)


@given(rows_re)
@then(rows_re)
def step_impl(context, number):
    number = int(number)
    util = context.util
    wait_until_datatable_has_n_rows(util, "#bibliography-table>tbody>tr",
                                    number)


@when(ur'the user clicks on the filtering field')
def step_impl(context):
    util = context.util
    field = util.find_element((By.CSS_SELECTOR,
                               "input[aria-controls='bibliography-table']"))
    field.click()


@then(ur'there are no buttons for adding primary sources')
def step_impl(context):
    driver = context.driver

    assert_equal(len(driver.find_elements_by_css_selector(
        "table#bibliography-table>tbody>tr div.add-button")), 0)


@then(ur'there are no buttons for editing primary sources')
def step_impl(context):
    # This test is hardcoded to check only in the first subtable and
    # expect the subtable to have only one row.
    util = context.util
    driver = context.driver

    def cond(driver):
        return driver.execute_script("""
        return jQuery("table#bibliography-table>tbody>tr")
            .filter(".odd, .even").eq(0).next().find("table")[0];
        """)

    subtable = util.wait(cond)
    wait_until_datatable_has_n_rows(util, subtable, 1)

    assert_equal(len(driver.find_elements_by_css_selector(
        "table#bibliography-table>tbody>tr div.edit-button")), 0)


@when(ur'the user selects the menu to show 25 entries')
def step_impl(context):
    driver = context.driver
    driver.execute_async_script("""
    var done = arguments[0];
    var $ = jQuery;
    var table = document.getElementById("bibliography-table");
    // We wait until the results have refreshed.
    $(table).one("refresh-results", function () {
        done();
    });
    // Switch to a 25 row display.
    var select = document.querySelector(
        "select[name='bibliography-table_length']");
    select.value = 25;
    // Must trigger the event manually...
    $(select).change();
    """)
