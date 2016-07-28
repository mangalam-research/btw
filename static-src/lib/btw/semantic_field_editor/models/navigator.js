/**
 * @module lib/btw/semantic_field_editor/models/navigator
 * @desc A model for navigators.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";

  var Bb = require("backbone");
  var Field = require("./field");
  var _ = require("lodash");

  var Page = Field.extend({
    __classname__: "Page",
    initialize: function initialize(attributes, options) {
      this.url = options.url;
      delete options.url;
      Field.prototype.initialize.call(this, attributes, options);
    },

    sync: function sync(method, model, options) {
      options.btwAjax = true;
      options.data = _.extend({}, options.data, {
        fields: "@details",
        "depths.parent": -1,
        "depths.related_by_pos": 1,
        "depths.children": 1,
      });

      return Field.prototype.sync.call(this, method, model, options);
    },
  });

  // We used to have this be a RelationalModel instance but the events generated
  // by backbone-relational do not check whether the view they affect has been
  // destroyed. So we would get errors about updates on destroyed views.
  var Navigator = Bb.Model.extend({
    __classname__: "Navigator",
    defaults: {
      index: -1,
    },

    initialize: function initialize(url, attributes, options) {
      Bb.Model.prototype.initialize.call(this, attributes, options);
      this.attributes.pages = new Bb.Collection();
      this.addPage(url);
    },

    addPage: function addPage(url) {
      var page = new Page({}, { url: url });
      page.on("change", function change() {
        this.trigger("pageChange", page);
      }.bind(this));
      var index = this.get("index") + 1;
      var pages = this.get("pages").models.slice(0, index);
      pages.push(page);
      this.set({
        index: index,
      });
      this.attributes.pages.reset(pages);
      page.fetch();
    },

    moveToFirstPage: function moveToFirstPage() {
      this.set("index", 0);
    },

    moveToLastPage: function moveToLastPage() {
      var length = this.get("pages").models.length;
      this.set("index", length - 1);
    },

    moveToNextPage: function moveToNextPage() {
      var length = this.get("pages").models.length;
      var index = this.get("index");
      if (index < length - 1) {
        index++;
        this.set("index", index);
      }
    },

    moveToPreviousPage: function moveToPreviousPage() {
      var index = this.get("index");
      if (index > 0) {
        index--;
        this.set("index", index);
      }
    },

    getCurrentUrl: function getCurrentUrl() {
      return this.getCurrentPage().get("url");
    },

    getCurrentPage: function getCurrentPage() {
      return this.get("pages").at((this.get("index")));
    },
  });

  return Navigator;
});
