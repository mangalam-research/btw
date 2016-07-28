/**
 * @module lib/btw/semantic_field_editor/views/chosen_field_collection
 * @desc Editor for semantic field lists.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var Mn = require("marionette");
  var Handlebars = require("handlebars");
  var FieldView = require("./field/inline");
  var template = require("text!./panel.hbs");

  var ChosenFieldCollectionBodyView = Mn.CollectionView.extend({
    initialize: function initialize(options) {
      this.fetcher = options.fetcher;
      delete options.fetcher;
      Mn.CollectionView.prototype.initialize.apply(this, arguments);
    },
    childView: FieldView,
    childViewOptions: function childViewOptions() {
      return {
        fetcher: this.fetcher,
        canDelete: true,
      };
    },
  });

  var ChosenFieldCollectionView = Mn.LayoutView.extend({
    initialize: function initialize(options) {
      this.fetcher = options.fetcher;
      delete options.fetcher;
      Mn.LayoutView.prototype.initialize.apply(this, arguments);
    },

    tagName: "div",

    template: Handlebars.compile(template),

    templateHelpers: {
      panelTitle: "Chosen Semantic Fields",
      panelBody: "",
    },

    regions: {
      body: ".panel-body",
    },

    onShow: function onShow() {
      this.showChildView("body", new ChosenFieldCollectionBodyView({
        collection: this.collection,
        fetcher: this.fetcher,
      }));
    },
  });

  return ChosenFieldCollectionView;
});
