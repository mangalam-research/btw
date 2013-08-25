define(["jquery", ], function (jQuery) {
    return {
        SyncTests: function () {
            // tests follow the following testing procedure
            // http://benalman.com/talks/unit-testing-qunit.html#42
            // Ajax are mocked here.
            function callAjx(url, data, callback) {
                jQuery.ajax({
                    url: url,
                    context: document.body,
                    data: data,
                }).always(function (a, b, c) {
                    // return the response
                    // jqXHR.always(function(data|jqXHR, textStatus, jqXHR|errorThrown) { });
                    callback(a, b, c);
                });
            }

            test("Sync Ajax with no data[URL:/search/sync/, response: 500:INTERNAL SERVER ERROR]", function () {
                expect(3);
                QUnit.stop();
                var dataString = "";
                callAjx('/search/sync/', dataString, function (a, b, c) {
                    // we assert the result coming from ajax here
                    QUnit.start();
                    // server error assertion.
                    equal(a.status, 500, "500 response code");
                    equal(a.responseText, "ERROR: sync data i/o error.", "search view response text");
                    equal(c, "INTERNAL SERVER ERROR", "HTTP response text");
                });
            });

            test("Sync Ajax with invalid data[URL:/search/sync/, response: 500:INTERNAL SERVER ERROR]", function () {
                expect(3);
                QUnit.stop();
                var dataString = "enc=";
                callAjx('/search/sync/', dataString, function (a, b, c) {
                    // server error assertion.
                    QUnit.start();
                    equal(a.status, 500, "500 response code");
                    equal(a.responseText, "Error: malformed data cannot be copied.", "search view response text");
                    equal(c, "INTERNAL SERVER ERROR", "HTTP response text");
                });
            });

            test("Sync Ajax with out-of-bound data[URL:/search/sync/, response: 200:'OK'(item not found)]", function () {
                expect(3);
                QUnit.stop();
                var dataString = "enc=AAJJAAXX9900";
                callAjx('/search/sync/', dataString, function (a, b, c) {
                    // server success assertion.
                    QUnit.start();
                    equal(c.status, 200, "200 response code");
                    equal(c.responseText, "Error: Item not in result database.", "search view response text");
                    equal(c.statusText, "OK", "HTTP response text");
                });
            });
        }
    }
});