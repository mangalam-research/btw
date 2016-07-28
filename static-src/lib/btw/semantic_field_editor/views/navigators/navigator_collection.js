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
    initialize: function initialize() {
      this.collection = new NavigatorCollection();
      Mn.CollectionView.prototype.initialize.apply(this, arguments);
    },
    template: id("<div class='navigators'></div>"),
    childView: NavigatorView,

    childEvents: {
      "navigator:closeAll": "closeAllNavigators",
      "navigator:close": "closeNavigator",
    },

    closeNavigator: function closeNavigator(view) {
      this.collection.remove(view.model);
    },

    closeAllNavigators: function closeAllNavigators() {
      this.collection.reset();
    },

    openUrl: function openUrl(url) {
      var existing = this.collection.find(function find(navigator) {
        return navigator.get("url") === url;
      });

      if (existing) {
        this.focusNavigator(existing);
      }

      var navigator = new Navigator(url);
      this.collection.add([navigator]);
    },

    focusNavigator: function focusNavigator(navigator) {
      var view = this.children.findByModel(navigator);
      return view.focus();
    },
  });

  return NavigatorCollectionView;
});
