/**
 * @module lib/btw/semantic_field_editor/app
 * @desc Editor for semantic field lists.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends module:lib/btw/semantic_field_editor/app */ function factory(
  require, exports, _module) {
  "use strict";
  var Bb = require("backbone");
  var Mn = require("marionette");
  var ajax = require("ajax").ajax$;
  var layoutTemplate = require("text!./layout.html");
  var ChosenFieldCollectionView = require("./views/chosen_field_collection");
  var SearchView = require("./views/search");
  var NavigatorCollectionView = require("./views/navigators/navigator_collection");
  var Field = require("./models/field");

  var origAjax = Bb.ajax;

  Bb.ajax = function ajaxWrapper(options) {
    if (!options.btwAjax) {
      return origAjax.call(this, options);
    }

    return ajax(options).xhr;
  };

  var ChosenFieldCollection = Bb.Collection.extend({
    Model: Field,
  });

  var LayoutView = Mn.LayoutView.extend({
    template: layoutTemplate,
    regions: {
      fieldList: ".sf-field-list",
      search: ".sf-search",
      navigators: ".sf-navigators",
    },
  });

  var SFEditor = Mn.Application.extend({
    initialize: function initialize(options) {
      var container = options.container;
      delete options.container;

      var fields = options.fields;
      delete options.fields;

      this.fetcher = options.fetcher;
      delete options.fetcher;

      Mn.Application.prototype.initialize.apply(this, arguments);
      var fieldCollection = new ChosenFieldCollection(fields);
      this.layoutView = new LayoutView({
        el: container,

        childEvents: {
          "sf:selected": this.showSF.bind(this),
        },
      });
      this.layoutView.render();
      this.layoutView.showChildView("fieldList", new ChosenFieldCollectionView({
        collection: fieldCollection,
        fetcher: this.fetcher,
      }));
      this.layoutView.showChildView("search", new SearchView({
        searchUrl: this.searchUrl,
      }));
      this.navigatorsView = new NavigatorCollectionView();
      this.layoutView.showChildView("navigators", this.navigatorsView);
    },

    showSF: function showSF(view, url) {
      this.navigatorsView.openUrl(url);
    },
  });

  exports.SFEditor = SFEditor;
});
