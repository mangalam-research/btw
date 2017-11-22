/**
 * @module js/lexicography/view-support
 * @desc Support for viewing articles.
 * @author Louis-Dominique Dubeau
 */

define(function factory(require, exports, _module) {
  "use strict";

  var $ = require("jquery");
  var moment = require("moment");
  require("bootstrap-datepicker");

  var body = $("#cite-modal .modal-body")[0];
  var $picker = $(document.getElementById("access-date"));
  var versionSpecificCheckbox = document.getElementById("version-specific");

  var accessedSpans = body.getElementsByClassName("accessed");
  var urlSpans = body.getElementsByClassName("url");
  var form = body.getElementsByTagName("form")[0];
  var downloadMods = document.getElementById("download-mods");
  var mlaYear = document.getElementById("mla_year");
  var citeButton = document.querySelector(".btn[data-target='#cite-modal']");
  var today = new Date();

  $picker.datepicker({
    format: "yyyy-mm-dd",
    todayBtn: "linked",
    autoclose: true,
    todayHighlight: true,
  }).datepicker("setDate", today);

  mlaYear.textContent = today.getFullYear();

  var absDiv = document.createElement("div");
  absDiv.innerHTML = "<a></a>";
  function absolute(url) {
    absDiv.firstChild.href = url;
    // absDiv.innerHTML = absDiv.innerHTML;
    return absDiv.firstChild.href;
  }

  return function viewSupport(permalink, versionPermalink, viewer) {
    function refreshCitations() {
      var date = $picker.datepicker("getDate");
      var i;
      var span;
      for (i = 0; i < accessedSpans.length; ++i) {
        span = accessedSpans[i];
        span.textContent = moment(date).format("MMMM D YYYY");
      }

      var url = absolute(versionSpecificCheckbox.checked ? versionPermalink
                         : permalink);
      for (i = 0; i < urlSpans.length; ++i) {
        span = urlSpans[i];
        span.innerHTML = url;
        span.href = url;
      }
    }

    $picker.on("changeDate", refreshCitations);
    $(versionSpecificCheckbox).on("change", refreshCitations);
    $(downloadMods).on("click", function click() {
      form.submit();
      return false;
    });

    refreshCitations();

    function convertNames(els) {
      var ret = [];
      for (var i = 0; i < els.length; ++i) {
        var el = els[i];
        var surname = el.getElementsByClassName("surname")[0];
        var forename = el.getElementsByClassName("forename")[0];
        var genName = el.getElementsByClassName("genName")[0];

        // If anything is missing, we abort the conversion. The document is not
        // ready.
        if (!(surname && forename && genName)) {
          return [];
        }

        surname = surname.textContent.trim();
        forename = forename.textContent.trim();
        genName = genName.textContent.trim();

        if (genName === "") {
          genName = undefined;
        }

        if (forename === "") {
          forename = undefined;
        }

        ret.push({
          surname: surname,
          forename: forename,
          genName: genName,
        });
      }

      return ret;
    }

    function combineNames(names, reverseFirst, max) {
      var ret = "";

      var i = 0;
      var name = names[0];

      if (reverseFirst) {
        ret += name.surname;

        if (name.forename) {
          ret += ", " + name.forename;
        }

        if (name.genName) {
          ret += ", " + name.genName;
        }

        if (names[1]) {
          ret += (names.length > 2) ? ", " : " and ";
        }

        i++;
      }

      // max is used for MLA format citations. If there are more
      // than 3 authors, then we only list the first author + "et
      // al.".
      if (names.length > max) {
        ret += "et al.";

        return ret;
      }

      for (; i < names.length; ++i) {
        name = names[i];
        if (name.forename) {
          ret += name.forename + " ";
        }

        ret += name.surname;

        if (name.genName) {
          ret += ", " + name.genName;
        }

        if (names[i + 1]) {
          ret += (i < names.length - 2) ? ", " : " and ";
        }
      }

      return ret;
    }


    viewer.whenCondition("done", function done() {
      // We need to wait until the document is "done" rendering so
      // that we can grab the author information and editor
      // information for the citations.

      var root = viewer.root;

      if (!root.querySelector(".btw\\:credits")) {
        // Leave the button disabled but add an explanatory title.
        citeButton.setAttribute(
          "title",
          "This article was produced with an old version of the " +
            "BTW schema and thus does not support the automatic " +
            "generation of citations.");
        return;
      }

      var authors = convertNames(
        root.querySelectorAll(".btw\\:credit .persName"));
      var editors = convertNames(root.querySelectorAll(".editor .persName"));

      if (!(authors.length && editors.length)) {
        // Leave the button disabled but add an explanatory title.
        citeButton.setAttribute(
          "title",
          "This article does not yet have authors and editors recorded.");
        return;
      }

      var mlaAuthors = document.getElementById("mla_authors");
      mlaAuthors.textContent = combineNames(authors, true, 3);

      var mlaEditors = document.getElementById("mla_editors");
      mlaEditors.textContent = editors.length > 1 ? "Eds. " : "Ed. ";
      mlaEditors.textContent += combineNames(editors, true, 3);

      var chicagoAuthors = document.getElementById("chicago_authors");
      chicagoAuthors.textContent = combineNames(authors);

      citeButton.classList.remove("disabled");
    });
  };
});
