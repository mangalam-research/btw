/**
 * @module lib/btw/semantic_field_editor/views/field/inline
 * @desc An inline view for esmantic fields.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var $ = require("jquery");
  var _ = require("lodash");
  var Mn = require("marionette");
  var fieldTemplate = require("text!./inline.html");
  var sfTemplate = require("text!btw/btw_view_sf_template.html");
  require("bootstrap-treeview");

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

      content.innerHTML = _.template(sfTemplate)({ keys: keys,
                                                   resolved: alreadyResolved });

      var treeDivs = tip.getElementsByClassName("tree");
      for (var treeDivIx = 0; treeDivIx < treeDivs.length; ++treeDivIx) {
        var treeDiv = treeDivs[treeDivIx];
        var key = keys[keyIx++];
        var field = alreadyResolved[key];

        if (field.tree.length === 0) {
          continue; // Nothing to show!
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
          continue;
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
      // popup. If the popover is recreated, then ``tip`` will be new, and
      // destroying the popup removes the event handlers that were created.
      var method = tip.classList.contains("in") ? "destroy" : "show";
      popover[method]();

      // If we're not showing the popup, then we are done.
      if (method !== "show") {
        return;
      }

      // Otherwise, we need to set handlers.
      tip.classList.add("sf-popover");

      function stopPropagation(ev) {
        ev.stopPropagation();
      }

      $tip.on("click mousedown contextmenu", stopPropagation);
    });
  }

  var InlineView = Mn.LayoutView.extend({
    initialize: function initialize(options) {
      this.fetcher = options.fetcher;
      this.canDelete = options.canDelete;
      delete options.fetcher;
      delete options.canDelete;
      Mn.LayoutView.prototype.initialize.apply(this, arguments);
    },

    tagName: "span",

    className: "btn btn-default sf-popover-button _phantom_wrap " +
      "_gui _inline field-view",

    attributes: {
      role: "button",
      contenteditable: "false",
    },

    template: _.template(fieldTemplate),

    templateHelpers: function templateHelpers() {
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
      "click @ui.deleteButton": "deleteSF",
    },

    deleteSF: function remove() {
      this.model.destroy();
    },

    onRender: function onRender() {
      var a = this.ui.popoverButton;
      var ref = this.model.get("path");
      attachPopover(a, ref, this.fetcher, true);
    },
  });

  return InlineView;
});
