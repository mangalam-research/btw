/* global it describe beforeEach before fixture chai after */
define(function factory(require, _exports, _module) {
  "use strict";
  var $ = require("jquery");
  var Viewer = require("btw/btw_view");
  var bluejax = require("bluejax");
  var Promise = require("bluebird");
  var sinon = require("sinon");
  var URI = require("urijs/URI");
  var assert = chai.assert;

  var semanticFieldURL = /^\/semantic-fields\/semanticfield\/(.*)$/;

  function setResponses(server, hteUrl, changeRecords) {
    changeRecords = changeRecords || [];

    // Clear all response in server.
    server.responses = [];
    server.respondWith(
      "GET",
      semanticFieldURL,
      function respond(request) {
        var query = new URI(request.url).query(true);
        var paths = query.paths.split(";");
        var response = [];
        for (var i = 0; i < paths.length; ++i) {
          var path = paths[i];
          response.push({
            path: path,
            heading: "semantic field foo",
            parent: undefined,
            hte_url: hteUrl,
            changerecords: changeRecords,
          });
        }
        request.respond(200,
                        { "Content-Type": "application/json" },
                        JSON.stringify(response));
      });
  }

  function one($el, event, fn) {
    return new Promise(function start(resolve, _reject) {
      $el.one(event, resolve);
      if (fn) {
        if (typeof fn === "string") {
          $el[fn]();
        }
        else {
          fn();
        }
      }
    });
  }

  function clickThenShown($el) {
    return one($el, "shown.bs.popover", "click");
  }

  function doThenHidden($el, fn) {
    return one($el, "hidden.bs.popover", fn);
  }

  function clickThenHidden($el) {
    return doThenHidden($el, "click");
  }

  function clickThenRenderedAndShown($el) {
    return one($el, "fully-rendered.btw-view.sf-popover", "click")
      .then(function rendered() {
        // We have to wait for the shown event too. That's because the
        // fully-rendered event happens before the popover is
        // "reshown". Issuing a `destroy` before the popover is shown
        // results in `destroy` being a no-op.
        return one($el, "shown.bs.popover");
      });
  }


  describe("btw_viewer", function btwViewerBlock() {
    var data;
    var biblData;
    var viewer;
    var server;
    var pristineFixtureHtml;
    var savedDuration;

    before(function before() {
      // Speed up the transitions so that we don't have to wait so much.
      savedDuration = $.fn.tooltip.Constructor.TRANSITION_DURATION;
      $.fn.tooltip.Constructor.TRANSITION_DURATION = 10;

      fixture.setBase("lexicography");
      fixture.load("templates/lexicography/viewer.html");

      var container = fixture.el.ownerDocument.createElement("div");
      container.className = "container";

      while (fixture.el.firstChild) {
        container.appendChild(fixture.el.firstChild);
      }

      fixture.el.appendChild(container);

      // Save the HTML of the fixture before any test has run, because
      // we need to reset it between tests.
      pristineFixtureHtml = fixture.el.innerHTML;


      server = sinon.fakeServer.create();
      server.xhr.useFilters = true;

      server.xhr.addFilter(function filter(method, url) {
        return !url.match(semanticFieldURL);
      });

      setResponses(server);
      server.respondImmediately = true;

      return Promise.all([
        bluejax.ajax({
          url: "/base/build/test-data/prepared_published_prasada.xml",
          dataType: "text",
        }).then(function then(data_) {
          data = data_;
        }),
        bluejax.ajax({
          url: "/base/build/test-data/prepared_published_prasada.json",
        }).then(function then(data_) {
          biblData = data_;
        }),
      ]);
    });

    after(function after() {
      // The xhr field is actually a reference to FakeXMLHttpRequest, which is
      // global. So restoring is not enough, we have to turn it off here.
      server.xhr.useFilters = false;
      server.xhr.filters = [];
      server.restore();
      $.fn.tooltip.Constructor.TRANSITION_DURATION = savedDuration;
    });

    beforeEach(function beforeEach(done) {
      fixture.el.innerHTML = pristineFixtureHtml;
      var wedDocument = fixture.el.getElementsByClassName("wed-document")[0];
      viewer = new Viewer(wedDocument, undefined,
                          undefined, "/semantic-fields/semanticfield/",
                          data,
                          biblData,
                          "/en-us");
      viewer.whenCondition("done", function finished() {
        done();
      });
    });

    it("makes all semantic fields into popover triggers", function it() {
      function check(el) {
        return Promise.try(function start() {
          var $trigger = $(el).closest("a.btn");
          return clickThenShown($trigger).then(function shown() {
            var popover = $trigger.data("bs.popover");
            assert.isDefined(popover);
            popover.destroy();
          });
        });
      }

      var sfs = viewer._root.getElementsByClassName("btw:sf");
      // We're not going to test every single element on the page but we should
      // test more than one.
      return Promise.each([sfs[0], sfs[1], sfs[sfs.length - 1]], check);
    });

    it("reclicking the semantic field closes the popover", function it() {
      var el = viewer._root.getElementsByClassName("btw:sf")[0];
      return Promise.try(function start() {
        // Reminder: getElementsByClassName returns a *live* list which
        // changes as elements are added or removed.
        var popovers = fixture.el.getElementsByClassName("popover");
        var $trigger = $(el).closest("a.btn");

        // Make sure we start from a clean slate.
        assert.equal(popovers.length, 0);

        return Promise.mapSeries([clickThenShown, clickThenHidden],
                                 function map(fn) {
                                   return fn($trigger);
                                 })
          .then(function hidden() {
            assert.equal(popovers.length, 0);
          });
      });
    });

    it("clicking outside the popover closes it", function it() {
      var el = viewer._root.getElementsByClassName("btw:sf")[0];
      return Promise.try(function start() {
        // Reminder: getElementsByClassName returns a *live* list which
        // changes as elements are added or removed.
        var popovers = fixture.el.getElementsByClassName("popover");
        var $trigger = $(el).closest("a.btn");

        // Make sure we start from a clean slate.
        assert.equal(popovers.length, 0);

        return clickThenShown($trigger)
          .then(function shown() {
            return doThenHidden($trigger, function hidden() {
              fixture.el.click();
            });
          })
          .then(function hidden() {
            assert.equal(popovers.length, 0);
          });
      });
    });

    it("clicking inside the popover does not close it", function it() {
      var el = viewer._root.getElementsByClassName("btw:sf")[0];
      return Promise.try(function start() {
        // Reminder: getElementsByClassName returns a *live* list which
        // changes as elements are added or removed.
        var popovers = fixture.el.getElementsByClassName("popover");
        var $trigger = $(el).closest("a.btn");

        // Make sure we start from a clean slate.
        assert.equal(popovers.length, 0);

        return clickThenShown($trigger)
          .then(function shown() {
            assert.equal(popovers.length, 1);
            var popover = popovers[0];
            popover.click();
            assert.equal(popovers.length, 1);
          })
          .finally(function finallyHandler() {
            var popover = $trigger.data("bs.popover");
            return doThenHidden($trigger, function hidden() {
              popover.destroy();
            });
          });
      });
    });

    it("a popover does not have a tree for fields without entries",
       function it() {
         var el = viewer._root.getElementsByClassName("btw:sf")[0];

         return Promise.try(function start() {
           // Reminder: getElementsByClassName returns a *live* list which
           // changes as elements are added or removed.
           var popovers = fixture.el.getElementsByClassName("popover");
           var $trigger = $(el).closest("a.btn");

           return clickThenRenderedAndShown($trigger)
             .then(function shown() {
               assert.equal(popovers.length, 1);
               var tree = popovers[0].getElementsByClassName("tree")[0];
               assert.isUndefined(tree);
             })
             .finally(function finallyHandler() {
               var popover = $trigger.data("bs.popover");
               popover.destroy();
             });
         });
       });

    it("a popover does not have a tree for fields with one entry",
       function it() {
         var el = viewer._root.getElementsByClassName("btw:sf")[0];
         setResponses(server, "http://example.com/fake",
                      [{
                        lemma: "foo",
                        url: "/foo",
                        datetime: "2001-01-01",
                        published: true,
                      }]);
         return Promise.try(function start() {
           // Reminder: getElementsByClassName returns a *live* list which
           // changes as elements are added or removed.
           var popovers = fixture.el.getElementsByClassName("popover");
           var $trigger = $(el).closest("a.btn");

           return clickThenRenderedAndShown($trigger)
             .then(function shown() {
               assert.equal(popovers.length, 1);
               // The element with the tree class exists but it is not actually
               // a GUI tree unless it has the treeview class.
               var tree = popovers[0].getElementsByClassName("tree")[0];
               assert.isDefined(tree);
               assert.isFalse(tree.classList.contains("treeview"),
                             "it should not be a treeview");
             })
             .finally(function finallyHandler() {
               var popover = $trigger.data("bs.popover");
               popover.destroy();
             });
         });
       });

    it("a popover has a tree for fields with one entry with multiple versions",
       function it() {
         var el = viewer._root.getElementsByClassName("btw:sf")[0];
         setResponses(server, "http://example.com/fake",
                      [{
                        lemma: "foo",
                        url: "/foo",
                        datetime: "2001-01-01",
                        published: true,
                      }, {
                        lemma: "foo",
                        url: "/foo2",
                        datetime: "2001-01-02",
                        published: true,
                      }]);
         return Promise.try(function start() {
           // Reminder: getElementsByClassName returns a *live* list which
           // changes as elements are added or removed.
           var popovers = fixture.el.getElementsByClassName("popover");
           var $trigger = $(el).closest("a.btn");

           return clickThenRenderedAndShown($trigger)
             .then(function shown() {
               assert.equal(popovers.length, 1);
               // The element with the tree class exists but it is not actually
               // a GUI tree unless it has the treeview class.
               var tree = popovers[0].getElementsByClassName("tree")[0];
               assert.isDefined(tree);
               assert.isTrue(tree.classList.contains("treeview"),
                             "the tree should be a treeview");
             })
             .finally(function finallyHandler() {
               var popover = $trigger.data("bs.popover");
               popover.destroy();
             });
         });
       });

    it("a popover has a tree for fields with multiple entries",
       function it() {
         var el = viewer._root.getElementsByClassName("btw:sf")[0];
         setResponses(server, "http://example.com/fake",
                      [{
                        lemma: "foo",
                        url: "/foo",
                        datetime: "2001-01-01",
                        published: true,
                      }, {
                        lemma: "bar",
                        url: "/bar",
                        datetime: "2001-01-01",
                        published: true,
                      }]);
         return Promise.try(function start() {
           // Reminder: getElementsByClassName returns a *live* list which
           // changes as elements are added or removed.
           var popovers = fixture.el.getElementsByClassName("popover");
           var $trigger = $(el).closest("a.btn");

           return clickThenRenderedAndShown($trigger)
             .then(function shown() {
               assert.equal(popovers.length, 1);
               // The element with the tree class exists but it is not actually
               // a GUI tree unless it has the treeview class.
               var tree = popovers[0].getElementsByClassName("tree")[0];
               assert.isDefined(tree);
               assert.isTrue(tree.classList.contains("treeview"),
                             "the tree should be a treeview");
             })
             .finally(function finallyHandler() {
               var popover = $trigger.data("bs.popover");
               popover.destroy();
             });
         });
       });
  });
});
