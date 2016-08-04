/**
 * @module lib/btw/semantic_field_editor/app
 * @desc Editor for semantic field lists.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends module:lib/btw/semantic_field_editor/app */ function factory(
  require, exports, _module) {
  "use strict";
  var $ = require("jquery");
  var Bb = require("backbone");
  var Mn = require("marionette");
  var ajax = require("ajax").ajax$;
  var layoutTemplate = require("text!./layout.html");
  var ChosenFieldCollectionView = require("./views/chosen_field_collection");
  var CombinatorView = require("./views/combinator");
  var SearchView = require("./views/search");
  var NavigatorCollectionView = require("./views/navigators/navigator_collection");
  var ChosenFieldCollection = require("./collections/chosen_field");
  var tools = require("./tools");
  var _ = require("lodash");

  var origAjax = Bb.ajax;

  Bb.ajax = function ajaxWrapper(options) {
    if (!options.btwAjax) {
      return origAjax.call(this, options);
    }

    var result = ajax(options);
    result.promise.asCallback(function () {});

    return result.xhr;
  };

  var LayoutView = Mn.LayoutView.extend({
    template: layoutTemplate,
    regions: {
      fieldList: ".sf-field-list",
      combinator: ".sf-combinator",
      search: ".sf-search",
      navigators: ".sf-navigators",
    },
  });

  var SFEditor = Mn.Application.extend({
    initialize: function initialize(options) {
      var container = this.container = options.container;
      this.fields = options.fields;
      this.fetcher = options.fetcher;
      tools.setApplication(container, this);
      this.channelPrefix = options.channelPrefix || "SFEditor:";
      this.channels = {
        global: this.channelPrefix + "global",
      };

      SFEditor.__super__.initialize.call(
        this, _.omit(options, ["container", "fields", "fetcher"]));
    },

    onStart: function onStart() {
      var fieldCollection = this._chosenFieldCollection =
            new ChosenFieldCollection(this.fields);

      fieldCollection.on("update reset",
                         this.triggerMethod.bind(this, "sf:chosen:change"));

      this.layoutView = new LayoutView({
        el: this.container,

        childEvents: {
          "sf:selected": this.navigateSF.bind(this),
        },
      });

      var chosenFieldCollectionView = new ChosenFieldCollectionView({
        panelTitle: "Chosen Semantic Fields",
        collection: fieldCollection,
        fetcher: this.fetcher,
        canDelete: true,
      });

      var combinatorView = this.combinatorView = new CombinatorView({
        fetcher: this.fetcher,
      });

      this.layoutView.render();
      this.layoutView.showChildView("fieldList", chosenFieldCollectionView);
      this.layoutView.showChildView("combinator", combinatorView);

      this.layoutView.showChildView("search", new SearchView({
        searchUrl: this.searchUrl,
        canAddResults: true,
      }));
      this.navigatorsView = new NavigatorCollectionView({
        canAddResults: true,
      });
      this.layoutView.showChildView("navigators", this.navigatorsView);

      var global = Bb.Radio.channel(this.channels.global);
      global.on("sf:add", function onAdd(view, model) {
        chosenFieldCollectionView.addSF(model);
      });

      global.on("sf:combine", function onCombine(view, model) {
        combinatorView.addSF(model);
      });
    },

    navigateSF: function navigateSF(view, url) {
      this.navigatorsView.openUrl(url);
    },

    getChosenFields: function () {
      return this._chosenFieldCollection.toArray();
    },

    destroy: function destroy() {
      this.layoutView.destroy();
    },
  });

  return SFEditor;
});
