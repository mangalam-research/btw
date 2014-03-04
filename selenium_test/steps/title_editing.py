import collections

# pylint: disable=no-name-in-module
from behave import given, then, when, step_matcher
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

step_matcher('re')


# pylint: disable=no-name-in-module
from nose.tools import assert_true, assert_equal

COLUMNS = {
    "title for reference": 0,
    "titles for reference": 0,
    "creators": 1,
    "original titles": 2,
    "dates": 3
}

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
    util = context.util
    table = util.find_element((By.ID, "bibliography-table"))

    column = COLUMNS[what]

    def cond(*_):
        header = table.find_elements_by_xpath("./thead/tr[1]/th")[column]
        classes = header.get_attribute("class").split(" ")
        return ORDERS[order].class_ in classes

    util.wait(cond)

    def cond(*_):
        rows = table.find_elements_by_xpath("./tbody/tr")
        if len(rows) != 2:
            return False

        cells = []
        try:
            for row in rows:
                cell = row.find_elements_by_tag_name("td")[column]
                cells.append(cell)
        except StaleElementReferenceException:
            return False

        op = ORDERS[order].op

        try:
            for i in xrange(0, len(cells) - 1):
                if not op(cells[i].text, cells[i + 1].text):
                    return False
        except StaleElementReferenceException:
            return False

        return True

    util.wait(cond)


@when(ur'^the user clicks on the icon for sorting '
      ur'(?P<what>creators|dates|original titles|titles for reference)$')
def step_impl(context, what):
    util = context.util
    table = util.find_element((By.ID, "bibliography-table"))

    column = COLUMNS[what]

    headers = table.find_elements_by_xpath("./thead/tr[1]/th")
    headers[column].click()


@when(ur'^the user clicks on the title for reference of row (?P<row_n>\d+)$')
def step_impl(context, row_n):
    util = context.util
    table = util.find_element((By.ID, "bibliography-table"))

    column = COLUMNS["title for reference"]

    cell = table.find_element_by_xpath(
        "./tbody/tr[{0}]/td[{1}]/span".format(int(row_n) + 1, column + 1))
    cell.click()


@then(ur'^the title for reference of row (?P<row_n>\d+) is '
      ur'"(?P<value>.*?)"\.?$')
def step_impl(context, row_n, value):
    util = context.util
    table = util.find_element((By.ID, "bibliography-table"))

    column = COLUMNS["title for reference"]

    def cond(*_):
        cell = table.find_element_by_xpath(
            "./tbody/tr[{0}]/td[{1}]".format(int(row_n) + 1, column + 1))
        ret = False

        # The cell might get recreated while we are doing this.
        try:
            ret = cell.text == value
        except StaleElementReferenceException:
            pass

        return ret

    util.wait(cond)


@then(ur'^the title for reference of row (?P<row_n>\d+) has an error '
      ur'message\.?$')
def step_impl(context, row_n):
    util = context.util
    table = util.find_element((By.ID, "bibliography-table"))

    column = COLUMNS["title for reference"]

    def cond(*_):
        cell = table.find_element_by_xpath(
            "./tbody/tr[{0}]/td[{1}]".format(int(row_n) + 1, column + 1))
        ret = False

        # The cell might get recreated while we are doing this.
        try:
            ret = cell.find_element_by_class_name("editable-error-block")
        except StaleElementReferenceException:
            pass

        return ret

    util.wait(cond)

rows_re = ur'^there (?:is|are) (?P<number>\d+) rows?\.?$'


@given(rows_re)
@then(rows_re)
def step_impl(context, number):
    number = int(number)

    util = context.util
    table = util.find_element((By.ID, "bibliography-table"))

    def cond(*_):
        rows = table.find_elements_by_xpath("./tbody/tr")
        return rows if len(rows) == number else None

    util.wait(cond)


@when(ur'^the user clicks on the filtering field$')
def step_impl(context):
    util = context.util
    field = util.find_element((By.CSS_SELECTOR,
                               "input[aria-controls='bibliography-table']"))
    field.click()
