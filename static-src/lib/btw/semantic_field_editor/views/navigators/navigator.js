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
  require("velocity-ui");

  var htmlTemplate = "\
<div class='panel panel-default semantic-field-details-panel'>\
  <div class='panel-heading'>\
    <h4 class='panel-title'>\
      Semantic Field Details <button class='btn btn-xs btn-default first' href='#'><i class='fa fa-fast-backward'></i></button> <button class='btn btn-xs btn-default previous' href='#'><i class='fa fa-backward'></i></button> <button class='btn btn-xs btn-default next' href='#'><i class='fa fa-forward'></i></button> <button class='btn btn-xs btn-default last' href='#'><i class='fa fa-fast-forward'></i></button><button class='btn btn-xs btn-default close-panel' href='#' title='Close'><i class='fa fa-times'></i></button> <button class='btn btn-xs btn-default close-all-panels' href='#' title='Close all'><i class='fa fa-times'></i><i class='fa fa-times'></i>\
</button>\
    </h4>\
  </div>\
  <div class='panel-body'>\
    <div class='paged-content'>\
    </div>\
  </div>\
</div>\
";

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

  var NavigatorView = Mn.LayoutView.extend({
    template: id(htmlTemplate),

    regions: {
      content: ".paged-content",
    },

    ui: {
      first: ".btn.first",
      previous: ".btn.previous",
      next: ".btn.next",
      last: ".btn.last",
      closePanel: ".btn.close-panel",
      closeAllPanels: ".btn.close-all-panels",
    },

    events: {
      "click @ui.first": dispatchToModel("moveToFirstPage"),
      "click @ui.last": dispatchToModel("moveToLastPage"),
      "click @ui.next": dispatchToModel("moveToNextPage"),
      "click @ui.previous": dispatchToModel("moveToPreviousPage"),
    },

    triggers: {
      "click @ui.closePanel": "navigator:close",
      "click @ui.closeAllPanels": "navigator:closeAll",
    },

    childEvents: {
      "sf:selected": "showSF",
    },

    modelEvents: {
      pageChange: "display",
      "change:index": "display",
    },

    showSF: function showSF(view, url) {
      this.model.addPage(url);
    },

    focus: function focus() {
      this.el.scrollIntoView();
      return velocity(this.el, "callout.shake").return(this);
    },

    onAttach: function onAttach() {
      this.el.scrollIntoView();
      velocity(this.el, "transition.expandIn");
    },

    display: function display() {
      this.showChildView("content", new PageView({
        model: this.model.getCurrentPage(),
      }));
    },

    remove: function remove() {
      velocity(this.el, "transition.expandOut").then(function removed() {
        this.constructor.__super__.remove.call(this);
        this.triggerMethod("dom:removed");
      }.bind(this));
      return this;
    },
  });

  return NavigatorView;
});
