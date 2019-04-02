/**
 * @module js/core/cite-support
 * @desc Support for citations.
 * @author Louis-Dominique Dubeau
 */
define(function factory(require, _exports, _module) {
  "use strict";

  var $ = require("jquery");
  var moment = require("moment");
  require("bootstrap-datepicker");

  var body = document.body;
  var $picker = $(document.getElementById("access-date"));

  var accessedSpans = body.getElementsByClassName("accessed");
  var today = new Date();

  $picker.datepicker({
    format: "yyyy-mm-dd",
    todayBtn: "linked",
    autoclose: true,
    todayHighlight: true,
  }).datepicker("setDate", today);

  function refreshCitations() {
    var date = $picker.datepicker("getDate");
    // eslint-disable-next-line no-cond-assign
    for (var i = 0, span; (span = accessedSpans[i]); ++i) {
      span.textContent = moment(date).format("MMMM D YYYY");
    }
  }

  $picker.on("changeDate", refreshCitations);

  refreshCitations();
});
