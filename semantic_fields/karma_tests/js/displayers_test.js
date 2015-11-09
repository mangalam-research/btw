define(["jquery", "sinon", "js/displayers", "velocity", "bluebird"],
       function ($, sinon, displayers, velocity, bluebird) {

var Promise = bluebird.Promise;
var assert = chai.assert;
var Displayers = displayers.Displayers;

function assertAnimated(el, desc) {
    assert.isTrue(!!$.data(el, "velocity"),
                  desc + " should have been animated");
}

function assertNotAnimated(el, desc) {
    assert.isNull($.data(el, "velocity"),
                  desc + " should not have been animated");
}

function clearAnimationInfo(el) {
    $.data(el, "velocity", null);
}

function promiseFromEvent(el, event) {
    return new Promise(function (resolve) {
        $(el).one(event, function () {
            resolve(Array.prototype.slice.call(arguments));
        });
    });
}

var DONE = {};

var it = function it(title, fn) {
    if (fn.length)
        throw new Error("you must update your it replacement to support " +
                        "the done callback or use a promise instead");
    return window.it.call(this, title, function () {
        var ret = fn();
        assert.isDefined(ret,
                         "you forgot to return a value from your test");
        if (!ret.then)
            return ret;

        return ret.then(function (x) {
            assert.equal(x, DONE,
                         "your test must return a promise that resolves " +
                         "to DONE");

        });
    });
};

it.only = window.it.only;

function eventually(cb, message, timeout) {
    timeout = (timeout === undefined) ? 1000: timeout;
    return new Promise(function (resolve, reject) {
        var start = Date.now();
        function check() {
            if (cb())
                resolve(true);
            if (Date.now() - start > timeout)
                reject(new Error(message));

            setTimeout(check, 200);
        }
        check();
    });
}

describe("", function () {
    var template;
    var server;
    before(function () {
        template = $(displayers.html_template)[0];
        document.body.insertBefore(template, null);

        // Remove the text content to help testing.
        template.getElementsByClassName("paged-content")[0].textContent = "";
        server = sinon.fakeServer.create();
        var blank_response = [200, { "Content-Type": "application/html" },
                              ''];
        server.respondWith("GET", "/blank", blank_response);
        server.respondWith("GET", "/blank2", blank_response);
        server.respondWith("GET", "/minimal",
                           [200, { "Content-Type": "application/html" },
                            '<p id="minimal">' +
                            '<a class="sf-link" href="/minimal2">/minimal2' +
                            '</a></p>']);
        server.respondWith("GET", "/minimal2",
                           [200, { "Content-Type": "application/html" },
                            '<p id="minimal2">minimal2</p>']);
        server.respondImmediately = true;


        // Make all animations be instantaneous so that we don't spend
        // seconds waiting for them to happen.
        velocity.mock = true;
    });

    after(function () {
        server.restore();
        document.body.removeChild(template);
        velocity.mock = false;
    });


    describe("Displayers", function () {
        var ds;
        beforeEach(function () {
            ds = new Displayers(template);
        });

        afterEach(function () {
            return ds.closeAll();
        });

        it("should construct a new Displayers object", function () {
            assert.equal(ds.displayers.length, 0,
                         "the object should have no displayers yet");
            assert.equal(ds.template, template,
                         "the object should have the proper template");
            return DONE;
        });

        describe("#closeAll()", function () {
            it("should work on an empty Displayers object", function () {
                ds.closeAll();
                assert.equal(ds.displayers.length, 0,
                             "the object should have no displayers");
                return DONE;
            });

            it("should empty a Displayers object", function () {
                return ds.open("/blank").then(function () {
                    return ds.open("/blank2");
                }).then(function () {
                    assert.equal(ds.displayers.length, 2,
                                 "the object should have 2 displayers");
                    return assert.eventually.equal(
                        ds.closeAll().get("displayers").get("length"),
                        0,
                        "the object should have no displayers").return(DONE);
                });
            });

            it("should be callable any number of times", function () {
                return ds.open("/blank").then(function () {
                    return ds.open("/blank2");
                }).then(function () {
                    return assert.eventually.equal(
                        ds.closeAll().get("displayers").get("length"),
                        0,
                        "the object should have no displayers");
                }).then(function () {
                    return ds.closeAll().return(DONE);
                });
            });

            it("should return a promise that resolves to the Displayers" +
               "on which it was called", function () {
                return ds.open("/blank").then(function () {
                    return assert.eventually.equal(
                        ds.closeAll(), ds,
                        "the resolved value should be the same as the object " +
                            "on which ``closeAll()`` was called")
                        .return(DONE);
                });
            });
        });

        describe("#open(url)", function () {
            it("should add a new Displayer to a new Displayers object",
               function () {
                assert.equal(ds.displayers.length, 0,
                             "the object should have no displayers");
                return ds.open("/blank").then(function () {
                    assert.equal(ds.displayers.length, 1,
                                 "the object should have 1 displayers");
                    return DONE;
                });
            });

            it("should animate the new Displayer added",
               function () {
                return ds.open("/blank").then(function () {
                    assertAnimated(ds.displayers[0].display_div,
                                   "the new Displayer");
                    return DONE;
                });
            });

            it("should add a new Displayer when the URL is not already shown",
               function () {
                assert.equal(ds.displayers.length, 0,
                             "the object should have no displayers");
                return ds.open("/blank").then(function () {
                    assert.equal(ds.displayers.length, 1,
                                 "the object should have 1 displayers");
                    return ds.open("/blank2");
                }).then(function () {
                    assert.equal(ds.displayers.length, 2,
                                 "the object should have 2 displayers");
                    return DONE;
                });
            });

            it("should not add a new Displayer when the URL is already shown",
               function () {
                assert.equal(ds.displayers.length, 0,
                             "the object should have no displayers");
                return ds.open("/blank").then(function () {
                    assert.equal(ds.displayers.length, 1,
                                 "the object should have 1 displayers");
                    return ds.open("/blank");
                }).then(function () {
                    assert.equal(ds.displayers.length, 1,
                                 "the object should have 1 displayers");
                    return DONE;
                });
            });


            it("should scroll into view the Display that already displays " +
               "the URL",
               function () {
                assert.equal(ds.displayers.length, 0,
                             "the object should have no displayers");
                return ds.open("/blank").then(function (d) {
                    assert.equal(ds.displayers.length, 1,
                                 "the object should have 1 displayers");
                    var div = d.display_div;
                    var mock_div = sinon.mock(div);
                    mock_div.expects("scrollIntoView").once();
                    return ds.open("/blank").then(function (d2) {
                        assert.equal(d, d2,
                                     "it should not have opened a new display");
                        assert.equal(ds.displayers.length, 1,
                                     "the object should have 1 displayers");
                        mock_div.verify();
                        return DONE;
                    }).finally(function () {
                        mock_div.restore();
                    });
                });
            });

            it("should animate the Display that already shows the URL",
               function () {
                return ds.open("/blank").then(function (d) {
                    clearAnimationInfo(d.display_div);
                    return ds.open("/blank");
                }).then(function (d) {
                    assertAnimated(d.display_div, "the Display");
                    return DONE;
                });
            });

            it("should display the URL's content",
               function () {
                assert.isNull(document.getElementById("minimal"),
                              "the element should not exist");
                return ds.open("/minimal").then(function () {
                    assert.isNotNull(document.getElementById("minimal"),
                                     "the element should exist");
                    return DONE;
                });
            });

            it("should generate an open.displayers event on the template " +
               "with the new display as parameter",
               function () {
                var p = promiseFromEvent(template, "open.displayers");
                ds.open("/blank");
                return p.spread(function (ev, param) {
                    assert.equal(ds.displayers[0], param,
                                 "param should be the displayer");
                    return DONE;
                });
            });

            it("should create a Displayer that has the right " +
               "``displayers`` value",
               function () {
                return assert.eventually.equal(
                    ds.open("/blank").get("displayers"), ds,
                    "the ``displayers`` field should be the object " +
                        "that created the Displayer object")
                    .return(DONE);
            });

            it("should create a Displayer whose display_div is just before " +
               "the template",
               function () {
                return assert.eventually.equal(
                    ds.open("/blank").get("display_div").get("nextSibling"),
                    template,
                    "the display_div should be before the template")
                    .return(DONE);
            });

            it("should create a Displayer whose display_div is based on " +
               "the template",
               function () {
                return ds.open("/blank").then(function (d) {
                    var template_els =
                        Array.prototype.map.call(
                            template.querySelectorAll("*"),
                            function (el) { return el.tagName; });

                    var div_els =
                        Array.prototype.map.call(
                            d.display_div.querySelectorAll("*"),
                            function (el) { return el.tagName; });

                    assert.sameMembers(
                        div_els,
                        template_els,
                        "the display_div be based on the template");
                    return DONE;
                });
            });

            it("should create a Displayer whose url is the one passed " +
               "to ``open``",
               function () {
                return assert.eventually.equal(
                    ds.open("/blank").get("url"),
                    "/blank",
                    "the display_div be based on the template")
                    .return(DONE);
            });

        });

    });

    describe("Displayer", function () {
        var ds;
        var first;
        beforeEach(function () {
            ds = new Displayers(template);
            return ds.open("/blank").then(function (d) {
                first = d;
                return d;
            });
        });

        afterEach(function () {
            return ds.closeAll();
        });

        describe("#closeAll()", function () {
            it("should close all Displayer objects associated with parent " +
               "Displayers object", function () {
                return ds.open("/blank2").then(function () {
                    assert.equal(ds.displayers.length, 2,
                                 "there should be two displayers");
                    var displayers_copy = ds.displayers.slice();
                    return ds.displayers[0].closeAll().then(function () {
                        assert.equal(ds.displayers.length, 0,
                                     "there should be no displayers");
                        for (var ix = 0, d; (d = displayers_copy[ix]); ++ix) {
                            assert.isTrue(d.closed,
                                          "the displayer should be destroyed");
                        }
                        return DONE;
                    });
                });

            });

            it("should be callable multiple times", function () {
                return ds.open("/blank2").then(function () {
                    assert.equal(ds.displayers.length, 2,
                                 "there should be two displayers");
                    return assert.eventually.equal(
                        first.closeAll().get("displayers").get("length"),
                        0,
                        "there should be no displayers");
                }).then(function () {
                    return first.closeAll().return(DONE);
                });
            });

            it("should return a promise that resolves to the " +
               "parent Displayers object", function () {
                return assert.eventually.equal(
                    first.closeAll(), ds,
                    "the resolved value should be the parent Displayers " +
                        "object").return(DONE);

            });
        });

        describe("#close()", function () {
            it("should mark the Displayer object as closed", function () {
                assert.isFalse(first.closed,
                              "the displayer should not be marked closed");
                return assert.eventually.isTrue(
                    first.close().get("closed"),
                    "the displayer should be marked closed").return(DONE);
            });

            it("should return a Promise that resolves to the " +
               "displayer being closed", function () {
                return assert.eventually.equal(
                    first.close(), first,
                    "the resolved value should be the displayer being closed")
                    .return(DONE);
            });

            it("should be callable multiple times", function () {
                return assert.eventually.equal(
                    first.close().call("close"), first,
                    "the resolved value should be the displayer being closed")
                    .return(DONE);
            });

            it("should remove the Displayer from the DOM", function () {
                assert.isNotNull(first.display_div.parentNode,
                                "the display_div should be in the DOM");
                return assert.eventually.isNull(
                    first.close().get("display_div").get("parentNode"),
                    "the display_div should no longer be in the DOM")
                    .return(DONE);
            });

            it("should trigger a ``closed.displayer`` event on the " +
               "display_div with the Displayer object as parameter",
               function () {
                var p = promiseFromEvent(first.display_div, "closed.displayer");

                first.close();
                return p.spread(function (ev, displayer) {
                    assert.equal(displayer, first,
                                 "the parameter should be the Displayer " +
                                 "being closed");
                }).return(DONE);
            });

            it("should trigger a ``closed.displayer`` event only once " +
               "even if called multiple times",
               function () {
                var cb = sinon.spy();
                $(first.display_div).on("closed.displayer", cb);
                return first.close().then(function () {
                    assert.isTrue(cb.calledOnce,
                                  "the event handler should have been " +
                                  "called once");
                    return first.close();
                }).then(function () {
                    assert.isTrue(cb.calledOnce,
                                  "the event handler should have been " +
                                  "called once");
                    return DONE;
                });
            });

            it("should animate the display_div",
               function () {
                clearAnimationInfo(first.display_div);
                return first.close().then(function () {
                    assertAnimated(first.display_div, "the Displayer");
                    return DONE;
                });
            });
        });

        describe("#display(url)", function () {
            it("should cause the Displayer to display the new contents",
               function () {
                assert.isNull(document.getElementById("minimal"),
                              "the contents should not yet be present");
                return first.display("/minimal").then(function () {
                    assert.isNotNull(document.getElementById("minimal"),
                                     "the contents should have been loaded");
                    return DONE;
                });
            });

            it("should cause the Displayer to change the current URL",
               function () {
                return assert.eventually.equal(
                    first.display("/minimal").get("url"),
                    "/minimal",
                    "the URL should be what was passed to ``display()``")
                    .return(DONE);
            });

            it("should cause the Displayer to record history",
               function () {
                var original = first.history.length;
                return assert.eventually.equal(
                    first.display("/minimal").get("history").get("length"),
                    original + 1,
                    "the history should have increased")
                    .return(DONE);
            });


            it("should cause the Displayer to scrap the history tail",
               function () {
                return first.display("/blank2").then(function () {
                    var p = promiseFromEvent(first.display_div,
                                             "refresh.displayer");

                    first.first();
                    return p;
                }).then(function () {
                    return first.display("/minimal");
                }).then(function () {
                    assert.equal(
                        first.history.length, 2,
                        "the length of the history should be 1");
                    return DONE;
                });
            });

            it("should cause the Displayer content to be animated",
               function () {
                clearAnimationInfo(first.content);
                return first.display("/minimal").then(function () {
                    assertAnimated(first.content, "the Display");
                    return DONE;
                });
            });

            it("should cause a ``refresh.displayer`` event on the " +
               "``display_div``",
               function () {
                var p = promiseFromEvent(first.display_div, "refresh.displayer")
                    .spread(function (ev, d, url) {
                        assert.equal(d, first,
                                     "the display parameter should be the " +
                                     "displayed being refreshed");
                        assert.equal(url, "/minimal",
                                     "the url parameter should be the URL " +
                                     "just displayed");
                        return DONE;

                    });
                first.display("/minimal");
                return p;
            });

            it("should be a no-op if the URL is the same as what was " +
               "already displayed",
               function () {
                var original = first.history.length;
                clearAnimationInfo(first.content);
                var $div = $(first.display_div);
                var cb = sinon.spy();
                $div.one("refresh.displayer", cb);
                return first.display("/blank").then(function () {
                    assert.equal(first.history.length, original,
                                 "the history should not have increased");
                    assertNotAnimated(first.content, "the Display");
                    assert.equal(cb.callCount, 0,
                                 "there should not have been a " +
                                 "``refresh.displayer`` event");
                    return DONE;
                });
            });

            it("should throw if called on a closed Displayer", function () {
                return ds.closeAll().then(function () {
                    return assert.isRejected(
                        first.display("/blank"),
                        "trying to display a URL on a closed Displayer")
                        .return(DONE);
                });
            });

            it("should throw if called on a Displayer which is no " +
               "longer in the DOM", function () {
                return ds.closeAll().then(function () {
                    // Yes, we cheat. There is currently no way for a Displayer
                    // to be closed but still in the DOM.
                    first._closed = false;
                    return assert.isRejected(
                        first.display("/blank"),
                        "trying to display a URL on a Displayer which is " +
                            "not in the DOM")
                        .return(DONE);
                });
            });

            it("should provide a useful rejection on failure",
               function () {
                return assert.isRejected(first.display("/bad"))
                    .then(function (err) {
                        assert.equal(err.constructor, Error);
                        assert.equal(err.message,
                                     "the loading of the new URL failed");
                        assert.equal(err.jqXHR.status, 404,
                                     "the error has status 404");
                        return DONE;
                    });
            });
        });

        describe("#first()", function () {
            it("should display the first item in history", function () {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id before we display the 2nd URL");
                return first.display("/minimal").call("display", "/minimal2")
                    .then(function () {
                        assert.isNotNull(
                            document.getElementById("minimal2"),
                            "there should be an element with the " +
                                "``minimal2`` id after we display the " +
                                "2nd URL");
                        return first.first();
                    }).then(function () {
                        assert.isNull(
                            document.getElementById("minimal2"),
                            "there should be no element with the " +
                                "``minimal2`` id after calling ``first``");
                        assert.isNull(
                            document.getElementById("minimal"),
                            "there should be no element with the " +
                                "``minimal`` id after calling ``first``");
                        assert.equal(
                            first.url, "/blank",
                            "the URL shown by the displayer should be " +
                                "the first URL in the history");
                        return DONE;
                    });
            });

            it("should be a noop if already first in history", function () {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id before we display the 2nd URL");
                var cb = sinon.spy();
                return first.display("/minimal").call("display", "/minimal2")
                    .then(function () {
                        assert.isNotNull(
                            document.getElementById("minimal2"),
                            "there should be an element with the " +
                                "``minimal2`` id after we display the " +
                                "2nd URL");
                        return first.first();
                    }).then(function () {
                        assert.isNull(
                            document.getElementById("minimal2"),
                            "there should be no element with the " +
                                "``minimal2`` id after calling ``first``");
                        assert.isNull(
                            document.getElementById("minimal"),
                            "there should be no element with the " +
                                "``minimal`` id after calling ``first``");
                        assert.equal(
                            first.url, "/blank",
                            "the URL shown by the displayer should be " +
                                "the first URL in the history");
                        $(first.display_div).one("refresh.displayer", cb);
                        return first.first();
                    }).then(function () {
                        assert.isNull(
                            document.getElementById("minimal2"),
                            "there should be no element with the " +
                                "``minimal2`` id after calling ``first``");
                        assert.isNull(
                            document.getElementById("minimal"),
                            "there should be no element with the " +
                                "``minimal`` id after calling ``first``");
                        assert.equal(
                            first.url, "/blank",
                            "the URL shown by the displayer should be " +
                                "the first URL in the history");
                        assert.equal(cb.callCount, 0,
                                     "there should have been no " +
                                     "``refresh.displayer`` event.");
                        return DONE;
                    });
            });


            it("should cause a ``refresh.displayer`` event to be emitted",
               function () {
                return first.display("/minimal").then(function () {
                    var p = promiseFromEvent(first.display_div,
                                             "refresh.displayer");
                    first.first();
                    return p.return(DONE);
                });
            });

        });

        describe("#last()", function () {
            it("should display the last item in history", function () {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id before we display the 2nd URL");
                return first.display("/minimal").call("display", "/minimal2")
                    .call("first")
                    .call("last")
                    .then(function () {
                        assert.isNotNull(
                            document.getElementById("minimal2"),
                            "there should be no element with the " +
                                "``minimal2`` id after calling ``first``");
                        assert.isNull(
                            document.getElementById("minimal"),
                            "there should be no element with the " +
                                "``minimal`` id after calling ``first``");
                        assert.equal(
                            first.url, "/minimal2",
                            "the URL shown by the displayer should be " +
                                "the last URL in the history");
                        return DONE;
                    });
            });

            it("should cause a ``refresh.displayer`` event to be emitted",
               function () {
                return first.display("/minimal").call("first")
                    .then(function () {
                        var p = promiseFromEvent(first.display_div,
                                                 "refresh.displayer");
                        first.last();
                        return p.return(DONE);
                    });
            });

            it("should be a no-op if already last in history", function () {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id before we display the 2nd URL");
                var cb = sinon.spy();
                return first.display("/minimal").call("display", "/minimal2")
                    .then(function () {
                        assert.isNotNull(
                            document.getElementById("minimal2"),
                            "there should be no element with the " +
                                "``minimal2`` id after calling ``first``");
                        assert.isNull(
                            document.getElementById("minimal"),
                            "there should be no element with the " +
                                "``minimal`` id after calling ``first``");
                        assert.equal(
                            first.url, "/minimal2",
                            "the URL shown by the displayer should be " +
                                "the last URL in the history");

                        $(first.display_div).one("refresh.displayer", cb);
                        return first.last();
                    }).then(function () {
                        assert.isNotNull(
                            document.getElementById("minimal2"),
                            "there should be no element with the " +
                                "``minimal2`` id after calling ``first``");
                        assert.isNull(
                            document.getElementById("minimal"),
                            "there should be no element with the " +
                                "``minimal`` id after calling ``first``");
                        assert.equal(
                            first.url, "/minimal2",
                            "the URL shown by the displayer should be " +
                                "the last URL in the history");
                        assert.equal(cb.callCount, 0,
                                     "there should have been no " +
                                     "``refresh.displayer`` event.");
                        return DONE;
                    });
            });
        });

        describe("#previous()", function () {
            it("should display the previous item in history", function () {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id before we display the 2nd URL");
                return first.display("/minimal")
                    .call("display", "/minimal2")
                    .call("previous")
                    .then(function () {
                        assert.isNull(
                            document.getElementById("minimal2"),
                            "there should be no element with the " +
                                "``minimal2`` id after calling ``first``");
                        assert.isNotNull(
                            document.getElementById("minimal"),
                            "there should be no element with the " +
                                "``minimal`` id after calling ``first``");
                        assert.equal(
                            first.url, "/minimal",
                            "the URL shown by the displayer should be " +
                                "the last URL in the history");
                        return DONE;
                });
            });

            it("should cause a ``refresh.displayer`` event to be emitted",
               function () {
                return first.display("/minimal").then(function () {
                    var p = promiseFromEvent(first.display_div,
                                             "refresh.displayer");
                    first.previous();
                    return p.return(DONE);
                });
            });

            it("should be a no-op if already first in history", function () {
                var cb = sinon.spy();
                return first.display("/minimal")
                    .call("previous")
                    .then(function () {
                        assert.isNull(document.getElementById("minimal2"),
                                      "there should be no element with the " +
                                      "``minimal2`` id after calling ``first``");
                        assert.isNull(document.getElementById("minimal"),
                                      "there should be no element with the " +
                                      "``minimal`` id after calling ``first``");
                        assert.equal(first.url, "/blank",
                                     "the URL shown by the displayer should be " +
                                     "the last URL in the history");

                        $(first.display_div).one("refresh.displayer", cb);
                        return first.previous();
                    }).then(function () {
                        assert.isNull(document.getElementById("minimal2"),
                                      "there should be no element with the " +
                                      "``minimal2`` id after calling ``first``");
                        assert.isNull(document.getElementById("minimal"),
                                      "there should be no element with the " +
                                      "``minimal`` id after calling ``first``");
                        assert.equal(first.url, "/blank",
                                     "the URL shown by the displayer should be " +
                                     "the last URL in the history");
                        assert.equal(cb.callCount, 0,
                                     "there should have been no " +
                                     "``refresh.displayer`` event.");
                        return DONE;
                    });
            });
        });

        describe("#next()", function () {
            it("should display the next item in history", function () {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id before we display the 2nd URL");
                return first.display("/minimal")
                    .call("display", "/minimal2")
                    .call("first")
                    .call("next")
                    .then(function () {
                        assert.isNull(
                            document.getElementById("minimal2"),
                            "there should be no element with the " +
                                "``minimal2`` id after calling ``first``");
                        assert.isNotNull(
                            document.getElementById("minimal"),
                            "there should be no element with the " +
                                "``minimal`` id after calling ``first``");
                        assert.equal(
                            first.url, "/minimal",
                            "the URL shown by the displayer should be " +
                                "the last URL in the history");
                        return DONE;
                });
            });

            it("should cause a ``refresh.displayer`` event to be emitted",
               function () {
                return first.display("/minimal")
                    .call("previous")
                    .then(function () {
                        var p = promiseFromEvent(first.display_div,
                                                 "refresh.displayer");
                        first.next();
                        return p.return(DONE);
                    });
            });

            it("should be a no-op if already last in history", function () {
                var cb = sinon.spy();
                return first.display("/minimal").then(function () {
                    assert.isNull(document.getElementById("minimal2"),
                                  "there should be no element with the " +
                                  "``minimal2`` id after calling ``first``");
                    assert.isNotNull(document.getElementById("minimal"),
                                     "there should be no element with the " +
                                     "``minimal`` id after calling ``first``");
                    assert.equal(first.url, "/minimal",
                                 "the URL shown by the displayer should be " +
                                 "the last URL in the history");

                    $(first.display_div).one("refresh.displayer", cb);
                    return first.next();
                }).then(function () {
                    assert.isNull(document.getElementById("minimal2"),
                                  "there should be no element with the " +
                                  "``minimal2`` id after calling ``first``");
                    assert.isNotNull(document.getElementById("minimal"),
                                     "there should be no element with the " +
                                     "``minimal`` id after calling ``first``");
                    assert.equal(first.url, "/minimal",
                                 "the URL shown by the displayer should be " +
                                 "the last URL in the history");
                    assert.equal(cb.callCount, 0,
                                 "there should have been no " +
                                 "``refresh.displayer`` event.");
                    return DONE;
                });
            });
        });

        describe("#_refresh()", function () {
            it("should cause a ``refresh.displayer`` event to be emitted",
               function () {
                var p = promiseFromEvent(first.display_div,
                                         "refresh.displayer");
                first._refresh();
                return p.return(DONE);
            });

            it("should be a noop on closed objects",
               function () {
                var cb = sinon.spy();
                return first.close().then(function () {
                    $(first.display_div).one("refresh.displayer", cb);
                    return first._refresh();
                }).then(function () {
                    assert.equal(cb.callCount, 0,
                                 "no ``refresh.displayer`` event should " +
                                 "have been emited");
                    return DONE;
                });
            });

            it("should be a noop on objects no longer in the DOM",
               function () {
                var cb = sinon.spy();
                return first.close().then(function () {
                    // Yes, we cheat to be able to simulate an object
                    // which is not closed but not in the DOM.
                    first._closed = false;
                    $(first.display_div).one("refresh.displayer", cb);
                    return first._refresh();
                }).then(function () {
                    assert.equal(cb.callCount, 0,
                                 "no ``refresh.displayer`` event should " +
                                 "have been emited");
                    return DONE;
                });
            });

            it("should return a promise that resolves to this object",
               function () {
                return assert.eventually.equal(
                    first._refresh(),
                    first,
                    "the promise should resolve to the object on which the " +
                        "method was called").return(DONE);
            });

            it("should bring up a spinner if the network is slow, " +
               "and remove it once a response has been obtained", function () {
                // Our job is to save the respondImmediately state, and return
                // a disposer that will restore it.
                function saveServerState() {
                    var saved = server.respondImmediately;
                    return Promise.resolve().disposer(function () {
                        server.respondImmediately = saved;
                    });
                }

                assert.isUndefined(
                    first.display_div
                        .getElementsByClassName("fa-spinner")[0],
                    "there should not be a spinner element");

                var refresh_p;
                return Promise.using(saveServerState(), function () {
                    server.respondImmediately = false;
                    // Reduce the timeout so that we don't have to wait long.
                    first._network_timeout = 20;
                    refresh_p = first._refresh();
                    // Wait for the spinner to come up.
                    return Promise.delay(30);
                }).then(function () {
                    assert.isDefined(
                        first.display_div
                            .getElementsByClassName("fa-spinner")[0],
                        "there should be a spinner element " +
                            "while waiting");

                    // Finally respond, and continue with the refresh
                    // promise.
                    server.respond();
                    return refresh_p;
                }).then(function () {
                    assert.isUndefined(
                        first.display_div
                            .getElementsByClassName("fa-spinner")[0],
                        "there should no longer be a spinner element " +
                            "after we obtained an answer");
                    return DONE;
                });
            });
        });

        it("should move to the previous URL when the previous button is clicked",
           function () {
            return first.display("/blank2").then(function () {
                $(first.previous_button).click();
                return eventually(function () {
                    return first.url === "/blank";
                }, "the displayer should eventually show the previous URL");
            }).return(DONE);
        });

        it("should move to the next URL when the next button is clicked",
           function () {
            return first.display("/blank2").then(function () {
                $(first.previous_button).click();
                return eventually(function () {
                    return first.url === "/blank";
                }, "the displayer should eventually show the previous URL");
            }).then(function () {
                $(first.next_button).click();
                return eventually(function () {
                    return first.url === "/blank2";
                }, "the displayer should eventually show the next URL");
            }).return(DONE);
        });

        it("should move to the first URL when the first button is clicked",
           function () {
            return first.display("/blank2").call("display", "/minimal")
                .then(function () {
                $(first.first_button).click();
                return eventually(function () {
                    return first.url === "/blank";
                }, "the displayer should eventually show the first URL");
            }).return(DONE);
        });

        it("should move to the last URL when the last button is clicked",
           function () {
            return first.display("/blank2").call("display", "/minimal")
                .then(function () {
                    $(first.first_button).click();
                    return eventually(function () {
                        return first.url === "/blank";
                    }, "the displayer should eventually show the first URL");
                }).then(function () {
                    $(first.last_button).click();
                    return eventually(function () {
                        return first.url === "/minimal";
                    }, "the displayer should eventually show the last URL");
                }).return(DONE);
        });

        it("should close the Displayer when the close button is clicked",
           function () {
            $(first.close_button).click();
            return eventually(function () {
                return first._closed;
            }, "the displayer should be closed").return(DONE);
        });

        it("should close all Displayer objects when the close all button is " +
           "clicked",
           function () {
            return ds.open("/blank2").then(function() {
                var all = Array.prototype.slice.call(ds.displayers);
                $(first.close_all_button).click();
                return eventually(function () {
                    return all.every(function (x) {
                        return x._closed;
                    });
                }, "all displayers should be closed");
            }).return(DONE);
        });

        it("should load the URL of the other content when the user clicks on " +
           "a URL that should load contents",
           function () {
            return first.display("/minimal").then(function() {
                var link = first.display_div
                    .getElementsByClassName("sf-link")[0];
                assert.isDefined(link, "we should have a link to click");
                $(link).click();
                return eventually(function () {
                    // We cannot just check against "/minimal2"
                    // because the link will change the url to
                    // something like http://localhost:..../minimal2. So
                    // we following rigmarole.
                    return first.url.split("/").splice(-1)[0]  === "minimal2";
                }, "the display should have switched");
            }).return(DONE);
        });

    });
});

});
