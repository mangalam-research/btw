/**
 * @module lib/btw/semantic_field_editor/views/navigators/navigator_collection
 * @desc A view for a group of navigators.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var Bb = require("backbone");
  var Mn = require("marionette");
  var NavigatorView = require("./navigator");
  var Navigator = require("../../models/navigator");
  var Promise = require("bluebird");
  var _ = require("lodash");

  function id(x) {
    return function innerId() {
      return x;
    };
  }

  var NavigatorCollection = Bb.Collection.extend({
    __classname__: "NavigatorCollection",
  });

  var NavigatorCollectionView = Mn.CollectionView.extend({
    __classname__: "NavigatorCollectionView",
    initialize: function initialize(options) {
      this.canAddResults = options.canAddResults;
      this.collection = new NavigatorCollection();
      NavigatorCollectionView.__super__.initialize.call(
        this, _.omit(options, ["canAddResults"]));
    },
    template: id("<div class='navigators'></div>"),
    childView: NavigatorView,

    childViewOptions: function childViewOptions() {
      return {
        canAddResults: this.canAddResults,
      };
    },

    childEvents: {
      "navigator:closeAll": "closeAllNavigators",
      "navigator:close": "closeNavigator",
    },

    closeNavigator: Promise.method(function closeNavigator(view) {
      var promise = view.makeDOMRemovedPromise();

      // This is possible if the view was already removed.
      if (promise === null) {
        promise = Promise.resolve(view);
      }

      this.collection.remove(view.model);
      return promise;
    }),

    closeAllNavigators: Promise.method(function closeAllNavigators() {
      var p = Promise.all(this.children.map(function map(view) {
        var promise = view.makeDOMRemovedPromise();

        // This is possible if the view was already removed.
        if (promise === null) {
          promise = Promise.resolve(view);
        }

        return promise;
      }));
      this.collection.reset();
      return p.return(this);
    }),

    openUrl: Promise.method(function openUrl(url) {
      var existing = this.collection.find(function find(navigator) {
        return navigator.getCurrentUrl() === url;
      });

      if (existing) {
        return this.focusNavigator(existing);
      }

      var navigator = new Navigator(url);
      this.collection.add([navigator], { at: 0 });
      var childView = this.children.findByModel(navigator);
      return childView.makeDOMDisplayedPromise();
    }),

    focusNavigator: Promise.method(function focusNavigator(navigator) {
      var view = this.children.findByModel(navigator);
      return view._focus();
    }),
  });

  return NavigatorCollectionView;
});
