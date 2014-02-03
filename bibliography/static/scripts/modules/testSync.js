define(["jquery", "jquery.cookie"], function ($) {
var root = '/bibliography/';
return {
    SyncTests: function () {
        // tests follow the following testing procedure
        // http://benalman.com/talks/unit-testing-qunit.html#42
        // Ajax are mocked here.

        var csrftoken = $.cookie('csrftoken');

        var headers =  {
            'X-CSRFToken': csrftoken
        };

        function callAjx(url, data, callback) {
            $.ajax({
                type: "POST", // sync calls always require POST
                url: url,
                data: data,
                headers: headers
            }).always(callback);
        }

        test("Sync Ajax with no data[URL:<root>sync/, "+
             "response: 500:INTERNAL SERVER ERROR]", function () {
            expect(3);
            QUnit.stop();
            var dataString = "";
            callAjx(root + 'sync/', dataString,
                    function (jqXHR, textStatus, errorThrown) {
                // we assert the result coming from ajax here
                QUnit.start();
                // server error assertion.
                equal(jqXHR.status, 500, "500 response code");
                equal(jqXHR.responseText,
                      "ERROR: sync data i/o error.",
                      "search view response text");
                equal(errorThrown, "INTERNAL SERVER ERROR",
                      "HTTP response text");
            });
        });

        test("Sync Ajax with invalid data[URL:<root>sync/, "+
             "response: 500:INTERNAL SERVER ERROR]", function () {
            expect(3);
            QUnit.stop();
            var dataString = "enc=";
            callAjx(root + 'sync/', dataString,
                    function (jqXHR, textStatus, errorThrown) {
                // server error assertion.
                QUnit.start();
                equal(jqXHR.status, 500, "500 response code");
                equal(jqXHR.responseText,
                      "Error: malformed data cannot be copied.",
                      "search view response text");
                equal(errorThrown, "INTERNAL SERVER ERROR",
                      "HTTP response text");
            });
        });

        test("Sync Ajax with out-of-bound data[URL:<root>sync/, "+
             "response: 200:'OK'(item not found)]", function () {
            expect(3);
            QUnit.stop();
            var dataString = "enc=AAJJAAXX9900";
            callAjx(root + 'sync/', dataString,
                    function (data, textStatus, jqXHR) {
                // server success assertion.
                QUnit.start();
                equal(jqXHR.status, 200, "200 response code");
                equal(jqXHR.responseText,
                      "Error: Item not in result database.",
                      "search view response text");
                equal(jqXHR.statusText, "OK", "HTTP response text");
            });
        });
    }
};

});
