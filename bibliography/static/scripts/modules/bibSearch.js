define(["jquery", "jquery.cookie"], function ($) {

var bibSearch = function () {

    var csrftoken = $.cookie('csrftoken');

    var headers =  {
        'X-CSRFToken': csrftoken
    };

    function refreshResults(data) {
        var $result_list = $("#result_list");
        $result_list.html(data);

        // add jquery selector for the new sync buttons.
        $result_list.find(".bibsearch-copy").click(function () {
            ajaxSync(this.name);
        });

        $result_list.find("a").click(function () {
            ajaxResult(this.name);
        });

        $result_list.trigger("bibsearch-refresh-results");
    }

    function ajaxResult(pageNumber) {
        var dataString = "page=" + pageNumber;
        $.ajax({
            url: '/bibliography/results/',
            data: dataString,
            headers: headers
        }).done(refreshResults);
    }

    function ajaxSync(encString) {
        var dataString = "enc=" + encString;
        $.ajax({
            type: "POST",
            url: '/bibliography/sync/',
            data: dataString,
            headers: headers,
            beforeSend: function () {
                $('#loading').css('display', 'inline');
                return true;
            }
        }).done(function (data) {
            // remove the button which was clicked
            // to sync information
            var parentObject = $("[" + "name='" +
                                 encString + "']").parent();
            parentObject.html("NA");
            if (data == "OK") {
                alert("Copy successful!.");
            } else if (data == "DUP") {
                alert("Duplicate item not copied.");
            } else {
                alert(data);
            }
        }).always(function () {
            $('#loading').css('display', 'none');
        });
    }

    // create a ajax search call
    this.ajaxSearch = function () {
        var dataString = "library=" + $('#id_library').val() + "&keyword=" +
                $('#id_keyword').val();
        $.ajax({
            type: "POST",
            url: '/bibliography/exec/',
            data: dataString,
            headers: headers,
            beforeSend: function () {
                $('#loading').css('display', 'inline');
                return true;
            }
        }).done(refreshResults).always(function () {
            $('#loading').css('display', 'none');
        });
    };
};

return bibSearch;

});
