define(['module', 'jquery', 'jquery.cookie', 'datatables',
        'bootstrap-editable'],
       function (module, $) {
var config = module.config();

$(function() {
    var csrftoken = $.cookie('csrftoken');
    var emptytext = '[No title assigned.]';

    var table = $('#bibliography-table').dataTable({
        bProcessing: true,
        bServerSide: true,
        sAjaxSource: config.ajax_source_url,
        aaSorting: [
            [2, 'asc']
        ],
        aoColumnDefs: [
            {
                aTargets: [0],
                bVisible: false
            },
            {
                aTargets: [1],
                mRender: function (data) {
                    if (data === null || data === undefined)
                        data = "";
                        return "<span>" + data + "</span>";
                },
                fnCreatedCell: function (cell, type, full) {
                    var $span = $(cell).children("span").first();
                    if (config.can_edit)
                        $span.editable(
                            {mode: 'inline',
                             send: 'always',
                             url: full[0],
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
        ]
    });
});

});
