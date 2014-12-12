from selenium.webdriver.common.by import By
from nose.tools import assert_equal  # pylint: disable=no-name-in-module

RETURN_INSERTABLE_ELEMENTS = """
function hasTrsAt(data_node, offset) {
    var ret = Object.create(null);
    wed_editor.validator.possibleAt(data_node, offset).forEach(
        function (ev) {
        if (ev.params[0] !== "enterStartTag")
            return;

        var unresolved = wed_editor.resolver.unresolveName(
            ev.params[1], ev.params[2]);

        var trs = wed_editor.mode.getContextualActions(
            "insert", unresolved, data_node, offset);
        if (trs.length)
            ret[unresolved] = 1;
    });
    function getPath(node) {
        var parent_path = "";
        if (node.parentNode &&
            node.parentNode !== wed_editor.data_root) {
            parent_path = getPath(node.parentNode);
        }
        return parent_path + "/" + node.tagName;
    }
    return [getPath(data_node), Object.keys(ret)];
}
var $ = jQuery;
return arguments[0].map(function (loc) {
    return hasTrsAt($.data(loc[0], "wed_mirror_node"), loc[1]);
});
"""

@then('context menu test')
def step_impl(context):
    driver = context.driver
    util = context.util

    trs = util.find_elements((By.CSS_SELECTOR, r".btw\:tr"))

    locations = [[tr, 0] for tr in trs]

    cits = util.find_elements((By.CSS_SELECTOR, r".btw\:cit"))

    locations += [[cit, 1] for cit in cits]

    foreigns = util.find_elements((By.CSS_SELECTOR, r".btw\:cit>.foreign"))

    locations += [[foreign, 0] for foreign in foreigns]

    base = [u'btw:antonym-instance', u'btw:cognate-instance',
            u'btw:conceptual-proximate-instance',
            u'btw:lemma-instance']
    expected_by_type = {
        "btw:cit": base + [u'lg', u'p', u'ref'],
        "foreign": base,
        "btw:tr": base + [u'lg', u'p']
    }

    for line in driver.execute_script(RETURN_INSERTABLE_ELEMENTS,
                                      locations):
        line[1].sort()
        assert_equal(
            line[1],
            expected_by_type[line[0].rsplit("/", 1)[-1]],
            line[0] + " has an incorrect set of possible elements")