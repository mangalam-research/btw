define(["jquery", "jquery.cookie"], function ($) {
    var root = '/bibliography/';
    return {
        SearchTests: function () {
            // tests follow the following testing procedure
            // http://benalman.com/talks/unit-testing-qunit.html#42
            // Ajax are mocked here.

            var csrftoken = $.cookie('csrftoken');

            var headers =  {
                'X-CSRFToken': csrftoken
            };

            function callAjx(type, url, data, callback) {
                $.ajax({
                    type: type,
                    url: url,
                    data: data,
                    headers: headers
                }).always(callback);
            }

            test("Search Ajax with no data[URL:/bibliography/exec, "+
                 "response: 500:INTERNAL SERVER ERROR]", function () {
                expect(3);
                QUnit.stop();
                var dataString = "";
                callAjx("POST", root + 'exec/', dataString,
                        function (jqXHR, textStatus, errorThrown) {
                    // we assert the result coming from ajax here
                    QUnit.start();
                    // server error assertion.
                    equal(jqXHR.status, 500, "500 response code");
                    equal(jqXHR.responseText, "cannot interpret form data.",
                          "search view response text");
                    equal(errorThrown, "INTERNAL SERVER ERROR",
                          "HTTP response text");
                });
            });

            test("Search Ajax with invalid data[URL:/bibliography/exec, "+
                 "response: 500:INTERNAL SERVER ERROR]", function () {
                expect(3);
                QUnit.stop();
                var dataString = "library=&keyword=";
                callAjx("POST", root + 'exec/', dataString,
                        function (jqXHR, textStatus, errorThrown) {
                    // server error assertion.
                    QUnit.start();
                    equal(jqXHR.status, 500, "500 response code");
                    equal(jqXHR.responseText, "Malformed form data.",
                          "search view response text");
                    equal(errorThrown, "INTERNAL SERVER ERROR",
                          "HTTP response text");
                });
            });

            test("Search Ajax with out-of-bound data[URL:<root>exec, "+
                 "response: 200:OK(Zero results)]", function () {
                expect(4);
                QUnit.stop();
                var dataString = "library=6&keyword=";
                callAjx("POST", root + 'exec/', dataString,
                        function (data, textStatus, jqXHR) {
                    // server success assertion.
                    QUnit.start();
                    equal(jqXHR.status, 200, "200 response code");
                    equal(jqXHR.statusText, "OK", "search view response text");
                    equal(textStatus, "success", "HTTP status text");
                    // last assertion for checking no results returned
                    var regex = /Showing results: 0 to 0 of/g;
                    var results = !regex.exec(data);
                    equal(results, false, "Zero results returned");
                });
            });

            test("Search Ajax with regular data[URL:/bibliography/search/, "+
                 "response: 200:OK]", function () {
                expect(3);
                QUnit.stop();
                // search everything in user library
                var dataString = "library=2&keyword=";
                callAjx("GET", '/bibliography/search/', dataString,
                        function (data, textStatus, jqXHR) {
                    // server success assertion.
                    QUnit.start();
                    equal(jqXHR.status, 200, "200 response code");
                    equal(jqXHR.statusText, "OK", "search view response text");
                    equal(textStatus, "success", "HTTP status text");
                });
            });

        }
    }
});
