define(['module', 'jquery', 'datatables'], function (module, $) {
    $(document).ready(function() {
        $('#bibliography-table').dataTable({
            bProcessing: true,
            bServerSide: true,
            sAjaxSource: module.config().ajax_url
        });
    });
});
