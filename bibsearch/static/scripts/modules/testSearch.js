define(["jquery"], function (jQuery) {
    return {
        SearchTests: function () {
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

            test("Search Ajax with no data[URL:/search/, response: 500:INTERNAL SERVER ERROR]", function () {
                expect(3);
                QUnit.stop();
                var dataString = "";
                callAjx('/search/', dataString, function (a, b, c) {
                    // we assert the result coming from ajax here
                    QUnit.start();
                    // server error assertion.
                    equal(a.status, 500, "500 response code");
                    equal(a.responseText, "Form data empty.", "search view response text");
                    equal(c, "INTERNAL SERVER ERROR", "HTTP response text");
                });
            });

            test("Search Ajax with invalid data[URL:/search/, response: 500:INTERNAL SERVER ERROR]", function () {
                expect(3);
                QUnit.stop();
                var dataString = "library=&keyword=";
                callAjx('/search/', dataString, function (a, b, c) {
                    // server error assertion.
                    QUnit.start();
                    equal(a.status, 500, "500 response code");
                    equal(a.responseText, "Malformed form data.", "search view response text");
                    equal(c, "INTERNAL SERVER ERROR", "HTTP response text");
                });
            });

            test("Search Ajax with out-of-bound data[URL:/search/, response: 200:OK(Zero results)]", function () {
                expect(4);
                QUnit.stop();
                var dataString = "library=6&keyword=";
                callAjx('/search/', dataString, function (a, b, c) {
                    // server success assertion.
                    QUnit.start();
                    equal(c.status, 200, "200 response code");
                    equal(c.statusText, "OK", "search view response text");
                    equal(b, "success", "HTTP status text");
                    // last assertion for checking no results returned
                    var results = true;
                    var regex = /Showing results: 0 to 0 of/g;
                    if (regex.exec(a)) {
                        results = false;
                    }
                    equal(results, false, "Zero results returned");
                });
            });

            test("Search Ajax with regular data[URL:/search/, response: 200:OK]", function () {
                expect(3);
                QUnit.stop();
                // search everything in user library
                var dataString = "library=2&keyword=";
                callAjx('/search/', dataString, function (a, b, c) {
                    // server success assertion.
                    QUnit.start();
                    equal(c.status, 200, "200 response code");
                    equal(c.statusText, "OK", "search view response text");
                    equal(b, "success", "HTTP status text");
                });
            });

        }
    }
});
