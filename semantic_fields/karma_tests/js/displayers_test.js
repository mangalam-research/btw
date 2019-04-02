/* global chai before after beforeEach afterEach describe */
define(
  ["jquery", "sinon", "js/displayers", "velocity", "bluebird"],
  function factory($, sinon, displayers, velocity, bluebird) {
    "use strict";

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
      return new Promise(function promiseFactory(resolve) {
        $(el).one(event, function onEvent() {
          resolve(Array.prototype.slice.call(arguments));
        });
      });
    }

    var DONE_VAL = {};
    var DONE = Promise.resolve(DONE_VAL);

    var it = function it(title, fn) {
      if (fn.length) {
        throw new Error("you must update your it replacement to support " +
                        "the done callback or use a promise instead");
      }

      return window.it.call(this, title, function test() {
        var ret = fn.call(this);
        assert.isDefined(ret,
                         "you forgot to return a value from your test");

        return ret.then(function check(x) {
          assert.equal(x, DONE_VAL);
        });
      });
    };

    it.only = window.it.only;

    function eventually(cb, message, timeout) {
      timeout = (timeout === undefined) ? 1000 : timeout;
      return new Promise(function promiseFactory(resolve, reject) {
        var start = Date.now();
        function check() {
          if (cb()) {
            resolve(true);
          }
          if (Date.now() - start > timeout) {
            reject(new Error(message));
          }

          setTimeout(check, 200);
        }
        check();
      });
    }

    describe("", function suite() {
      var template;
      var server;
      before(function beforeHook() {
        template = $(displayers.html_template)[0];
        document.body.insertBefore(template, null);

        // Remove the text content to help testing.
        template.getElementsByClassName("paged-content")[0].textContent = "";
        server = sinon.fakeServer.create();
        var blankResponse = [200, { "Content-Type": "application/html" }, ""];
        server.respondWith("GET", "/blank", blankResponse);
        server.respondWith("GET", "/blank2", blankResponse);
        server.respondWith("GET", "/minimal",
                           [200, { "Content-Type": "application/html" },
                            "<p id='minimal'>" +
                            "<a class='sf-link' href='/minimal2'>/minimal2" +
                            "</a></p>"]);
        server.respondWith("GET", "/minimal2",
                           [200, { "Content-Type": "application/html" },
                            "<p id='minimal2'>minimal2</p>"]);
        server.respondWith("GET", "/bad",
                           [404, { "Content-Type": "application/html" }, ""]);
        server.respondImmediately = true;


        // Make all animations be instantaneous so that we don't spend seconds
        // waiting for them to happen.
        velocity.mock = true;
      });

      after(function afterHook() {
        server.restore();
        document.body.removeChild(template);
        velocity.mock = false;
      });


      describe("Displayers", function displayersTest() {
        var ds;
        beforeEach(function beforeEachHook() {
          ds = new Displayers(template);
        });

        afterEach(function afterEachHook() {
          return ds.closeAll();
        });

        it("should construct a new Displayers object", function test() {
          assert.equal(ds.displayers.length, 0,
                       "the object should have no displayers yet");
          assert.equal(ds.template, template,
                       "the object should have the proper template");
          return DONE;
        });

        describe("#closeAll()", function closeAll() {
          it("should work on an empty Displayers object", function test() {
            ds.closeAll();
            assert.equal(ds.displayers.length, 0,
                         "the object should have no displayers");
            return DONE;
          });

          it("should empty a Displayers object", function test() {
            return ds.open("/blank").then(function opened() {
              return ds.open("/blank2");
            }).then(function opened() {
              assert.equal(ds.displayers.length, 2,
                           "the object should have 2 displayers");
              return assert.eventually.equal(
                ds.closeAll().get("displayers").get("length"),
                0,
                "the object should have no displayers").return(DONE);
            });
          });

          it("should be callable any number of times", function test() {
            return ds.open("/blank").then(function opened() {
              return ds.open("/blank2");
            }).then(function opened() {
              return assert.eventually.equal(
                ds.closeAll().get("displayers").get("length"),
                0,
                "the object should have no displayers");
            }).then(function done() {
              return ds.closeAll().return(DONE);
            });
          });

          it("should return a promise that resolves to the Displayers" +
             "on which it was called",
             function test() {
               return ds.open("/blank").then(function opened() {
                 return assert.eventually.equal(
                   ds.closeAll(), ds,
                   "the resolved value should be the same as the object " +
                     "on which ``closeAll()`` was called")
                   .return(DONE);
               });
             });
        });

        describe("#open(url)", function open() {
          it("should add a new Displayer to a new Displayers object",
             function test() {
               assert.equal(ds.displayers.length, 0,
                            "the object should have no displayers");
               return ds.open("/blank").then(function opened() {
                 assert.equal(ds.displayers.length, 1,
                              "the object should have 1 displayers");
                 return DONE;
               });
             });

          it("should animate the new Displayer added", function test() {
            return ds.open("/blank").then(function opened() {
              assertAnimated(ds.displayers[0].display_div, "the new Displayer");
              return DONE;
            });
          });

          it("should add a new Displayer when the URL is not already shown",
             function test() {
               assert.equal(ds.displayers.length, 0,
                            "the object should have no displayers");
               return ds.open("/blank").then(function opened() {
                 assert.equal(ds.displayers.length, 1,
                              "the object should have 1 displayers");
                 return ds.open("/blank2");
               }).then(function done() {
                 assert.equal(ds.displayers.length, 2,
                              "the object should have 2 displayers");
                 return DONE;
               });
             });

          it("should not add a new Displayer when the URL is already shown",
             function test() {
               assert.equal(ds.displayers.length, 0,
                            "the object should have no displayers");
               return ds.open("/blank").then(function opened() {
                 assert.equal(ds.displayers.length, 1,
                              "the object should have 1 displayers");
                 return ds.open("/blank");
               }).then(function done() {
                 assert.equal(ds.displayers.length, 1,
                              "the object should have 1 displayers");
                 return DONE;
               });
             });


          it("should scroll into view the Display that already displays " +
             "the URL",
             function test() {
               assert.equal(ds.displayers.length, 0,
                            "the object should have no displayers");
               return ds.open("/blank").then(function opened(d) {
                 assert.equal(ds.displayers.length, 1,
                              "the object should have 1 displayers");
                 var div = d.display_div;
                 var mockDiv = sinon.mock(div);
                 mockDiv.expects("scrollIntoView").once();
                 return ds.open("/blank").then(function opened2(d2) {
                   assert.equal(d, d2,
                                "it should not have opened a new display");
                   assert.equal(ds.displayers.length, 1,
                                "the object should have 1 displayers");
                   mockDiv.verify();
                   return DONE;
                 }).finally(function done() {
                   mockDiv.restore();
                 });
               });
             });

          it("should animate the Display that already shows the URL",
             function test() {
               return ds.open("/blank").then(function opened(d) {
                 clearAnimationInfo(d.display_div);
                 return ds.open("/blank");
               }).then(function done(d) {
                 assertAnimated(d.display_div, "the Display");
                 return DONE;
               });
             });

          it("should display the URL's content", function test() {
            assert.isNull(document.getElementById("minimal"),
                          "the element should not exist");
            return ds.open("/minimal").then(function opened() {
              assert.isNotNull(document.getElementById("minimal"),
                               "the element should exist");
              return DONE;
            });
          });

          it("should generate an open.displayers event on the template " +
             "with the new display as parameter",
             function test() {
               var p = promiseFromEvent(template, "open.displayers");
               ds.open("/blank");
               return p.spread(function opened(ev, param) {
                 assert.equal(ds.displayers[0], param,
                              "param should be the displayer");
                 return DONE;
               });
             });

          it("should create a Displayer that has the right " +
             "``displayers`` value",
             function test() {
               return assert.eventually.equal(
                 ds.open("/blank").get("displayers"), ds,
                 "the ``displayers`` field should be the object " +
                   "that created the Displayer object")
                 .return(DONE);
             });

          it("should create a Displayer whose display_div is just before " +
             "the template",
             function test() {
               return assert.eventually.equal(
                 ds.open("/blank").get("display_div").get("nextSibling"),
                 template,
                 "the display_div should be before the template")
                 .return(DONE);
             });

          it("should create a Displayer whose display_div is based on " +
             "the template",
             function test() {
               return ds.open("/blank").then(function opened(d) {
                 var templateEls = Array.prototype.map.call(
                   template.querySelectorAll("*"),
                   function getTagName(el) {
                     return el.tagName;
                   });

                 var divEls = Array.prototype.map.call(
                   d.display_div.querySelectorAll("*"),
                   function getTagName(el) {
                     return el.tagName;
                   });

                 assert.sameMembers(
                   divEls,
                   templateEls,
                   "the display_div be based on the template");
                 return DONE;
               });
             });

          it("should create a Displayer whose url is the one passed " +
             "to ``open``",
             function test() {
               return assert.eventually.equal(
                 ds.open("/blank").get("url"),
                 "/blank",
                 "the display_div be based on the template")
                 .return(DONE);
             });
        });
      });

      describe("Displayer", function displayerTest() {
        var ds;
        var first;
        beforeEach(function beforeEachHook() {
          ds = new Displayers(template);
          return ds.open("/blank").then(function opened(d) {
            first = d;
            return d;
          });
        });

        afterEach(function afterEachHook() {
          return ds.closeAll();
        });

        describe("#closeAll()", function closeAll() {
          it("should close all Displayer objects associated with parent " +
             "Displayers object",
             function test() {
               return ds.open("/blank2").then(function opened() {
                 assert.equal(ds.displayers.length, 2,
                              "there should be two displayers");
                 var displayersCopy = ds.displayers.slice();
                 return ds.displayers[0].closeAll().then(function closed() {
                   assert.equal(ds.displayers.length, 0,
                                "there should be no displayers");
                   // eslint-disable-next-line no-cond-assign
                   for (var ix = 0, d; (d = displayersCopy[ix]); ++ix) {
                     assert.isTrue(d.closed,
                                   "the displayer should be destroyed");
                   }
                   return DONE;
                 });
               });
             });

          it("should be callable multiple times", function test() {
            return ds.open("/blank2").then(function open() {
              assert.equal(ds.displayers.length, 2,
                           "there should be two displayers");
              return assert.eventually.equal(
                first.closeAll().get("displayers").get("length"),
                0,
                "there should be no displayers");
            }).then(function done() {
              return first.closeAll().return(DONE);
            });
          });

          it("should return a promise that resolves to the " +
             "parent Displayers object",
             function test() {
               return assert.eventually.equal(
                 first.closeAll(), ds,
                 "the resolved value should be the parent Displayers " +
                   "object").return(DONE);
             });
        });

        describe("#close()", function close() {
          it("should mark the Displayer object as closed", function test() {
            assert.isFalse(first.closed,
                           "the displayer should not be marked closed");
            return assert.eventually.isTrue(
              first.close().get("closed"),
              "the displayer should be marked closed").return(DONE);
          });

          it("should return a Promise that resolves to the " +
             "displayer being closed",
             function test() {
               return assert.eventually.equal(
                 first.close(), first,
                 "the resolved value should be the displayer being closed")
                 .return(DONE);
             });

          it("should be callable multiple times", function test() {
            return assert.eventually.equal(
              first.close().call("close"), first,
              "the resolved value should be the displayer being closed")
              .return(DONE);
          });

          it("should remove the Displayer from the DOM", function test() {
            assert.isNotNull(first.display_div.parentNode,
                             "the display_div should be in the DOM");
            return assert.eventually.isNull(
              first.close().get("display_div").get("parentNode"),
              "the display_div should no longer be in the DOM")
              .return(DONE);
          });

          it("should trigger a ``closed.displayer`` event on the " +
             "display_div with the Displayer object as parameter",
             function test() {
               var p = promiseFromEvent(first.display_div, "closed.displayer");

               first.close();
               return p.spread(function closed(ev, displayer) {
                 assert.equal(displayer, first,
                              "the parameter should be the Displayer " +
                              "being closed");
               }).return(DONE);
             });

          it("should trigger a ``closed.displayer`` event only once " +
             "even if called multiple times",
             function test() {
               var cb = sinon.spy();
               $(first.display_div).on("closed.displayer", cb);
               return first.close().then(function closed() {
                 assert.isTrue(cb.calledOnce,
                               "the event handler should have been " +
                               "called once");
                 return first.close();
               }).then(function done() {
                 assert.isTrue(cb.calledOnce,
                               "the event handler should have been " +
                               "called once");
                 return DONE;
               });
             });

          it("should animate the display_div", function test() {
            clearAnimationInfo(first.display_div);
            return first.close().then(function closed() {
              assertAnimated(first.display_div, "the Displayer");
              return DONE;
            });
          });
        });

        describe("#display(url)", function display() {
          it("should cause the Displayer to display the new contents",
             function test() {
               assert.isNull(document.getElementById("minimal"),
                             "the contents should not yet be present");
               return first.display("/minimal").then(function displayed() {
                 assert.isNotNull(document.getElementById("minimal"),
                                  "the contents should have been loaded");
                 return DONE;
               });
             });

          it("should cause the Displayer to change the current URL",
             function test() {
               return assert.eventually.equal(
                 first.display("/minimal").get("url"),
                 "/minimal",
                 "the URL should be what was passed to ``display()``")
                 .return(DONE);
             });

          it("should cause the Displayer to record history",
             function test() {
               var original = first.history.length;
               return assert.eventually.equal(
                 first.display("/minimal").get("history").get("length"),
                 original + 1,
                 "the history should have increased")
                 .return(DONE);
             });


          it("should cause the Displayer to scrap the history tail",
             function test() {
               return first.display("/blank2").then(function displayed() {
                 var p = promiseFromEvent(first.display_div,
                                          "refresh.displayer");

                 first.first();
                 return p;
               }).then(function displayed2() {
                 return first.display("/minimal");
               }).then(function done() {
                 assert.equal(first.history.length, 2,
                              "the length of the history should be 1");
                 return DONE;
               });
             });

          it("should cause the Displayer content to be animated",
             function test() {
               clearAnimationInfo(first.content);
               return first.display("/minimal").then(function displayed() {
                 assertAnimated(first.content, "the Display");
                 return DONE;
               });
             });

          it("should cause a ``refresh.displayer`` event on the " +
             "``display_div``",
             function test() {
               var p = promiseFromEvent(first.display_div, "refresh.displayer")
                   .spread(function refreshed(ev, d, url) {
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
             function test() {
               var original = first.history.length;
               clearAnimationInfo(first.content);
               var $div = $(first.display_div);
               var cb = sinon.spy();
               $div.one("refresh.displayer", cb);
               return first.display("/blank").then(function displayed() {
                 assert.equal(first.history.length, original,
                              "the history should not have increased");
                 assertNotAnimated(first.content, "the Display");
                 assert.equal(cb.callCount, 0,
                              "there should not have been a " +
                              "``refresh.displayer`` event");
                 return DONE;
               });
             });

          it("should throw if called on a closed Displayer", function test() {
            return ds.closeAll().then(function closed() {
              return assert.isRejected(
                first.display("/blank"),
                "trying to display a URL on a closed Displayer")
                .return(DONE);
            });
          });

          it("should throw if called on a Displayer which is no " +
             "longer in the DOM",
             function test() {
               return ds.closeAll().then(function closed() {
                 // Yes, we cheat. There is currently no way for a Displayer to
                 // be closed but still in the DOM.
                 first._closed = false;
                 return assert.isRejected(
                   first.display("/blank"),
                   "trying to display a URL on a Displayer which is " +
                     "not in the DOM")
                   .return(DONE);
               });
             });

          it("should provide a useful rejection on failure", function test() {
            return assert.isRejected(first.display("/bad")).return(DONE);
          });
        });

        describe("#first()", function firstSuite() {
          it("should display the first item in history", function test() {
            assert.isNull(document.getElementById("minimal2"),
                          "there should be no element with the " +
                          "``minimal2`` id before we display the 2nd URL");
            return first.display("/minimal").call("display", "/minimal2")
              .then(function displayed() {
                assert.isNotNull(document.getElementById("minimal2"),
                                 "there should be an element with the " +
                                 "``minimal2`` id after we display the " +
                                 "2nd URL");
                return first.first();
              }).then(function done() {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id after calling ``first``");
                assert.isNull(document.getElementById("minimal"),
                              "there should be no element with the " +
                              "``minimal`` id after calling ``first``");
                assert.equal(first.url, "/blank",
                             "the URL shown by the displayer should be " +
                             "the first URL in the history");
                return DONE;
              });
          });

          it("should be a noop if already first in history", function test() {
            assert.isNull(document.getElementById("minimal2"),
                          "there should be no element with the " +
                          "``minimal2`` id before we display the 2nd URL");
            var cb = sinon.spy();
            return first.display("/minimal").call("display", "/minimal2")
              .then(function displayed() {
                assert.isNotNull(document.getElementById("minimal2"),
                                 "there should be an element with the " +
                                 "``minimal2`` id after we display the " +
                                 "2nd URL");
                return first.first();
              }).then(function goneFirst() {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id after calling ``first``");
                assert.isNull(document.getElementById("minimal"),
                              "there should be no element with the " +
                              "``minimal`` id after calling ``first``");
                assert.equal(first.url, "/blank",
                             "the URL shown by the displayer should be " +
                             "the first URL in the history");
                $(first.display_div).one("refresh.displayer", cb);
                return first.first();
                // eslint-disable-next-line newline-per-chained-call
              }).then(function done() {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id after calling ``first``");
                assert.isNull(document.getElementById("minimal"),
                              "there should be no element with the " +
                              "``minimal`` id after calling ``first``");
                assert.equal(first.url, "/blank",
                             "the URL shown by the displayer should be " +
                             "the first URL in the history");
                assert.equal(cb.callCount, 0,
                             "there should have been no " +
                             "``refresh.displayer`` event.");
                return DONE;
              });
          });


          it("should cause a ``refresh.displayer`` event to be emitted",
             function test() {
               return first.display("/minimal").then(function displayed() {
                 var p = promiseFromEvent(first.display_div,
                                          "refresh.displayer");
                 first.first();
                 return p.return(DONE);
               });
             });
        });

        describe("#last()", function last() {
          it("should display the last item in history", function test() {
            assert.isNull(document.getElementById("minimal2"),
                          "there should be no element with the " +
                          "``minimal2`` id before we display the 2nd URL");
            return first.display("/minimal").call("display", "/minimal2")
              .call("first")
              .call("last")
              .then(function goneLast() {
                assert.isNotNull(document.getElementById("minimal2"),
                                 "there should be no element with the " +
                                 "``minimal2`` id after calling ``first``");
                assert.isNull(document.getElementById("minimal"),
                              "there should be no element with the " +
                              "``minimal`` id after calling ``first``");
                assert.equal(first.url, "/minimal2",
                             "the URL shown by the displayer should be " +
                             "the last URL in the history");
                return DONE;
              });
          });

          it("should cause a ``refresh.displayer`` event to be emitted",
             function test() {
               return first.display("/minimal").call("first")
                 .then(function displayed() {
                   var p = promiseFromEvent(first.display_div,
                                            "refresh.displayer");
                   first.last();
                   return p.return(DONE);
                 });
             });

          it("should be a no-op if already last in history", function test() {
            assert.isNull(document.getElementById("minimal2"),
                          "there should be no element with the " +
                          "``minimal2`` id before we display the 2nd URL");
            var cb = sinon.spy();
            return first.display("/minimal").call("display", "/minimal2")
              .then(function displayed() {
                assert.isNotNull(document.getElementById("minimal2"),
                                 "there should be no element with the " +
                                 "``minimal2`` id after calling ``first``");
                assert.isNull(document.getElementById("minimal"),
                              "there should be no element with the " +
                              "``minimal`` id after calling ``first``");
                assert.equal(first.url, "/minimal2",
                             "the URL shown by the displayer should be " +
                             "the last URL in the history");

                $(first.display_div).one("refresh.displayer", cb);
                return first.last();
              }).then(function goneLast() {
                assert.isNotNull(document.getElementById("minimal2"),
                                 "there should be no element with the " +
                                 "``minimal2`` id after calling ``first``");
                assert.isNull(document.getElementById("minimal"),
                              "there should be no element with the " +
                              "``minimal`` id after calling ``first``");
                assert.equal(first.url, "/minimal2",
                             "the URL shown by the displayer should be " +
                             "the last URL in the history");
                assert.equal(cb.callCount, 0,
                             "there should have been no " +
                             "``refresh.displayer`` event.");
                return DONE;
              });
          });
        });

        describe("#previous()", function previous() {
          it("should display the previous item in history", function test() {
            assert.isNull(document.getElementById("minimal2"),
                          "there should be no element with the " +
                          "``minimal2`` id before we display the 2nd URL");
            return first.display("/minimal")
              .call("display", "/minimal2")
              .call("previous")
              .then(function gonePrevious() {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id after calling ``first``");
                assert.isNotNull(document.getElementById("minimal"),
                                 "there should be no element with the " +
                                 "``minimal`` id after calling ``first``");
                assert.equal(first.url, "/minimal",
                             "the URL shown by the displayer should be " +
                             "the last URL in the history");
                return DONE;
              });
          });

          it("should cause a ``refresh.displayer`` event to be emitted",
             function test() {
               return first.display("/minimal").then(function displayed() {
                 var p = promiseFromEvent(first.display_div,
                                          "refresh.displayer");
                 first.previous();
                 return p.return(DONE);
               });
             });

          it("should be a no-op if already first in history", function test() {
            var cb = sinon.spy();
            return first.display("/minimal")
              .call("previous")
              .then(function gonePrevious() {
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
              }).then(function gonePrevious2() {
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

        describe("#next()", function next() {
          it("should display the next item in history", function test() {
            assert.isNull(document.getElementById("minimal2"),
                          "there should be no element with the " +
                          "``minimal2`` id before we display the 2nd URL");
            return first.display("/minimal")
              .call("display", "/minimal2")
              .call("first")
              .call("next")
              .then(function goneNext() {
                assert.isNull(document.getElementById("minimal2"),
                              "there should be no element with the " +
                              "``minimal2`` id after calling ``first``");
                assert.isNotNull(document.getElementById("minimal"),
                                 "there should be no element with the " +
                                 "``minimal`` id after calling ``first``");
                assert.equal(first.url, "/minimal",
                             "the URL shown by the displayer should be " +
                             "the last URL in the history");
                return DONE;
              });
          });

          it("should cause a ``refresh.displayer`` event to be emitted",
             function test() {
               return first.display("/minimal")
                 .call("previous")
                 .then(function gonePrevious() {
                   var p = promiseFromEvent(first.display_div,
                                            "refresh.displayer");
                   first.next();
                   return p.return(DONE);
                 });
             });

          it("should be a no-op if already last in history", function test() {
            var cb = sinon.spy();
            return first.display("/minimal").then(function displayed() {
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
            }).then(function goneNext() {
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

        describe("#_refresh()", function _refresh() {
          it("should cause a ``refresh.displayer`` event to be emitted",
             function test() {
               var p = promiseFromEvent(first.display_div, "refresh.displayer");
               first._refresh();
               return p.return(DONE);
             });

          it("should be a noop on closed objects", function test() {
            var cb = sinon.spy();
            return first.close().then(function closed() {
              $(first.display_div).one("refresh.displayer", cb);
              return first._refresh();
            }).then(function refreshed() {
              assert.equal(cb.callCount, 0,
                           "no ``refresh.displayer`` event should " +
                           "have been emited");
              return DONE;
            });
          });

          it("should be a noop on objects no longer in the DOM",
             function test() {
               var cb = sinon.spy();
               return first.close().then(function closed() {
                 // Yes, we cheat to be able to simulate an object
                 // which is not closed but not in the DOM.
                 first._closed = false;
                 $(first.display_div).one("refresh.displayer", cb);
                 return first._refresh();
               }).then(function refreshed() {
                 assert.equal(cb.callCount, 0,
                              "no ``refresh.displayer`` event should " +
                              "have been emited");
                 return DONE;
               });
             });

          it("should return a promise that resolves to this object",
             function test() {
               return assert.eventually.equal(
                 first._refresh(),
                 first,
                 "the promise should resolve to the object on which the " +
                   "method was called").return(DONE);
             });

          it("should bring up a spinner if the network is slow, " +
             "and remove it once a response has been obtained",
             function test() {
               // Our job is to save the respondImmediately state, and return
               // a disposer that will restore it.
               function saveServerState() {
                 var saved = server.respondImmediately;
                 return Promise.resolve().disposer(function dispose() {
                   server.respondImmediately = saved;
                 });
               }

               assert.isUndefined(first.display_div
                                  .getElementsByClassName("fa-spinner")[0],
                                  "there should not be a spinner element");

               var refreshP;
               return Promise.using(saveServerState(), function use() {
                 server.respondImmediately = false;
                 // Reduce the timeout so that we don't have to wait long.
                 first._network_timeout = 20;
                 refreshP = first._refresh();
                 // Wait for the spinner to come up.
                 return Promise.delay(30);
               }).then(function done() {
                 assert.isDefined(first.display_div
                                  .getElementsByClassName("fa-spinner")[0],
                                  "there should be a spinner element " +
                                  "while waiting");

                 // Finally respond, and continue with the refresh promise.
                 server.respond();
                 return refreshP;
               }).then(function refreshed() {
                 assert.isUndefined(first.display_div
                                    .getElementsByClassName("fa-spinner")[0],
                                    "there should no longer be a spinner " +
                                    "element after we obtained an answer");
                 return DONE;
               });
             });
        });

        it("should move to the previous URL when previous button is clicked",
           function test() {
             return first.display("/blank2").then(function displayed() {
               $(first.previous_button).click();
               return eventually(function cond() {
                 return first.url === "/blank";
               }, "the displayer should eventually show the previous URL");
             }).return(DONE);
           });

        it("should move to the next URL when the next button is clicked",
           function test() {
             return first.display("/blank2").then(function displayed() {
               $(first.previous_button).click();
               return eventually(function cond() {
                 return first.url === "/blank";
               }, "the displayer should eventually show the previous URL");
             }).then(function correctUrl() {
               $(first.next_button).click();
               return eventually(function cond() {
                 return first.url === "/blank2";
               }, "the displayer should eventually show the next URL");
             }).return(DONE);
           });

        it("should move to the first URL when the first button is clicked",
           function test() {
             return first.display("/blank2").call("display", "/minimal")
               .then(function displayed() {
                 $(first.first_button).click();
                 return eventually(function cond() {
                   return first.url === "/blank";
                 }, "the displayer should eventually show the first URL");
               }).return(DONE);
           });

        it("should move to the last URL when the last button is clicked",
           function test() {
             return first.display("/blank2").call("display", "/minimal")
               .then(function displayed() {
                 $(first.first_button).click();
                 return eventually(function cond() {
                   return first.url === "/blank";
                 }, "the displayer should eventually show the first URL");
               }).then(function correctUrl() {
                 $(first.last_button).click();
                 return eventually(function condition() {
                   return first.url === "/minimal";
                 }, "the displayer should eventually show the last URL");
                 // eslint-disable-next-line newline-per-chained-call
               }).return(DONE);
           });

        it("should close the Displayer when the close button is clicked",
           function test() {
             $(first.close_button).click();
             return eventually(function cond() {
               return first._closed;
             }, "the displayer should be closed").return(DONE);
           });

        it("should close all Displayer objects when the close all button is " +
           "clicked",
           function test() {
             return ds.open("/blank2").then(function opened() {
               var all = Array.prototype.slice.call(ds.displayers);
               $(first.close_all_button).click();
               return eventually(function cond() {
                 return all.every(function check(x) {
                   return x._closed;
                 });
               }, "all displayers should be closed");
             }).return(DONE);
           });

        it("should load the URL of the other content when the user clicks on " +
           "a URL that should load contents",
           function test() {
             return first.display("/minimal").then(function displayed() {
               var link = first.display_div
                   .getElementsByClassName("sf-link")[0];
               assert.isDefined(link, "we should have a link to click");
               $(link).click();
               return eventually(function cond() {
                 // We cannot just check against "/minimal2" because the link
                 // will change the url to something like
                 // http://localhost:..../minimal2. So we following rigmarole.
                 return first.url.split("/").splice(-1)[0] === "minimal2";
               }, "the display should have switched");
             }).return(DONE);
           });
      });
    });
  });
