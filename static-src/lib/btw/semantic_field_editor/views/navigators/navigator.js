/**
 * @module lib/btw/semantic_field_editor/views/navigators/navigator
 * @desc A view for a single navigator.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var Mn = require("marionette");
  var velocity = require("velocity");
  var PageView = require("./page");
  var Promise = require("bluebird");
  var template = require("text!./navigator.html");
  var _ = require("lodash");
  require("velocity-ui");

  function id(x) {
    return function innerId() {
      return x;
    };
  }

  function dispatchToModel(method) {
    return function dispatchToModelInner(ev) {
      ev.stopPropagation();
      ev.preventDefault();
      this.model[method].apply(this.model, arguments);
    };
  }

  function slideRightIn(el) {
    return velocity(el,
                    { opacity: [1, 0], translateX: [0, "100%"],
                      translateZ: 0 },
                    { duration: 500 });
  }

  function slideLeftIn(el) {
    return velocity(el,
                    { opacity: [1, 0], translateX: [0, "-100%"],
                      translateZ: 0 },
                    { duration: 500 });
  }

  var PageCollectionView = Mn.CollectionView.extend({
    __classname__: "PageCollectionView",
    initialize: function initialize(options) {
      this.navigator = options.navigator;
      this.canAddResults = options.canAddResults;
      this.collection = this.navigator.get("pages");
      PageCollectionView.__super__.initialize.apply(
        this, _.omit(options, ["navigator", "canAddResults"]));
    },

    childView: PageView,

    childViewOptions: function childViewOptions() {
      // Yes, the name is different on the child. If the result collection can
      // add results, then the results themselves can be added.
      return {
        canBeAdded: this.canAddResults,
      };
    },

    filter: function filter(child, index, _collection) {
      return index === this.navigator.get("index");
    },
  });

  var NavigatorView = Mn.View.extend({
    __classname__: "NavigatorView",
    initialize: function initialize(options) {
      this.canAddResults = options.canAddResults;
      NavigatorView.__super__.initialize.call(
        this, _.omit(options, ["canAddResults"]));
    },

    template: id(template),

    regions: {
      content: ".paged-content",
    },

    ui: {
      first: ".btn.first",
      previous: ".btn.previous",
      next: ".btn.next",
      last: ".btn.last",
      closeNavigator: ".btn.close-navigator",
      closeAllNavigators: ".btn.close-all-navigators",
      pagedContent: ".paged-content",
    },

    events: {
      "click @ui.first": dispatchToModel("moveToFirstPage"),
      "click @ui.last": dispatchToModel("moveToLastPage"),
      "click @ui.next": dispatchToModel("moveToNextPage"),
      "click @ui.previous": dispatchToModel("moveToPreviousPage"),
    },

    triggers: {
      "click @ui.closeNavigator": "navigator:close",
      "click @ui.closeAllNavigators": "navigator:closeAll",
    },

    childViewEvents: {
      "sf:selected": "_showSF",
    },

    modelEvents: function modelEvents() {
      return {
        pageSync: "_display",
        "change:index": "_display",
      };
    },

    _showSF: function _showSF(url) {
      if (url !== this.model.getCurrentUrl()) {
        this.model.addPage(url);
      }
    },

    _focus: function _focus() {
      this.el.scrollIntoView();
      return velocity(this.el, "callout.shake").return(this);
    },

    firstDisplay: true,
    _displayedIndex: undefined,

    _display: function _display() {
      // This can happen in testing.
      if (!this.getRegion("content")) {
        return;
      }

      this.showChildView("content", new PageCollectionView({
        navigator: this.model,
        canAddResults: this.canAddResults,
      }));

      var newIndex = this.model.get("index");
      var prevIndex = this._displayedIndex;
      this._displayedIndex = newIndex;
      var pagedContent = this.ui.pagedContent[0];
      this.el.scrollIntoView();
      if (this.firstDisplay) {
        this.firstDisplay = false;
        velocity(this.el, "transition.expandIn").then(function done() {
          this.triggerMethod("dom:displayed");
        }.bind(this));
      }
      else if (newIndex > prevIndex) {
        slideLeftIn(pagedContent).then(function done() {
          this.triggerMethod("dom:displayed");
        }.bind(this));
      }
      else if (newIndex < prevIndex) {
        slideRightIn(pagedContent).then(function done() {
          this.triggerMethod("dom:displayed");
        }.bind(this));
      }
      else {
        this.triggerMethod("dom:displayed");
      }
    },

    makeEventPromise: function makeEventPromise(event) {
      var view = this;
      return new Promise(function promiseFactory(resolve) {
        view.once(event, function handler() {
          resolve(view);
        });
      });
    },

    makeDOMDisplayedPromise: function makeDOMDisplayedPromise() {
      return this.makeEventPromise("dom:displayed");
    },

    _inDOM: function _inDOM() {
      return !!this.el.parentNode;
    },

    makeDOMRemovedPromise: function makeDOMRemovedPromise() {
      // If it is not in the dom, dom:removed won't ever happen so we signal
      // this by returning null. We do not return a Promise that is already
      // resolved because the caller should *know* what is going on.
      if (!this._inDOM()) {
        return null;
      }
      return this.makeEventPromise("dom:removed");
    },

    _isRemoving: false,

    destroy: function destroy() {
      // If it is not in the DOM, don't do anything.
      //
      // We check parentNode because using the standard Backbone functions would
      // simply remove this.el from its parent. If it was removed from the DOM
      // because an ancestor was removed, don't consider it "removed".
      //
      if (!this._inDOM() || this._isRemoving) {
        return this;
      }

      this._isRemoving = true;
      // Otherwise, we perform an animation and then remove it.
      velocity(this.el, "transition.expandOut").then(function removed() {
        NavigatorView.__super__.destroy.call(this);
        this.triggerMethod("dom:removed");
      }.bind(this));

      return this;
    },
  });

  return NavigatorView;
});
