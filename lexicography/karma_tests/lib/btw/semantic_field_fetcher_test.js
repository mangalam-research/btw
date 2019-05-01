/* global it describe beforeEach afterEach chai */
define(function factory(require, _exports, _module) {
  "use strict";

  var _ = require("lodash");
  var sinon = require("sinon");
  var Fetcher = require("btw/semantic-field-fetcher").SFFetcher;
  var assert = chai.assert;

  describe("semantic-field-fetcher", function btwViewerBlock() {
    var fetcher;
    var server;
    var fetchUrl = "/semantic-fields/semanticfield";
    var excludeUrl = window.location.href;

    beforeEach(function beforeEach() {
      fetcher = new Fetcher(fetchUrl, excludeUrl, ["changerecords"]);
      server = sinon.fakeServer.create({
        respondImmediately: true,
      });
    });

    afterEach(function afterEach() {
      server.restore();
    });

    describe("fetch", function fetchSemanticFieldRefs() {
      it("is able to fetch data", function it() {
        var response = [{
          path: "01.01n",
          heading: "semantic field foo",
          parent: undefined,
          hte_url: undefined,
          changerecords: [{
            lemma: "foo",
            url: "/foo",
            datetime: "2001-01-01",
            published: true,
          }],
        }];
        server.respondWith("GET",
                           fetchUrl + "?paths=01.01n&fields=changerecords",
                           [200, { "Content-Type": "application/json" },
                            JSON.stringify(response)]);
        return assert.isFulfilled(fetcher.fetch(["01.01n"]));
      });

      it("caches semantic field information", function it() {
        var basic = {
          path: "01.01n",
          heading: "semantic field foo",
          parent: undefined,
          hte_url: undefined,
          changerecords: [],
        };
        var response = [basic, _.extend({}, basic, { path: "01.02n" })];
        // We don't particularly care about how the query is constructed,
        // or what is returned exactly, so long as we can test caching.
        server.respondWith([200, { "Content-Type": "application/json" },
                            JSON.stringify(response)]);
        return fetcher.fetch(["01.01n", "01.02n"])
          .then(function then() {
            return fetcher.fetch(["01.01n"]);
          })
          .then(function then() {
            return fetcher.fetch(["01.02n"]);
          })
          .then(function then() {
            return fetcher.fetch(["01.02n", "01.01n"]);
          })
          .then(function then(data) {
            assert.sameMembers(Object.keys(data),
                               ["01.01n", "01.02n"]);
            assert.equal(server.requests.length, 1,
                         "the fetcher should have made only one request");

            // We want the next response we get to be for 01.03n.
            server.respondWith(
              [200, { "Content-Type": "application/json" },
               JSON.stringify([_.extend({}, basic, { path: "01.03n" })])]);

            return fetcher.fetch(["01.02n", "01.01n", "01.03n"]);
          })
          .then(function then(data) {
            // Check the requests.
            assert.equal(server.requests.length, 2,
                         "the fetcher should have made only two requests");
            var lastRequest = server.requests[1];
            var url = new URL(lastRequest.url);
            assert.equal(url.searchParams.get("paths"), "01.03n",
                         "the last query should have queried only the " +
                         "semantic field we lack");

            // Check that the data received for 01.03n has been combined with
            // the cached data.
            assert.sameMembers(Object.keys(data),
                               ["01.01n", "01.02n", "01.03n"]);
          });
      });

      it("filters out changerecords with the excluded URL", function it() {
        var response = [{
          path: "01.01n",
          heading: "semantic field foo",
          parent: undefined,
          hte_url: undefined,
          changerecords: [{
            lemma: "foo",
            url: excludeUrl,
            datetime: "2001-01-01",
            published: true,
          }],
        }, {
          path: "01.02n",
          heading: "semantic field foo",
          parent: undefined,
          hte_url: undefined,
          changerecords: [{
            lemma: "foo",
            url: excludeUrl,
            datetime: "2001-01-01",
            published: true,
          }],
        }];
        server.respondWith("GET",
                           fetchUrl +
                           "?paths=01.01n%3B01.02n&fields=changerecords",
                           [200, { "Content-Type": "application/json" },
                            JSON.stringify(response)]);
        return fetcher.fetch(["01.01n", "01.02n"]).then(function then(data) {
          assert.deepEqual(data["01.01n"].changerecords, {});
          assert.deepEqual(data["01.02n"].changerecords, {});
        });
      });

      it("transforms changerecords into an map from lemma to array of " +
         "changerecords",
         function it() {
           var response = [{
             path: "01.01n",
             heading: "semantic field foo",
             parent: undefined,
             hte_url: undefined,
             changerecords: [{
               lemma: "foo",
               url: "a",
               datetime: "2001-01-01",
               published: true,
             }, {
               lemma: "bar",
               url: "b",
               datetime: "2001-01-01",
               published: true,
             }, {
               lemma: "bar",
               url: "c",
               datetime: "2001-01-02",
               published: true,
             }],
           }];
           server.respondWith("GET",
                              fetchUrl + "?paths=01.01n&fields=changerecords",
                              [200, { "Content-Type": "application/json" },
                               JSON.stringify(response)]);
           return fetcher.fetch(["01.01n"]).then(function then(data) {
             var records = data["01.01n"].changerecords;
             assert.equal(records.bar.length, 2);
             assert.equal(records.foo.length, 1);
             assert.sameMembers(Object.keys(records),
                                ["bar", "foo"]);
           });
         });

      it("sorts changerecords by descending datetime", function it() {
        var response = [{
          path: "01.01n",
          heading: "semantic field foo",
          parent: undefined,
          hte_url: undefined,
          changerecords: [{
            lemma: "foo",
            url: "a",
            datetime: "2001-01-01",
            published: true,
          }, {
            lemma: "bar",
            url: "b",
            datetime: "2001-01-01",
            published: true,
          }, {
            lemma: "bar",
            url: "c",
            datetime: "2001-01-02",
            published: true,
          }],
        }];
        server.respondWith("GET",
                           fetchUrl + "?paths=01.01n&fields=changerecords",
                           [200, { "Content-Type": "application/json" },
                            JSON.stringify(response)]);
        return fetcher.fetch(["01.01n"]).then(function then(data) {
          var records = data["01.01n"].changerecords;
          assert.equal(records.bar[0].datetime, "2001-01-02");
          assert.equal(records.bar[1].datetime, "2001-01-01");
        });
      });

      describe("create a tree for Bootstrap that has", function treeTests() {
        var response = [{
          path: "01.01n",
          heading: "semantic field foo",
          parent: undefined,
          hte_url: undefined,
          changerecords: [{
            lemma: "foo",
            url: "a",
            datetime: "2001-01-01",
            published: true,
          }, {
            lemma: "bar",
            url: "b",
            datetime: "2001-01-01",
            published: true,
          }, {
            lemma: "bar",
            url: "c",
            datetime: "2001-01-02",
            published: false,
          }],
        }];

        beforeEach(function beforeEach() {
          server.respondWith("GET",
                             fetchUrl + "?paths=01.01n&fields=changerecords",
                             [200, { "Content-Type": "application/json" },
                              JSON.stringify(response)]);
        });

        it("a top level sorted by lemma", function it() {
          return fetcher.fetch(["01.01n"]).then(function then(data) {
            var tree = data["01.01n"].tree;
            assert.equal(tree[0].text, "bar");
            assert.equal(tree[1].text, "foo");
          });
        });

        it("a top level with href pointing to the first changerecord",
           function it() {
             return fetcher.fetch(["01.01n"]).then(function then(data) {
               var tree = data["01.01n"].tree;
               assert.equal(tree[0].href, "c");
               assert.equal(tree[1].href, "a");
             });
           });

        it("a 2nd level sorted by descending datetime", function it() {
          return fetcher.fetch(["01.01n"]).then(function then(data) {
            var tree = data["01.01n"].tree;
            assert.equal(tree[0].nodes[0].text, "2001-01-02");
            assert.equal(tree[0].nodes[1].text, "2001-01-01 published");
          });
        });

        it("a 2nd level that has proper href values", function it() {
          return fetcher.fetch(["01.01n"]).then(function then(data) {
            var tree = data["01.01n"].tree;
            assert.equal(tree[0].nodes[0].href, "c");
            assert.equal(tree[0].nodes[1].href, "b");
          });
        });

        it("unselectable nodes", function it() {
          return fetcher.fetch(["01.01n"]).then(function then(data) {
            var tree = data["01.01n"].tree;
            function getSelectable(node) {
              return [node.selectable,
                      _.flatMapDeep(node.nodes, getSelectable)];
            }

            // We extract ``selectable`` from all nodes and then remove all
            // ``false`` values from the array. The result should be empty.
            assert.sameMembers(
              _.pull(_.flatMapDeep(tree, getSelectable), false),
              [],
              "all nodes should have a selectable property " +
                "which is false");
          });
        });
      });
    });
  });
});
