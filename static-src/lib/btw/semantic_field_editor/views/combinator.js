/**
 * @module lib/btw/semantic_field_editor/views/combinator
 * @desc Semantic field combinator.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, _exports, _module) {
  "use strict";
  var Mn = require("marionette");
  var Handlebars = require("handlebars");
  var Field = require("../models/field");
  var template = require("text!./panel.hbs");
  var tools = require("../tools");
  var _ = require("lodash");
  var ChosenFieldCollection = require("../collections/chosen_field");
  var ChosenFieldCollectionView = require("./chosen_field_collection");

  var CombinatorElementsView = ChosenFieldCollectionView.extend({
    __classname__: "CombinatorElementsView",
    canDelete: true,
  });

  var ResultView = ChosenFieldCollectionView.extend({
    __classname__: "ResultView",
    initialize: function initialize(options) {
      options = _.extend({}, options);
      options.panelTitle = new Handlebars.SafeString(
        "Result of Combining <button class='btn btn-default sf-add'>" +
          "<i class='fa fa-fw fa-thumbs-up'></i></button>");
      ResultView.__super__.initialize.call(this, options);
    },

    ui: {
      addButton: ".sf-add",
    },

    events: {
      "click @ui.addButton": "_onAddButtonClick",
    },

    collectionEvents: {
      "remove add reset": "_updateAddButton",
    },

    _updateAddButton: function _updateAddButton() {
      this.ui.addButton[0].disabled = this.collection.length === 0;
    },

    onRender: function onRender() {
      this._updateAddButton();
      return ResultView.__super__.onRender.apply(this, arguments);
    },

    _onAddButtonClick: function _onAddButtonClick(ev) {
      ev.stopPropagation();
      ev.preventDefault();
      if (this.collection.length > 0) {
        this.triggerMethod("sf:add", this.collection.at(0));
      }
    },
  });

  var CombinatorView = Mn.View.extend({
    __classname__: "CombinatorView",
    initialize: function initialize(options) {
      this.fetcher = options.fetcher;
      this.resultCollection = new ChosenFieldCollection();
      this.elementsCollection = new ChosenFieldCollection();

      this.elementsCollection.on("update reset",
                                 this.onElementsUpdated.bind(this));
      tools.GettersMixin.call(this);
      CombinatorView.__super__.initialize.call(this,
                                               _.omit(options, ["fetcher"]));
    },

    tagName: "div",

    template: Handlebars.compile(template),

    templateContext: function templateContext() {
      return {
        collapse: true,
        headingId: "sf-editor-collapse-heading-" + this.cid,
        collapseId: "sf-editor-collapse-" + this.cid,
        panelTitle: "Field Combinator",
        panelBody: new Handlebars.SafeString(
        "<div class='combinator-results'>" +
          "</div><div class='combinator-elements'></div>"),
      };
    },

    regions: {
      results: ".combinator-results",
      elements: ".combinator-elements",
    },

    getters: tools.communicationGetters,

    addSF: function addSF(model) {
      this.elementsCollection.add(model);
    },

    // This uses the chidview:* magic.
    onChildviewSfAdd: function onSfAdd(model) {
      this.channel.trigger("sf:add", this, model);
    },

    onElementsUpdated: function onElementsUpdated() {
      var combined = this.elementsCollection.reduce(
        function reduce(expr, curr) {
          return !expr ? curr.get("path") : expr + "@" + curr.get("path");
        }, null);
      if (combined) {
        this.fetcher.fetch([combined]).then(function then(fetched) {
          var field = new Field(fetched[combined]);
          this.resultCollection.reset(field);
        }.bind(this));
      }
      else {
        this.resultCollection.reset([]);
      }
    },

    onRender: function onRender() {
      this.resultView = new ResultView({
        collection: this.resultCollection,
        fetcher: this.fetcher,
      });
      this.showChildView("results", this.resultView);

      this.elementsView = new CombinatorElementsView({
        panelTitle: "Elements to Combine",
        collection: this.elementsCollection,
        fetcher: this.fetcher,
      });
      this.showChildView("elements", this.elementsView);
    },
  });

  return CombinatorView;
});
