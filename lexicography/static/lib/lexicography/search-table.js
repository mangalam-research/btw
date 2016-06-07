define(function searchTableModule(require, exports, _module) {
  "use strict";

  var $ = require("jquery");
  var ajaxLib = require("ajax");
  var ajax = ajaxLib.ajax;
  var ajax$ = ajaxLib.ajax$;
  var modalTemplate = require("text!./modal.html");
  var advancedSearchTemplate = require("text!./advanced-search.html");
  require("datatables.bootstrap");
  require("jquery.bootstrap-growl");

  // This number should be bumped whenever we must flush the old saved
  // state but do not have any other means to do so.
  var _LOCAL_VERSION = 1;

  return function searchTable($table, options) {
    var canAuthor = options.canAuthor;
    var columnDefs = [];
    if (!canAuthor) {
      columnDefs.push({
        targets: [1, 2, 3],
        orderable: false,
        visible: false,
      });
    }
    else {
      columnDefs.push({
        targets: [3],
        render: function render(data, type, rowData) {
          var deleted = rowData[3];
          return deleted === "Yes" ?
            "<span style='color: red'>Yes</span>" : deleted;
        },
      });
    }

    // This is not meant to prevent reverse engineering or be
    // sophisticated in any way. What we want is that if a change in
    // privileges happen, then the saved state should be flushed.
    var token = "" + _LOCAL_VERSION + "," + (canAuthor ? "1" : "0");

    var recordName = canAuthor ? "change records" : "articles";
    var publishBtns = $table[0].getElementsByClassName("btw-publish-btn");
    var unpublishBtns = $table[0].getElementsByClassName("btw-unpublish-btn");

    function alert(el, data, kind) {
      var rect = el.getBoundingClientRect();
      var alertbox = document.createElement("div");
      alertbox.className = "alert alert-dismissible " + kind;
      alertbox.setAttribute("role", "alert");
      alertbox.innerHTML =
        "<button type='button' class='close' data-dismiss='alert'>" +
        "<span aria-hidden='true'>&times;</span><span class='sr-only'>" +
        "Close</span></button>" +
        data + "&nbsp;";
      document.body.appendChild(alertbox);
      alertbox.style.position = "absolute";
      alertbox.style.top = rect.top + 5 + "px";
      alertbox.style.left = rect.left + 5 + "px";
    }

    function postPublishUnpublish(ev) {
      ajax({
        type: "POST",
          url: this.attributes.href.value,
      }).then(function done(data) {
        alert(ev.target, data, "alert-success");
          // eslint-disable-next-line no-use-before-define
        table.api().ajax.reload(null, false);
      }).catch(function handle(err) {
        alert(ev.target, err.jqXHR.responseText, "alert-danger");
      });

      return false;
    }

    function checkUnpublish(ev) {
      var $modal = $(modalTemplate);
      document.body.appendChild($modal[0]);

      $modal.on("click", ".btn.btn-primary", function clickPrimary() {
        document.body.removeChild($modal[0]);
        return false;
      });

      var obj = this;
      $modal.on("click", ".btn.btn-default", function clickDefault() {
        postPublishUnpublish.call(obj, ev);
        document.body.removeChild($modal[0]);
        return false;
      });

      $modal.modal();
      return false;
    }

    var doc = $table[0].ownerDocument;

    var label = doc.createElement("label");
    label.innerHTML = "Lemmata only: <input type='checkbox' " +
      "class='form-control input-sm'></input>";
    var lemmaCheckbox = label.lastElementChild;

    var advancedRow = doc.createElement("div");
    advancedRow.className = "row";
    var advanced = doc.createElement("div");
    advanced.className = "panel-group";
    advanced.style.marginBottom = "0px";
    advanced.id = "advanced-search";
    advanced.innerHTML = advancedSearchTemplate;
    var icon = advanced.getElementsByClassName("fa")[0];
    var cl = icon.classList;
    $(advanced).on("show.bs.collapse", function showCollapse() {
      cl.remove("fa-plus");
      cl.add("fa-minus");
    }).on("hide.bs.collapse", function hideCollapse() {
      cl.remove("fa-minus");
      cl.add("fa-plus");
    });

    advancedRow.appendChild(advanced);

    var publicationSelector =
          advanced.getElementsByClassName("btw-publication-status")[0];

    publicationSelector.value = canAuthor ? "both" : "published";

    var searchAll =
          advanced.getElementsByClassName("btw-search-all-history")[0];

    $([lemmaCheckbox, publicationSelector, searchAll])
      .change(function change() {
        // eslint-disable-next-line no-use-before-define
        table.fnDraw();
      });

    function drawCallback() {
      if (!label.parentNode) {
        var filter =
              doc.getElementById("search-table_wrapper")
              .getElementsByClassName("dataTables_filter")[0];
        var filterRow = filter.parentNode.parentNode;
        filter.appendChild(doc.createTextNode(" "));
        filter.appendChild(label);

        if (canAuthor) {
          filterRow.parentNode.insertBefore(advancedRow,
                                            filterRow.nextElementSibling);
        }
      }

      var i;
      var btn;
      for (i = 0; i < publishBtns.length; ++i) {
        btn = publishBtns[i];
        $(btn).click(postPublishUnpublish);
      }

      for (i = 0; i < unpublishBtns.length; ++i) {
        btn = unpublishBtns[i];
        $(btn).click(checkUnpublish);
      }
    }

    // We need to have this custom function so that we can handle the cases
    // where a bad Lucene query is passed to eXist-db and the server replies
    // that the query is bad.
    function tableAjax(data, callback, settings) {
      data.lemmata_only = lemmaCheckbox.checked;
      data.publication_status = publicationSelector.value;
      data.search_all = searchAll.checked;
      var bundle = ajax$({
        url: options.ajaxSourceURL,
        data: data,
        dataType: "json",
        cache: false,
        type: settings.sServerMethod,
      });

      var me = this;
      bundle.promise.then(function then(json) {
        // We force DataTables to not update the table by setting draw to a
        // negative value. DataTables will interpret this as receiving results
        // from the server out of order and will ignore these results.
        if (json.badLucene) {
          json.draw = -1;

          // We need to call this ourselves to remove the "processing" label.
          me._fnProcessingDisplay(false);
        }

        callback(json);
      });

      return bundle.xhr;
    }

    var table = $table.dataTable({
      pageLength: options.rows || undefined,
      lengthChange: (options.rows === undefined),
      processing: true,
      serverSide: true,
      autoWidth: false,
      stateSave: true,
      stateSaveParams: function stateSaveParams(settings, data) {
        var params = this.api().ajax.params();
        data.btw_token = token;
        data.lemmata_only = params.lemmata_only;
        data.publication_status = params.publication_status;
        data.search_all = params.search_all;
      },
      stateLoadParams: function stateLoadParams(settings, data) {
        if (data.btw_token !== token) {
          // The token changed, clear the state.
          this.api().state.clear();
          return false;
        }
        return undefined;
      },
      stateLoaded: function stateLoaded(settings, data) {
        lemmaCheckbox.checked = data.lemmata_only;
        publicationSelector.value = data.publication_status;
        searchAll.checked = data.search_all;
      },
      ajax: tableAjax,
      columnDefs: columnDefs,
      language: {
        info: "Showing _START_ to _END_ of _TOTAL_ " + recordName,
        infoEmpty: "No " + recordName + " to show",
        infoFiltered: "(filtered from _MAX_ total " + recordName + ")",
        lengthMenu: "Show _MENU_ " + recordName,
      },
      drawCallback: drawCallback,
    });

    $table.data("search-table", table);
    return table;
  };
});
