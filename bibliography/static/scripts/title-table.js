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
<% if (edit) { %>\
<div class='btn btn-default btn-sm add-button'><i class='fa fa-plus'></i></div>\
<% } %>\
<div style='position: relative' \
     class='btn <% print(children ? 'btn-default ':'') %>btn-sm open-close-button'>\
  <i class='fa fa-fw \
            <% print(children ? 'fa-caret-right': '') %>'></i>\
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

function makeSubtable(table, options, row_node, url) {
    var $new_row = $(table.fnOpen(row_node, subtable_template, "subtable"));
    var $subtable = $new_row.find("table").first();
    $new_row.children("td").attr("colspan", "2");
    $new_row.prepend("<td colspan='1'></td>");

    var aoColumnDefs = [];
    if (options.can_edit) {
        aoColumnDefs.push({
            aTargets: [0],
            bSortable: false,
            mRender: function (data, type, row_data) {
                return '<div class="btn btn-default btn-sm edit-button"><i class="fa fa-edit"></i></div>';
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
        });
    }
    else {
        // We can't edit so the first column is not visible.
        aoColumnDefs.push({
            aTargets: [0],
            bSortable: false,
            bVisible: false
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
            [1, 'asc']
        ],
        aoColumnDefs: aoColumnDefs,
        fnCreatedRow: function (row_node, data, data_index) {
            // Move the item key to a data attribute.
            $(row_node).attr("data-item-url", data[0]);
        },
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

function openOrCloseRow(table, options, row_node, $i, url, id) {
    if (table.fnIsOpen(row_node)) {
        table.fnClose(row_node);
        $i.removeClass("fa-caret-down");
        $i.addClass("fa-caret-right");
        $i.parents("div.open-close-button").removeClass("active");
        delete open_ids[id];
    }
    else {
        makeSubtable(table, options, row_node, url);
        $i.removeClass("fa-caret-right");
        $i.addClass("fa-caret-down");
        $i.parents("div.open-close-button").addClass("active");
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
            if ($this.find("tbody>tr").length === 0) {
                $table.find("tbody>tr").removeClass('selected-row');
                $this.siblings("tr").removeClass('selected-row');
                $this.addClass('selected-row');
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
                    return buttons_template({children: children,
                                             edit: options.can_edit});
                },
                fnCreatedCell: function (cell, data, row, row_ix, col_ix) {
                    var $cell = $(cell);
                    $cell.css("white-space", "nowrap");
                    var subtable_url = row[1];
                    var $open = $cell.children("div.open-close-button");
                    var $i = $open.children("i");
                    $open.click(function () {
                        var row_node = $open.parents("tr")[0];
                        openOrCloseRow(table, options, row_node, $i,
                                       subtable_url, row[0]);
                    });

                    var add_url = row[col_ix];
                    var $add = $cell.children("div.add-button");
                    $add.click(function () {
                        $body.load(add_url, function () {
                            setFormFields();
                            $primary.on("click", function () {
                                $.ajax({
                                    url: add_url,
                                    type: "POST",
                                    data: $modal.find("form").serialize(),
                                    success: function () {
                                        $modal.modal("hide");
                                        table.fnDraw(false);
                                        $primary.off("click");
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
            var url = data[0];
            var primary_sources_url = data[1];
            var $i = $row_node.children("td").eq(0).find("i").eq(1);
            if (open_ids[url])
                openOrCloseRow(table, options, row_node, $i,
                               primary_sources_url, url);
            // Move the item key to a data attribute.
            $row_node.attr("data-item-url", url);
        },
        fnDrawCallback: function () {
            refilterOpenRows(table, $table);
            $table.trigger("refresh-results");
        }
    });

    $table.data("title-table", table);

    var $hide_all = $table.find(".hide-all-ps");
    var $show_all = $table.find(".show-all-ps");

    $hide_all.click(function () {
        var rows = table.fnGetNodes();
        for(var i = 0, limit = rows.length; i < limit; ++i) {
            var row_node = rows[i];
            var data = table.fnGetData(i);
            if (table.fnIsOpen(row_node)) {
                var $i = $(row_node).children("td").eq(0).find("i").eq(1);
                openOrCloseRow(table, options, row_node, $i, data[1], data[0]);
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
                openOrCloseRow(table, options, row_node, $i, data[1], data[0]);
            }
        }
    });



    return table;
};

});
