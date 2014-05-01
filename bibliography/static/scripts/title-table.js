define(['jquery', 'lodash/modern/utilities/template',
        'jquery.cookie', 'datatables'],
       function ($, template) {
var csrftoken = $.cookie('csrftoken');

var $modal = $(
       '\
<div class="modal" style="position: absolute" tabindex="1">\
  <div class="modal-dialog">\
    <div class="modal-content">\
      <div class="modal-header">\
        <button type="button" class="close" data-dismiss="modal" \
         aria-hidden="true">&times;</button>\
        <h3>Create New Primary Source</h3>\
      </div>\
      <div class="modal-body">\
        <p>No body.</p>\
      </div>\
      <div class="modal-footer">\
        <a href="#" class="btn btn-primary">Save</a>\
        <a href="#" class="btn" data-dismiss="modal">Cancel</a>\
      </div>\
    </div>\
  </div>\
</div>');

var buttons_template = template("\
<div class='btn btn-default btn-sm'><i class='icon-plus'></i></div>\
<div style='position: relative' \
     class='btn <% print(children ? 'btn-default ':'') %>btn-sm'>\
  <i class='icon-fixed-width \
            <% print(children ? 'icon-caret-right': '') %>'></i>\
  <% print(children ? \
           '<span class=\"primary-source-count\" style=\"position: absolute; font-size: x-small; text-align: left; top:0; left: 0.5em;\">' + \
           children + '</span>' : '') %>\
</div>");

var $body = $modal.find(".modal-body");
var $footer = $modal.find(".modal-footer");
var $clicked;
var $primary = $modal.find(".btn-primary");

$modal.on('click', '.btn', function (ev) {
    $clicked = $(ev.currentTarget);
    return true;
}.bind(this));

$("body").prepend($modal);

var subtable_template = '\
<table class="primary-source-table" width="100%">\
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
</table>';

function makeSubtable(table, row_node, url) {
    var $new_row = $(table.fnOpen(row_node, subtable_template, "subtable"));
    var $subtable = $new_row.find("table").first();
    $new_row.children("td").attr("colspan", "2");
    $new_row.prepend("<td colspan='1'></td>");

    var subtable = $subtable.dataTable({
        iDisplayLength: -1,
        bProcessing: true,
        bServerSide: true,
        bAutoWidth: true,
        sAjaxSource: url,
        sDom: "rtip",
        aaSorting: [
            [1, 'asc']
        ],
        aoColumnDefs: [
            {
                aTargets: [0],
                bSortable: false,
                mRender: function (data, type, row_data) {
                    return '<div class="btn btn-default btn-sm"><i class="icon-edit"></i></div>';
                },
                fnCreatedCell: function (cell, data, row, row_ix, col_ix) {
                    var $cell = $(cell);
                    var edit_url = row[0];
                    var $edit = $cell.children("div");
                    var $i = $edit.children("i");
                    $edit.click(function () {
                        $.ajax({
                            url: edit_url,
                            headers: {
                                Accept: "application/x-form"
                            }
                        }).done(function (data) {
                            $body.html(data);
                            setFormFields();
                            $primary.one("click", function () {
                                $.ajax({
                                    url: edit_url,
                                    type: "PUT",
                                    data: $modal.find("form").serialize(),
                                    headers: {
                                        'X-CSRFToken': csrftoken,
                                        Accept: "application/x-form"
                                    },
                                    success: function () {
                                        $modal.modal("hide");
                                        subtable.fnDraw(false);
                                    },
                                    error: function errorHandler(jqXHR) {
                                        $body.html(jqXHR.responseText);
                                    }
                                });
                            });
                            $modal.modal();
                        });
                    });
                }
            }
        ],
        fnDrawCallback: function (options) {
            var visibility = (options._iDisplayLength === -1 ||
                              (options.fnRecordsTotal() <=
                               options._iDisplayLength)) ?
                    "none" : "block";
            var $wrapper = $subtable.parents(".dataTables_wrapper").first();

            $wrapper.find('.dataTables_info').css("display", visibility);
            $wrapper.find('.dataTables_paginate').css("display", visibility);
        }
    });
    subtable.fnFilter(prev_filter);
}

var open_ids = Object.create(null);

function openOrCloseRow(table, row_node, $i, url, id) {
    if (table.fnIsOpen(row_node)) {
        table.fnClose(row_node);
        $i.removeClass("icon-caret-down");
        $i.addClass("icon-caret-right");
        $i.parents("div").first().removeClass("active");
        delete open_ids[id];
    }
    else {
        makeSubtable(table, row_node, url);
        $i.removeClass("icon-caret-right");
        $i.addClass("icon-caret-down");
        $i.parents("div").first().addClass("active");
        open_ids[id] = true;
    }
}

var prev_filter = "";

function refilterOpenRows(table, $table) {
    var new_filter = $table.parents(".dataTables_wrapper").first()
            .find(".dataTables_filter input").val();
    if (prev_filter !== new_filter) {
        var rows = table.fnGetNodes();
        for(var i = 0, limit = rows.length; i < limit; ++i) {
            var row_node = rows[i];
            if (table.fnIsOpen(row_node)) {
                var $subtable = $(row_node).next("tr").find(".primary-source-table");
                var subtable = $subtable.dataTable();
                subtable.fnFilter(new_filter);
            }
        }
        prev_filter = new_filter;
    }
}


function setFormFields() {
    var $textarea = $body.find("textarea");
    $textarea.one("keypress", function (ev) {
        if(ev.which == 10 || ev.which == 13) {
            $primary.click();
            return false;
        }
        return true;
    });
    // Let the current event finish before setting the focus.
    setTimeout(function () {
        $textarea[0].focus();
    }, 0);
}

return function ($table, options) {
    var emptytext = '[No title assigned.]';

    if (options.selectable) {
        $table.find("tbody").on("click", "tr", function (ev) {
            var $this = $(this);
            $this.siblings("tr").removeClass('selected-row');
            $this.addClass('selected-row');
            $table.trigger("selected-row");
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
            [4, 'asc']
        ],
        aoColumnDefs: [
            {
                aTargets: [0, 1, 2],
                bVisible: false
            },
            {
                aTargets: [2],
                bSortable: false,
            },
            {
                aTargets: [3],
                bSortable: false,
                mRender: function (data, type, row_data) {
                    var children = Number(row_data[2]);
                    return buttons_template({children: children});
                },
                fnCreatedCell: function (cell, data, row, row_ix, col_ix) {
                    var $cell = $(cell);
                    $cell.css("white-space", "nowrap");
                    var subtable_url = row[1];
                    var $open = $cell.children("div").eq(1);
                    var $i = $open.children("i");
                    $open.click(function () {
                        var row_node = $open.parents("tr")[0];
                        openOrCloseRow(table, row_node, $i, subtable_url,
                                       row[0]);
                    });

                    var add_url = row[col_ix];
                    var $add = $cell.children("div").first();
                    $add.click(function () {
                        $body.load(add_url, function () {
                            setFormFields();
                            $primary.one("click", function () {
                                $.ajax({
                                    url: add_url,
                                    type: "POST",
                                    data: $modal.find("form").serialize(),
                                    success: function () {
                                        $modal.modal("hide");
                                        table.fnDraw(false);
                                    },
                                    error: function errorHandler(jqXHR) {
                                        $body.html(jqXHR.responseText);
                                    }
                                });
                            });
                            $modal.modal();
                        });
                    });
                }
            }
        ],
        fnCreatedRow: function (row_node, data, data_index) {
            var $row_node = $(row_node);
            // Move the item key to a data attribute.
            var id = data[0];
            var url = data[1];
            var $i = $row_node.children("td").eq(0).find("i").eq(1);
            if (open_ids[id])
                openOrCloseRow(table, row_node, $i, url, id);
            $row_node.attr("data-item-key", id);
        },
        fnDrawCallback: function (options) {
            refilterOpenRows(table, $table);
            $table.trigger("refresh-results");
        }
    });

    var old_fnFilter = table.fnFilter;
    table.fnFilter = function () {
        old_fnFilter.apply(this, arguments);
    };

    $table.data("title-table", table);

    var $hide_all = $table.find(".hide-all-ps");
    var $show_all = $table.find(".show-all-ps");

    $hide_all.click(function () {
        var rows = table.fnGetNodes();
        for(var i = 0, limit = rows.length; i < limit; ++i) {
            var row_node = rows[i];
            if (table.fnIsOpen(row_node)) {
                var $i = $(row_node).children("td").eq(0).find("i").eq(1);
                // We're going to close it so the last 2 arguments are
                // not needed.
                openOrCloseRow(table, row_node, $i, undefined, undefined);
            }
        }
    });

    $show_all.click(function () {
        var rows = table.fnGetNodes();
        for(var i = 0, limit = rows.length; i < limit; ++i) {
            var row_node = rows[i];
            var data = table.fnGetData(i);
            if (Number(data[2]) > 0 && !table.fnIsOpen(row_node)) {
                var $i = $(row_node).children("td").eq(0).find("i").eq(1);
                openOrCloseRow(table, row_node, $i, data[1], data[0]);
            }
        }
    });



    return table;
};

});
