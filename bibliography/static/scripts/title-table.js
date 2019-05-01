define(function factory(require) {
  "use strict";

  var $ = require("jquery");
  var _ = require("lodash");
  var cookies = require("js-cookie");
  require("datatables.bootstrap");

  var csrftoken = cookies.get("csrftoken");

  var template = _.template;

  var $modal = $(
    "\
<div class='modal' style='position: absolute' tabindex='1'>\
  <div class='modal-dialog'>\
    <div class='modal-content'>\
      <div class='modal-header'>\
        <h5>Create New Primary Source</h5>\
        <button type='button' class='close' data-dismiss='modal' \
         aria-hidden='true'>&times;</button>\
      </div>\
      <div class='modal-body'>\
        <p>No body.</p>\
      </div>\
      <div class='modal-footer'>\
        <a href='#' class='btn btn-primary'>Save</a>\
        <a href='#' class='btn btn-outline-dark' data-dismiss='modal'>Cancel</a>\
      </div>\
    </div>\
  </div>\
</div>");

  var buttonsTemplate = template("\
<% if (edit) { %>\
<div class='btn btn-outline-dark btn-sm add-button'><i class='fa fa-plus'></i></div>\
<% } %>\
<div style='position: relative' \
     class='btn <% print(children ? 'btn-outline-dark ':'') %>btn-sm open-close-button'>\
  <i class='fa fa-fw \
            <% print(children ? 'fa-caret-right': '') %>'></i>\
  <% print(children ? \
           '<span class=\"primary-source-count\" style=\"position: absolute; font-size: x-small; text-align: left; top:0; left: 0.5em;\">' + \
           children + '</span>' : '') %>\
</div>");

  var $body = $modal.find(".modal-body");
  var $primary = $modal.find(".btn-primary");

  $("body").prepend($modal);

  var subtableTemplate = "\
<table class='primary-source-table table table-striped' width='100%'>\
  <thead>\
    <tr>\
      <th></th>\
      <th>Reference Title</th>\
      <th>Genre</th>\
    </tr>\
  </thead>\
  <tbody>\
  </tbody>\
  <tfoot>\
  </tfoot>\
</table>";

  function makeSubtable(table, options, rowNode, url) {
    var $newRow = $(table.fnOpen(rowNode, subtableTemplate, "subtable"));
    var $subtable = $newRow.find("table").first();
    $newRow.children("td").attr("colspan", "2");
    $newRow.prepend("<td colspan='1'></td>");

    var aoColumnDefs = [];
    if (options.can_edit) {
      aoColumnDefs.push({
        aTargets: [0],
        bSortable: false,
        mRender: function render() {
          return "<div class='btn btn-outline-dark btn-sm edit-button'>\
<i class='fa fa-edit'></i></div>";
        },
        fnCreatedCell: function created(cell, _data, row) {
          var $cell = $(cell);
          var editUrl = row[0];
          var $edit = $cell.children("div");
          $edit.click(function onClick() {
            $.ajax({
              url: editUrl,
              headers: {
                Accept: "application/x-form",
              },
            }).done(function done(data) {
              $body.html(data);
              // eslint-disable-next-line no-use-before-define
              setFormFields();
              $primary.one("click", function onPrimaryClick() {
                $.ajax({
                  url: editUrl,
                  type: "PUT",
                  data: $modal.find("form").serialize(),
                  headers: {
                    "X-CSRFToken": csrftoken,
                    Accept: "application/x-form",
                  },
                  success: function success() {
                    $modal.modal("hide");
                    // eslint-disable-next-line no-use-before-define
                    subtable.fnDraw(false);
                  },
                  error: function errorHandler(jqXHR) {
                    $body.html(jqXHR.responseText);
                  },
                });
              });
              $modal.modal();
            });
          });
        },
      });
    }
    else {
      // We can't edit so the first column is not visible.
      aoColumnDefs.push({
        aTargets: [0],
        bSortable: false,
        bVisible: false,
      });
    }

    var subtable = $subtable.dataTable({
      iDisplayLength: -1,
      bProcessing: true,
      bServerSide: true,
      bAutoWidth: true,
      sAjaxSource: url,
      sDom: "rtip",
      aaSorting: [
        [1, "asc"],
      ],
      aoColumnDefs: aoColumnDefs,
      fnCreatedRow: function created(subtableRowNode, data) {
        // Move the item key to a data attribute.
        $(subtableRowNode).attr("data-item-url", data[0]);
      },
      fnDrawCallback: function draw(subtableOptions) {
        var visibility = (subtableOptions._iDisplayLength === -1 ||
                          (subtableOptions.fnRecordsTotal() <=
                           subtableOptions._iDisplayLength)) ?
            "none" : "block";
        var $wrapper = $subtable.parents(".dataTables_wrapper").first();

        $wrapper.find(".dataTables_info").css("display", visibility);
        $wrapper.find(".dataTables_paginate").css("display", visibility);
      },
    });
    // eslint-disable-next-line no-use-before-define
    subtable.fnFilter(prevFilter);
  }

  var openIds = Object.create(null);

  function openOrCloseRow(table, options, rowNode, $i, url, id) {
    if (table.fnIsOpen(rowNode)) {
      table.fnClose(rowNode);
      $i.removeClass("fa-caret-down");
      $i.addClass("fa-caret-right");
      $i.parents("div.open-close-button").removeClass("active");
      delete openIds[id];
    }
    else {
      makeSubtable(table, options, rowNode, url);
      $i.removeClass("fa-caret-right");
      $i.addClass("fa-caret-down");
      $i.parents("div.open-close-button").addClass("active");
      openIds[id] = true;
    }
  }

  var prevFilter = "";

  function refilterOpenRows(table, $table) {
    var newFilter = $table.parents(".dataTables_wrapper").first()
        .find(".dataTables_filter input").val();
    if (prevFilter !== newFilter) {
      var rows = table.fnGetNodes();
      for (var i = 0, limit = rows.length; i < limit; ++i) {
        var rowNode = rows[i];
        if (table.fnIsOpen(rowNode)) {
          var $subtable = $(rowNode).next("tr").find(".primary-source-table");
          var subtable = $subtable.dataTable();
          subtable.fnFilter(newFilter);
        }
      }
      prevFilter = newFilter;
    }
  }


  function setFormFields() {
    var $textarea = $body.find("textarea");
    $textarea.one("keypress", function keypress(ev) {
      if (ev.which === 10 || ev.which === 13) {
        $primary.click();
        return false;
      }
      return true;
    });
    // Let the current event finish before setting the focus.
    setTimeout(function onTimeout() {
      $textarea[0].focus();
    }, 0);
  }

  return function titleTable($table, options) {
    if (options.selectable) {
      $table.find("tbody").on("click", "tr", function onClick() {
        var $this = $(this);
        if ($this.find("tbody>tr").length === 0) {
          $table.find("tbody>tr").removeClass("selected-row");
          $this.siblings("tr").removeClass("selected-row");
          $this.addClass("selected-row");
          $table.trigger("selected-row");
        }
      });
    }

    var table = $table.dataTable({
      iDisplayLength: options.rows || undefined,
      bLengthChange: (options.rows === undefined),
      bProcessing: true,
      bServerSide: true,
      bAutoWidth: false,
      sAjaxSource: options.ajax_source_url,
      aaSorting: [
        [4, "asc"],
      ],
      aoColumnDefs: [
        {
          aTargets: [0, 1, 2],
          bVisible: false,
        },
        {
          aTargets: [2],
          bSortable: false,
        },
        {
          aTargets: [3],
          bSortable: false,
          mRender: function render(data, type, rowData) {
            var children = Number(rowData[2]);
            return buttonsTemplate({
              children: children,
              edit: options.can_edit,
            });
          },
          fnCreatedCell: function created(cell, data, row, rowIx, colIx) {
            var $cell = $(cell);
            $cell.css("white-space", "nowrap");
            var subtableUrl = row[1];
            var $open = $cell.children("div.open-close-button");
            var $i = $open.children("i");
            $open.click(function onClick() {
              var rowNode = $open.parents("tr")[0];
              openOrCloseRow(table, options, rowNode, $i,
                             subtableUrl, row[0]);
            });

            var addUrl = row[colIx];
            var $add = $cell.children("div.add-button");
            $add.click(function onClick() {
              $body.load(addUrl, function loaded() {
                setFormFields();
                $primary.on("click", function onPrimaryClick() {
                  $.ajax({
                    url: addUrl,
                    type: "POST",
                    data: $modal.find("form").serialize(),
                    success: function success() {
                      $modal.modal("hide");
                      table.fnDraw(false);
                      $primary.off("click");
                    },
                    error: function errorHandler(jqXHR) {
                      $body.html(jqXHR.responseText);
                    },
                  });
                });
                $modal.modal();
              });
            });
          },
        },
      ],
      fnCreatedRow: function created(rowNode, data) {
        var $rowNode = $(rowNode);
        var url = data[0];
        var primarySourcesUrl = data[1];
        var $i = $rowNode.children("td").eq(0).find("i").eq(1);
        if (openIds[url]) {
          openOrCloseRow(table, options, rowNode, $i,
                         primarySourcesUrl, url);
        }
        // Move the item key to a data attribute.
        $rowNode.attr("data-item-url", url);
      },
      fnDrawCallback: function draw() {
        refilterOpenRows(table, $table);
        $table.trigger("refresh-results");
      },
    });

    $table.data("title-table", table);

    var $hideAll = $table.find(".hide-all-ps");
    var $showAll = $table.find(".show-all-ps");

    $hideAll.click(function onClick() {
      var rows = table.fnGetNodes();
      for (var i = 0, limit = rows.length; i < limit; ++i) {
        var rowNode = rows[i];
        var data = table.fnGetData(i);
        if (table.fnIsOpen(rowNode)) {
          // eslint-disable-next-line newline-per-chained-call
          var $i = $(rowNode).children("td").eq(0).find("i").eq(1);
          openOrCloseRow(table, options, rowNode, $i, data[1], data[0]);
        }
      }
    });

    $showAll.click(function onClick() {
      var rows = table.fnGetNodes();
      for (var i = 0, limit = rows.length; i < limit; ++i) {
        var rowNode = rows[i];
        var data = table.fnGetData(i);
        if (Number(data[2]) > 0 && !table.fnIsOpen(rowNode)) {
          // eslint-disable-next-line newline-per-chained-call
          var $i = $(rowNode).children("td").eq(0).find("i").eq(1);
          openOrCloseRow(table, options, rowNode, $i, data[1], data[0]);
        }
      }
    });

    return table;
  };
});
