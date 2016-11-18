/**
 * @module lib/btw/semantic_field_editor/views/field/inline
 * @desc An inline view for esmantic fields.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, _exports, _module) {
  "use strict";
  var $ = require("jquery");
  var _ = require("lodash");
  var Mn = require("marionette");
  var fieldTemplate = require("text!./inline.hbs").replace(/\\\n/g, "");
  var popoverTemplate = require("text!./popover.hbs");
  var Handlebars = require("handlebars");
  require("bootstrap-treeview");

  var popoverTemplateCompiled = Handlebars.compile(popoverTemplate);

  function attachPopover(a, ref, sfFetcher, forEditing) {
    var initialContent = "<i class='fa fa-spinner fa-2x fa-spin'></i>";
    var $a = $(a);
    var alreadyResolved;
    function makeContent() {
      if (!alreadyResolved) {
        sfFetcher.fetch([ref]).then(function then(resolved) {
          alreadyResolved = resolved;

          // This causes rerendering of the popover and makeContent to be
          // called again.
          $a.popover("show");
        });

        return initialContent;
      }


      var popover = $a.data("bs.popover");
      var $tip = popover.tip();
      var tip = $tip[0];

      var content = tip.getElementsByClassName("popover-content")[0];
      var keys = Object.keys(alreadyResolved).sort();
      var keyIx = 0;

      var resolved = keys.map(function map(key) {
        return alreadyResolved[key];
      });
      content.innerHTML = popoverTemplateCompiled({ resolved: resolved });

      var treeDivs = tip.getElementsByClassName("tree");
      for (var treeDivIx = 0; treeDivIx < treeDivs.length; ++treeDivIx) {
        var treeDiv = treeDivs[treeDivIx];
        var key = keys[keyIx++];
        var field = alreadyResolved[key];

        if (field.tree.length === 0) {
          // Nothing to show!
          continue; // eslint-disable-line no-continue
        }

        // If there is only one element at the top of the tree, and this element
        // has only one child, then what we have is a single entry which would
        // have only one version available. There's no need to have a proper
        // tree for this.
        if (field.tree.length === 1 && field.tree[0].nodes.length <= 1) {
          var node = field.tree[0];
          var link = treeDiv.ownerDocument.createElement("a");
          link.textContent = node.text;
          link.href = node.href;
          treeDiv.appendChild(link);
          continue; // eslint-disable-line no-continue
        }

        // Otherwise: build a tree.
        $(treeDiv).treeview({
          data: field.tree,
          enableLinks: true,
          levels: 0,
        });
      }

      // Inform that the popover has been fully rendered. This is used mainly in
      // testing.
      $a.trigger("fully-rendered.btw-view.sf-popover");

      return Array.prototype.slice.call(content.childNodes);
    }

    $a.on("click", function click(ev) {
      ev.stopPropagation();
      ev.preventDefault();
      // If there is already a popover existing for this element, this call
      // won't create a new one.
      $a.popover({
        html: true,
        trigger: "manual",
        content: makeContent,
      });

      var popover = $a.data("bs.popover");

      // The stock hasContent is very expensive.
      popover.hasContent = function hasContent() {
        return true;
      };

      var $tip = popover.tip();
      var tip = $tip[0];
      if (forEditing) {
        tip.setAttribute("contenteditable", false);
        tip.classList.add("_phantom", "_gui");
      }

      // Note that we destroy the popover when we "close" it. This is also why
      // we add the event handlers below for every click that shows the
      // popover. If the popover is recreated, then ``tip`` will be new, and
      // destroying the popover removes the event handlers that were created.
      var method = tip.classList.contains("in") ? "destroy" : "show";
      popover[method]();

      // If we're not showing the popover, then we are done.
      if (method !== "show") {
        return;
      }

      // Otherwise, we need to set handlers.
      tip.classList.add("sf-popover");

      function stopPropagation(stopEv) {
        stopEv.stopPropagation();
      }

      $tip.on("click mousedown contextmenu", stopPropagation);
    });
  }

  var InlineView = Mn.View.extend({
    __classname__: "InlineView",
    initialize: function initialize(options) {
      this.fetcher = options.fetcher;
      this.canDelete = options.canDelete;
      InlineView.__super__.initialize.call(
        this, _.omit(options, ["fetcher", "canDelete"]));
    },

    tagName: "span",
    className: "_phantom_wrap",

    attributes: {
      role: "button",
      contenteditable: "false",
    },

    template: Handlebars.compile(fieldTemplate),

    templateContext: function templateContext() {
      return {
        canDelete: this.canDelete,
      };
    },

    ui: {
      deleteButton: ".delete-button",
      popoverButton: ".popover-button",
      field: ".field",
    },

    events: {
      "click @ui.deleteButton": "onDeleteClick",
    },

    onDeleteClick: function onDeleteClick(ev) {
      ev.stopPropagation();
      ev.preventDefault();
      this.triggerMethod("sf:delete", this.model);
    },

    onRender: function onRender() {
      var a = this.ui.popoverButton;
      var ref = this.model.get("path");
      attachPopover(a, ref, this.fetcher, true);
    },
  });

  return InlineView;
});
