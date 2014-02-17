define(['module', 'jquery', 'jquery.cookie', 'datatables',
        'bootstrap-editable'],
       function (module, $) {
    $(document).ready(function() {
        var csrftoken = $.cookie('csrftoken');
        var table = $('#bibliography-table').dataTable({
            bProcessing: true,
            bServerSide: true,
            sAjaxSource: module.config().ajax_source_url,
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
                        $(cell).children("span").editable(
                            {mode: 'inline',
                             send: 'always',
                             url: full[0],
                             ajaxOptions: {
                                 headers: {
                                     'X-CSRFToken': csrftoken
                                                               }
                             },
                             success: function () {
                                 table.fnDraw();
                             },
                             emptytext: '[No title assigned.]'
                            });
                    }
                }
            ]
        });
    });
});
