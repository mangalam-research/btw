define(["jquery", "jquery.cookie", "jquery.bootstrap-growl"], function ($) {

return function(initiate_url, check_url) {
    var span = document.getElementById("btw-prev-refreshed");
    var table_el = document.getElementById("bibliography-table");
    var button = document.getElementById("btw-refresh");
    var icon = button.getElementsByTagName("i")[0];
    var csrftoken = $.cookie('csrftoken');

    function working() {
        icon.classList.add("fa-spin");
        button.disabled = true;
    }

    function idle() {
        icon.classList.remove("fa-spin");
        button.disabled = false;
    }

    function growl(message, type) {
        $.bootstrapGrowl(message, {
            ele: 'body',
            type: type,
            offset: {from: 'top', amount: 20},
            align: 'center',
            width: 'auto',
            delay: 4000,
            allow_dismiss: true,
            stackup_spacing: 10
        });
    }

    function failed(jqXHR) {
        idle();
        growl("Refresh failed. Please contact technical support.", "danger");
    }

    $(button).on("click", function (ev) {
        working();
        $.ajax({
            url: initiate_url,
            type: "POST",
            headers: {
                'X-CSRFToken': csrftoken,
                Accept: "application/json"
            }
        }).done(function (data) {
            var last = data;
            function check () {
                $.ajax({
                    url: check_url,
                    type: "GET",
                    headers: {
                        Accept: "application/json"
                    }
                }).done(function (data) {
                    var now = data;
                    if (now === last)
                        setTimeout(check, 500);
                    else {
                        idle();
                        span.textContent = data;
                        var table = $.data(table_el, "title-table");
                        if (table)
                            table.fnDraw();
                        growl("Refreshed!", "success");
                    }

                }).fail(failed);
            }
            check();
        }).fail(failed);
    });
};

});
