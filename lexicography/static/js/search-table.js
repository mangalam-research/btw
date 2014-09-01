define(['jquery', 'jquery.cookie', 'datatables.bootstrap'], function ($) {

var csrftoken = $.cookie('csrftoken');

return function ($table, options) {
    var table = $table.dataTable({
        iDisplayLength: options.rows || undefined,
        bLengthChange: (options.rows === undefined),
        bProcessing: true,
        bServerSide: true,
        bAutoWidth: false,
        sAjaxSource: options.ajax_source_url,
        fnServerParams: function (aoData) {
            aoData.push({"name": "bHeadwordsOnly",
                         "value": checkbox && checkbox.checked} );
        }
    });

    $table.data("search-table", table);

    var doc = $table[0].ownerDocument;
    var filter =
            doc.getElementById("search-table_wrapper")
            .getElementsByClassName("dataTables_filter")[0];
    var label = filter.ownerDocument.createElement("label");
    label.innerHTML = 'Headwords only: <input type="checkbox" class="form-control input-sm"></input>';
    var checkbox = label.lastElementChild;
    filter.appendChild(doc.createTextNode(" "));
    filter.appendChild(label);
    $(checkbox).change(function () {
        table.fnDraw();
    });

    return table;
};

});
