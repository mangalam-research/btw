/**
 * @module js/core/cite-support
 * @desc Support for citations.
 * @author Louis-Dominique Dubeau
 */

define(function (require, exports, module) {

var $ = require("jquery");
var moment = require("moment");
require("bootstrap-datepicker");

var body = document.body;
var $picker = $(document.getElementById("access-date"));

var accessed_spans = body.getElementsByClassName("accessed");
var form = body.getElementsByClassName("cite-form")[0];
var download_mods = document.getElementById("download-mods");
var today = new Date();

$picker.datepicker({
    format: "yyyy-mm-dd",
    todayBtn: "linked",
    autoclose: true,
    todayHighlight: true
}).datepicker('setDate', today);

function refreshCitations() {
    var date = $picker.datepicker('getDate');
    var i, span;
    for (i = 0; (span = accessed_spans[i]); ++i)
        span.textContent = moment(date).format("MMMM D YYYY");
}

$picker.on("changeDate", refreshCitations);
$(download_mods).on("click", function () {
    form.submit();
    return false;
});

refreshCitations();

});
