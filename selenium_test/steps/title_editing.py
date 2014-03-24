import collections

# pylint: disable=no-name-in-module
from behave import given, then, when, step_matcher
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

step_matcher('re')

COLUMNS = {
    "title for reference": 0,
    "titles for reference": 0,
    "creators": 1,
    "original titles": 2,
    "dates": 3
}

NUMBER_OF_ROWS = 3

load_re = ur'^(?:that )?the user (?:is on|reloads) the page for editing '\
          ur'titles$'


@given(load_re)
@when(load_re)
def step_impl(context):
    driver = context.driver
    config = context.selenic_config
    driver.get(config.SERVER + "/bibliography/title/")


title_re = ur'^(?:that )?the items are sorted by ' \
           ur'(?P<order>ascending|descending) ' \
           ur'(?P<what>creators|dates|original titles|' \
           ur'titles for reference)\.?$'
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


@when(ur'^the user clicks on the icon for sorting '
      ur'(?P<what>creators|dates|original titles|titles for reference)$')
def step_impl(context, what):
    util = context.util
    column = COLUMNS[what]

    header = util.find_element((
        By.XPATH,
        "//table[@id='bibliography-table']/thead/tr[1]/th[{0}]".format(
            column + 1)))
    header.click()


@when(ur'^the user clicks on the title for reference of row (?P<row_n>\d+)$')
def step_impl(context, row_n):
    util = context.util
    column = COLUMNS["title for reference"]

    def cond(*_):
        try:
            cell = util.find_element((
                By.XPATH,
                "//table[@id='bibliography-table']/tbody/tr[{0}]/td[{1}]/span"
                .format(int(row_n) + 1, column + 1)))
            cell.click()
            return True
        except StaleElementReferenceException:
            return False

    util.wait(cond)


@when(ur'^the user clicks the clear button$')
def step_impl(context):
    util = context.util
    button = util.find_element((By.CLASS_NAME, "editable-clear-x"))
    button.click()


@then(ur'^the title for reference of row (?P<row_n>\d+) is '
      ur'"(?P<value>.*?)"\.?$')
def step_impl(context, row_n, value):
    driver = context.driver
    util = context.util

    column = COLUMNS["title for reference"]
    row_n = int(row_n)

    def cond(*_):
        return driver.execute_script("""
        var row_n = arguments[0];
        var colno = arguments[1];
        var text = arguments[2];

        var $ = jQuery;
        var $table = $("#bibliography-table");
        var $cell = $table.find("tbody>tr").eq(row_n).children("td").eq(colno);
        if (!$cell[0])
            return false;

        return $cell.text() === text;
        """, row_n, column, value)

    util.wait(cond)


@then(ur'^the title for reference of row (?P<row_n>\d+) has an error '
      ur'message\.?$')
def step_impl(context, row_n):
    driver = context.driver
    util = context.util

    column = COLUMNS["title for reference"]

    def cond(*_):
        return driver.execute_script("""
        var row_n = arguments[0];
        var colno = arguments[1];
        var text = arguments[2];

        var $ = jQuery;
        var $table = $("#bibliography-table");
        var $cell = $table.find("tbody>tr").eq(row_n).children("td").eq(colno);
        if (!$cell[0])
            return false;

        return $cell.find(".editable-error-block")[0];
        """, row_n, column)

    util.wait(cond)


@given("^all rows are loaded\.?$")
def step_impl(context):
    context.execute_steps(u"""
    Given there are {0} rows.
    """.format(NUMBER_OF_ROWS))

rows_re = ur'^there (?:is|are) (?P<number>\d+) rows?\.?$'


@given(rows_re)
@then(rows_re)
def step_impl(context, number):
    number = int(number)

    driver = context.driver
    util = context.util

    def cond(*_):
        return driver.execute_script("""
        var no = arguments[0];

        var $ = jQuery;
        var $table = $("#bibliography-table");
        return $table.find("tbody>tr").length === no;
        """, number)

    util.wait(cond)


@when(ur'^the user clicks on the filtering field$')
def step_impl(context):
    util = context.util
    field = util.find_element((By.CSS_SELECTOR,
                               "input[aria-controls='bibliography-table']"))
    field.click()
