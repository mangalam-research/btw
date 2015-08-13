/**
 * @module js/lexicography/view-support
 * @desc Support for viewing articles.
 * @author Louis-Dominique Dubeau
 */

define(function (require, exports, module) {

var $ = require("jquery");
var moment = require("moment");
require("bootstrap-datepicker");

var body = $('#cite-modal .modal-body')[0];
var $picker = $(document.getElementById("access-date"));
var version_specific_checkbox = document.getElementById("version-specific");

var accessed_spans = body.getElementsByClassName("accessed");
var url_spans = body.getElementsByClassName("url");
var form = body.getElementsByTagName("form")[0];
var download_mods = document.getElementById("download-mods");
var mla_year = document.getElementById("mla_year");
var cite_button = document.querySelector(".btn[data-target='#cite-modal']");
var today = new Date();

$picker.datepicker({
    format: "yyyy-mm-dd",
    todayBtn: "linked",
    autoclose: true,
    todayHighlight: true
}).datepicker('setDate', today);

mla_year.textContent = today.getFullYear();

var abs_div = document.createElement('div');
abs_div.innerHTML = "<a></a>";
function absolute(url) {
    abs_div.firstChild.href = url;
    // abs_div.innerHTML = abs_div.innerHTML;
    return abs_div.firstChild.href;
}

return function (permalink, version_permalink, viewer) {

    function refreshCitations() {
        var date = $picker.datepicker('getDate');
        var i, span;
        for (i = 0; (span = accessed_spans[i]); ++i)
            span.textContent = moment(date).format("MMMM D YYYY");

        var url = absolute(version_specific_checkbox.checked ? version_permalink
                : permalink);
        for (i = 0; (span = url_spans[i]); ++i) {
            span.innerHTML = url;
            span.href = url;
        }

    }

    $picker.on("changeDate", refreshCitations);
    $(version_specific_checkbox).on("change", refreshCitations);
    $(download_mods).on("click", function () {
        form.submit();
        return false;
    });

    refreshCitations();

    function convertNames(els) {
        var ret = [];
        for (var i = 0, el; (el = els[i]); ++i) {
            var surname = el.getElementsByClassName("surname")[0]
                    .textContent.trim();
            var forename = el.getElementsByClassName("forename")[0]
                    .textContent.trim();
            var genName = el.getElementsByClassName("genName")[0]
                    .textContent.trim();

            if (genName === "")
                genName = undefined;

            if (forename === "")
                forename = undefined;

            ret.push({
                surname: surname,
                forename: forename,
                genName: genName
            });
        }

        return ret;
    }

    function combineNames(names, reverse_first, max) {
        var ret = "";

        var i = 0, name = names[0];

        if (reverse_first) {
            ret += name.surname;

            if (name.forename)
                ret += ", " + name.forename;

            if (name.genName)
                ret += ", " + name.genName;

            if (names[1])
                ret += (names.length > 2) ? ", " : " and ";

            i++;
        }

        // max is used for MLA format citations. If there are more
        // than 3 authors, then we only list the first author + "et
        // al.".
        if (names.length > max) {
            ret += "et al.";

            return ret;
        }

        for (; (name = names[i]); ++i) {
            if (name.forename)
                ret += name.forename + " ";

            ret += name.surname;

            if (name.genName)
                ret += ", " + name.genName;

            if (names[i + 1])
                ret += (i < names.length - 2) ? ", " : " and ";
        }

        return ret;
    }


    viewer.whenCondition("done", function () {
        var root = viewer._root;

        if (!root.querySelector(".btw\\:credits")) {
            // Leave the button disabled but add an explanatory title.
            cite_button.setAttribute(
                "title",
                "This article was produced with an old version of the " +
                    "BTW schema and thus does not support the automatic " +
                    "generation of citations.");
            return;
        }

        // We need to wait until the document is "done" rendering so
        // that we can grab the author information and editor
        // information for the citations.
        var authors = convertNames(
            root.querySelectorAll(".btw\\:credit .persName"));
        var editors = convertNames(root.querySelectorAll(".editor .persName"));

        var mla_authors = document.getElementById("mla_authors");
        mla_authors.textContent = combineNames(authors, true, 3);

        var mla_editors = document.getElementById("mla_editors");
        mla_editors.textContent = editors.length > 1 ? "Eds. " : "Ed. ";
        mla_editors.textContent += combineNames(editors, true, 3);

        var chicago_authors = document.getElementById("chicago_authors");
        chicago_authors.textContent = combineNames(authors);

        cite_button.classList.remove("disabled");
    });
};

});
