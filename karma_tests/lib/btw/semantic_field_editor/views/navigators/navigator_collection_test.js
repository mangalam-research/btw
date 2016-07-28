/* global chai describe beforeEach before after it */
define(function factory(require, exports, _module) {
  var $ = require("jquery");
  var sinon = require("sinon");
  var velocity = require("velocity");
  var Promise = require("bluebird");
  var Squire = require("Squire");
  var Mn = require("marionette");

  var assert = chai.assert;
  var injector = new Squire();

  describe.skip("NavigatorCollectionView", function _describe() {
    var view;
    var NavigatorCollectionView;
    var server;

    before(function before(done) {
      server = sinon.fakeServer.create();
      server.respondWith("GET", "/one",
                         [200, { "Content-Type": "application/json" },
                          JSON.stringify({ text: "one" })]);
      server.respondImmediately = true;

      // Make all animations be instantaneous so that we don't spend
      // seconds waiting for them to happen.
      velocity.mock = true;

      // injector.mock("btw/semantic_field_editor/views/navigators/page",
      //             Mn.ItemView)
      //   .require(
      //     ["btw/semantic_field_editor/views/navigators/navigator_collection"],
      //     function loaded(_view) {
      //       NavigatorCollectionView = _view;
      //       done();
      //     });
      done();
    });

    after(function after() {
      server.restore();
      velocity.mock = false;
      // injector.clean();
    });

    beforeEach(function beforeEach() {
      view = new NavigatorCollectionView();
    });

    it("constructs a view with an empty collection", function test() {
      assert.equal(view.collection.length, 0);
      return Promise.resolve(1);
    });

    describe("#closeAllNavigators", function _describe() {
      it("works when the collection is empty", function test() {
        view.closeAllNavigators();
        assert.equal(view.collection.length, 0);
        return Promise.resolve(1);
      });
    });
  });
});
