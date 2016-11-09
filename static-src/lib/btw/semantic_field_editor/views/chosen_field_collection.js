/**
 * @module lib/btw/semantic_field_editor/views/chosen_field_collection
 * @desc Editor for semantic field lists.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, _exports, _module) {
  "use strict";
  var Mn = require("marionette");
  var Handlebars = require("handlebars");
  var FieldView = require("./field/inline");
  var template = require("text!./panel.hbs");
  var dragula = require("dragula");
  var _ = require("lodash");

  function id(x) {
    return function innerId() {
      return x;
    };
  }

  var EmptyCollectionView = Mn.View.extend({
    template: id("No fields."),
  });

  var ChosenFieldCollectionBodyView = Mn.CollectionView.extend({
    initialize: function initialize(options) {
      this.fetcher = this.fetcher || options.fetcher;
      this.canDelete = this.canDelete || options.canDelete;
      delete options.fetcher;
      ChosenFieldCollectionBodyView.__super__.initialize.call(
        this, _.omit(options, ["fetcher", "canDelete"]));
    },
    childView: FieldView,
    childViewOptions: function childViewOptions() {
      return {
        fetcher: this.fetcher,
        canDelete: this.canDelete,
      };
    },

    childViewTriggers: {
      "sf:delete": "sf:delete", // bubble up
    },

    emptyView: EmptyCollectionView,

    findChildViewByEl: function findChildViewByEl(el) {
      return this.children.find(function find(view) {
        return view.el === el;
      });
    },

    _setDragAndDrop: function _setDragAndDrop() {
      if (this._currentDrake) {
        this._currentDrake.destroy();
      }

      // The way dragula works, it will update the DOM when the user drops an
      // element in a new position. So from that point on, the DOM is in a state
      // that is inconsistent with what the Marionette view expects. We listen
      // to the ``drop`` event so that we can update the collection and trigger
      // the view to refresh the DOM. It will effectively rebuild a DOM that
      // looks like what the DOM was after dragula moved elements around. This
      // may seem wasteful but it is not clear that there is an easy way to
      // optimize this. Marionette views maintain internal state that is
      // supposed to correspond to what they puts out in the DOM. This state
      // would have to be updated too. Having the view rebuild the DOM is the
      // easiest way to have everything line up and avoid nasty surprises.
      var drake = dragula([this.el]);
      drake.on("drop", this.onChildDrop.bind(this));
      this._currentDrake = drake;
    },

    onChildDrop: function onChildDrop(el, target, source, sibling) {
      // This can happen if the user drags something outside the list.  It can
      // also happen when the DOM is reorganized by the work we do in this
      // function.
      if (target === null) {
        return;
      }

      var movedView = this.findChildViewByEl(el);
      if (!movedView) {
        throw new Error("cannot find the view that was moved");
      }
      var movedModel = movedView.model;

      // There may be no sibling if we are moving to the end of the list.
      var siblingModel;
      if (sibling) {
        var siblingView = this.findChildViewByEl(sibling);
        if (!siblingView) {
          throw new Error("cannot find the sibling view");
        }
        siblingModel = siblingView.model;
      }

      // Copy the list of models to manipulate it. It is not clear that
      // just editing the list in place is safe.
      var newOrder = this.collection.models.slice();

      // Drop the model we are moving from the list.
      var movedModelIndex = newOrder.indexOf(movedModel);
      newOrder.splice(movedModelIndex, 1);

      // Add it before the sibling.
      var siblingModelIndex = siblingModel ?
            newOrder.indexOf(siblingModel) :
            newOrder.length;
      newOrder.splice(siblingModelIndex, 0, movedModel);

      // Update the collection.
      this.collection.reset(newOrder);
    },

    onRender: function onRender() {
      this._setDragAndDrop();
    },

  });

  var ChosenFieldCollectionView = Mn.View.extend({
    initialize: function initialize(options) {
      this.fetcher = this.fetcher || options.fetcher;
      this.panelTitle = this.panelTitle || options.panelTitle;
      this.canDelete = this.canDelete || options.canDelete;
      Mn.View.prototype.initialize.call(
        this,
        _.omit(options, ["fetcher", "panelTitle", "canDelete"]));
    },

    tagName: "div",

    template: Handlebars.compile(template),

    templateContext: function templateContext() {
      return {
        panelTitle: this.panelTitle,
        panelBody: "",
      };
    },

    regions: {
      body: ".panel-body",
    },

    childViewEvents: {
      "sf:delete": "_deleteSF",
    },

    _deleteSF: function _deleteSF(model) {
      this.deleteSF(model);
    },

    deleteSF: function deleteSF(model) {
      this.collection.remove(model);
    },

    addSF: function addSF(model) {
      this.collection.add(model);
    },

    onRender: function onRender() {
      this.showChildView("body", new ChosenFieldCollectionBodyView({
        collection: this.collection,
        fetcher: this.fetcher,
        canDelete: this.canDelete,
      }));
    },
  });

  return ChosenFieldCollectionView;
});
