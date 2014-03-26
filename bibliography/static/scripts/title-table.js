define(['jquery', 'jquery.cookie', 'datatables', 'bootstrap-editable'],
       function ($) {
return function ($table, options) {
    var csrftoken = $.cookie('csrftoken');
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
            [3, 'asc']
        ],
        aoColumnDefs: [
            {
                aTargets: [0, 1],
                bVisible: false
            },
            {
                aTargets: [2],
                mRender: function (data) {
                    if (data === null || data === undefined)
                        data = "";
                    return "<span>" + data + "</span>";
                },
                fnCreatedCell: function (cell, type, full) {
                    var $span = $(cell).children("span").first();
                    if (options.can_edit)
                        $span.editable(
                            {mode: 'inline',
                             send: 'always',
                             url: full[1],
                             ajaxOptions: {
                                     headers: {
                                         'X-CSRFToken': csrftoken
                                     }
                                 },
                             success: function () {
                                 table.fnDraw(false);
                             },
                             emptytext: emptytext
                            });
                    else if ($span.text() === "") {
                        $span.text(emptytext);
                        // We just apply the same class that
                        // x-editable would use.
                        $span.addClass("editable-empty");
                    }
                }
            }
        ],
        fnCreatedRow: function (row, data, data_index) {
            // Move the item key to a data attribute.
            $(row).attr("data-item-key", data[0]);
        },
        fnDrawCallback: function () {
            $table.trigger("refresh-results");
        }
    });
    $table.data("title-table", table);
    return table;
};

});
