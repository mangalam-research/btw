/**
 * @module wed/modes/btw/btw_dispatch
 * @desc The dispatch logic common to editing and displaying articles.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends module:wed/modes/btw/btw_decorator */ function btwDecorator(
  require, exports, _module) {
  "use strict";

  var util = require("wed/util");
  var $ = require("jquery");
  var tooltip = require("wed/gui/tooltip").tooltip;
  var domutil = require("wed/domutil");
  var Decorator = require("wed/decorator").Decorator;
  var btwUtil = require("./btw_util");
  var FieldView = require("./semantic_field_editor/views/field/inline");
  var Field = require("./semantic_field_editor/models/field");
  require("bootstrap-treeview");

  /**
   * This mixin is made to be used by the {@link module:wed/decorator~Decorator
   * Decorator} created for BTW's mode and by {@link
   * module:wed/modes/btw/btw_view~Viewer Viewer}. It combines decoration
   * methods that are common to editing and viewing articles.
   */
  function DispatchMixin() {
    this._inMode = this instanceof Decorator;
  }

  var DispatchMixinP = DispatchMixin.prototype;

  DispatchMixinP.dispatch = function dispatch(root, el) {
    var klass = this._meta.getAdditionalClasses(el);
    if (klass.length) {
      el.className += " " + klass;
    }

    var name = util.getOriginalName(el);
    var skipDefault = false;
    switch (name) {
    case "btw:overview":
    case "btw:sense-discrimination":
    case "btw:historico-semantical-data":
    case "btw:credits":
      this._heading_decorator.unitHeadingDecorator(el);
      break;
    case "btw:definition":
    case "btw:english-renditions":
    case "btw:english-rendition":
    case "btw:etymology":
    case "btw:contrastive-section":
    case "btw:antonyms":
    case "btw:cognates":
    case "btw:conceptual-proximates":
    case "btw:other-citations":
    case "btw:citations":
      this._heading_decorator.sectionHeadingDecorator(el);
      break;
    case "btw:semantic-fields":
      this._heading_decorator.sectionHeadingDecorator(el);
      break;
    case "btw:sf":
      this.sfDecorator(root, el);
      skipDefault = true;
      break;
    case "ptr":
      this.ptrDecorator(root, el);
      break;
    case "foreign":
      this.languageDecorator(el);
      break;
    case "ref":
      this.refDecorator(root, el);
      break;
    case "btw:example":
      this.idDecorator(root, el);
      break;
    case "btw:cit":
      this.citDecorator(root, el);
      skipDefault = true; // citDecorator calls elementDecorator
      break;
    case "btw:explanation":
      this.explanationDecorator(root, el);
      skipDefault = true; // explanationDecorator calls elementDecorator
      break;
    case "btw:none":
      this.noneDecorator(root, el);
      // THIS ELEMENT DOES NOT GET THE REGULAR DECORATION.
      skipDefault = true;
      break;
    default:
      break;
    }

    if (!skipDefault) {
      this.elementDecorator(root, el);
    }
  };

  DispatchMixinP._getIDManagerForRefman = function _getIDManagerForRefman(
    refman) {
    switch (refman.name) {
    case "sense":
    case "subsense":
      return this._sense_subsense_id_manager;
    case "example":
      return this._example_id_manager;
    default:
      throw new Error("unexpected name: " + refman.name);
    }
  };

  DispatchMixinP.idDecorator = function idDecorator(root, el) {
    var refman = this._refmans.getRefmanForElement(el);
    if (refman) {
      var wedId = el.id;
      if (!wedId) {
        var id = el.getAttribute(util.encodeAttrName("xml:id"));
        var idMan = this._getIDManagerForRefman(refman);
        wedId = "BTW-" + (id || idMan.generate());
        el.id = wedId;
      }

      // We have some reference managers that don't derive from
      // ReferenceManager and thus do not have this method.
      if (refman.allocateLabel) {
        refman.allocateLabel(wedId);
      }
    }
  };

  var WHEEL = "☸";

  DispatchMixinP.explanationDecorator = function explanationDecorator(root,
                                                                      el) {
    var child;
    var next;
    var div; // Damn hoisting...
    // Handle explanations that are in btw:example-explained.
    if (el.parentNode.classList.contains("btw:example-explained")) {
      child = el.firstElementChild;
      while (child) {
        next = child.nextElementSibling;
        if (child.classList.contains("_explanation_bullet")) {
          this._gui_updater.removeNode(child);
          break; // There's only one.
        }
        child = next;
      }

      var cit = domutil.siblingByClass(el, "btw:cit");
      // If the next btw:cit element contains Pāli text.
      if (cit &&
          cit.querySelector("*[" + util.encodeAttrName("xml:lang") +
                            "='pi-Latn']")) {
        div = el.ownerDocument.createElement("div");
        div.className = "_phantom _decoration_text _explanation_bullet";
        div.style.position = "absolute";
        div.style.left = "-1em";
        div.textContent = WHEEL;
        this._gui_updater.insertNodeAt(el, 0, div);
        el.style.position = "relative";
      }
      this.elementDecorator(root, el);
      return;
    }

    this.elementDecorator(root, el);
    var label;
    var parent = el.parentNode;
    // Is it in a subsense?
    if (parent.classList.contains("btw:subsense")) {
      var refman = this._refmans.getSubsenseRefman(el);
      label = refman.idToSublabel(parent.id);
      child = el.firstElementChild;
      var start;
      while (child) {
        next = child.nextElementSibling;
        if (child.classList.contains("_explanation_number")) {
          this._gui_updater.removeNode(child);
        }
        else if (child.classList.contains("__start_label")) {
          start = child;
        }
        child = next;
      }

      // We want to insert it after the start label.
      div = el.ownerDocument.createElement("div");
      div.className = "_phantom _decoration_text _explanation_number " +
        "_start_wrapper'";
      div.textContent = label + ". ";
      this._gui_updater.insertBefore(el, div,
                                     start ? start.nextSibling : el.firstChild);
    }

    this._heading_decorator.sectionHeadingDecorator(el);
  };

  DispatchMixinP.citDecorator = function citDecorator(root, el) {
    this.elementDecorator(root, el);

    var ref;
    var child = el.firstElementChild;
    while (child) {
      var next = child.nextElementSibling;
      if (child.classList.contains("_ref_space") ||
          child.classList.contains("_cit_bullet")) {
        this._gui_updater.removeNode(child);
      }
      else if (child.classList.contains("ref")) {
        ref = child;
      }
      child = next;
    }

    if (ref) {
      var space = el.ownerDocument.createElement("div");
      space.className = "_text _phantom _ref_space";
      space.innerHTML = " ";
      el.insertBefore(space, ref.nextSibling);
    }

    if (el.querySelector("*[" + util.encodeAttrName("xml:lang") +
                         "='pi-Latn']")) {
      var div = el.ownerDocument.createElement("div");
      div.className = "_phantom _text _cit_bullet";
      div.style.position = "absolute";
      div.style.left = "-1em";
      div.textContent = WHEEL;
      this._gui_updater.insertNodeAt(el, 0, div);
      el.style.position = "relative";
    }
  };

  DispatchMixinP.ptrDecorator = function ptrDecorator(root, el) {
    this.linkingDecorator(root, el, true);
  };

  DispatchMixinP.refDecorator = function refDecorator(root, el) {
    this.linkingDecorator(root, el, false);
  };

  function setTitle($el, data) {
    var creators = data.creators;
    var firstCreator = "***ITEM HAS NO CREATORS***";
    if (creators) {
      firstCreator = creators.split(",")[0];
    }

    var title = firstCreator + ", " + data.title;
    var date = data.date;
    if (date) {
      title += ", " + date;
    }

    tooltip($el, { title: title, container: "body", trigger: "hover" });
  }

  DispatchMixinP.linkingDecorator = function linkingDecorator(root, el, isPtr) {
    var origTarget = el.getAttribute(util.encodeAttrName("target"));
    // XXX This should become an error one day. The only reason we
    // need this now is that some of the early test files had <ref>
    // elements without targets.
    if (!origTarget) {
      origTarget = "";
    }

    origTarget = origTarget.trim();

    var doc = root.ownerDocument;
    var targetId;
    var child;
    var next; // Damn hoisting.
    if (origTarget.lastIndexOf("#", 0) === 0) {
      // Internal target
      // Add BTW in front because we want the target used by wed.
      targetId = origTarget.replace(/#(.*)$/, "#BTW-$1");

      var text = doc.createElement("div");
      text.className = "_text _phantom _linking_deco";
      var a = doc.createElement("a");
      a.className = "_phantom";
      a.setAttribute("href", targetId);
      text.appendChild(a);
      if (isPtr) {
        // _linking_deco is used locally to make this function idempotent

        child = el.firstElementChild;
        while (child) {
          next = child.nextElementSibling;
          if (child.classList.contains("_linking_deco")) {
            this._gui_updater.removeNode(child);
            break; // There is only one.
          }
          child = next;
        }

        var refman = this._refmans.getRefmanForElement(el);

        // Find the referred element. Slice to drop the #.
        var target = doc.getElementById(targetId.slice(1));

        // An undefined or null refman can happen when first
        // decorating the document.
        var label;
        if (refman) {
          if (refman.name === "sense" || refman.name === "subsense") {
            label = refman.idToLabel(targetId.slice(1));
            label = label && "[" + label + "]";
          }
          else {
            // An empty target can happen when first
            // decorating the document.
            if (target) {
              var dataEl = this._editor.toDataNode(el);
              var dataTarget = this._editor.toDataNode(target);
              label = refman.getPositionalLabel(dataEl,
                                                dataTarget,
                                                targetId.slice(1));
            }
          }
        }

        if (label === undefined) {
          label = targetId;
        }

        a.textContent = label;

        // A ptr contains only attributes, no text, so we can just append.
        var pair = this._mode.nodesAroundEditableContents(el);
        this._gui_updater.insertBefore(el, text, pair[1]);

        if (target) {
          var targetName = util.getOriginalName(target);

          // Reduce the target to something sensible for tooltip text.
          if (targetName === "btw:sense") {
            var terms = target.querySelectorAll(domutil.toGUISelector(
              this._sense_tooltip_selector));
            var html = "";
            for (var i = 0; i < terms.length; ++i) {
              var term = terms[i];
              html += term.innerHTML;
              if (i < terms.length - 1) {
                html += ", ";
              }
            }
            target = target.ownerDocument.createElement("div");
            target.innerHTML = html;
          }
          else if (targetName === "btw:subsense") {
            child = target.firstElementChild;
            while (child) {
              if (child.classList.contains("btw:explanation")) {
                target = child.cloneNode(true);
                break;
              }
              child = child.nextElementSibling;
            }
          }
          else if (targetName === "btw:example") {
            target = undefined;
          }

          if (target) {
            var nodes = target.querySelectorAll(
              ".head, ._gui, ._explanation_number");
            for (var nodeIx = 0; nodeIx < nodes.length; ++nodeIx) {
              var node = nodes[nodeIx];
              node.parentNode.removeChild(node);
            }
            tooltip($(text), { title: "<div>" + target.innerHTML + "</div>",
                               html: true,
                               container: "body",
                               trigger: "hover" });
          }
        }
      }
      else {
        throw new Error("internal error: ref with unexpected target");
      }
    }
    else {
      // External target
      var biblPrefix = "/bibliography/";
      if (origTarget.lastIndexOf(biblPrefix, 0) === 0) {
        // Bibliographical reference...
        if (isPtr) {
          throw new Error("internal error: bibliographic " +
                          "reference recorded as ptr");
        }

        targetId = origTarget;

        // It is okay to skip the tree updater for these operations.
        child = el.firstElementChild;
        while (child) {
          next = child.nextElementSibling;
          if (child.classList.contains("_ref_abbr") ||
              child.classList.contains("_ref_paren")) {
            this._gui_updater.removeNode(child);
          }
          child = next;
        }

        var abbr = doc.createElement("div");
        abbr.className = "_text _phantom _ref_abbr";
        this._gui_updater.insertBefore(el, abbr, el.firstChild);
        var open = doc.createElement("div");
        open.className = "_phantom _decoration_text _ref_paren " +
          "_open_ref_paren _start_wrapper";
        open.innerHTML = "(";
        this._gui_updater.insertBefore(el, open, abbr);

        var close = doc.createElement("div");
        close.className = "_phantom _decoration_text " +
          "_ref_paren _close_ref_paren _end_wrapper";
        close.innerHTML = ")";
        this._gui_updater.insertBefore(el, close);

        this.fetchAndFillBiblData(targetId, el, abbr);
      }
    }
  };

  DispatchMixinP.fetchAndFillBiblData = function fetchAndFillBiblData(
    targetId, el, abbr) {
    var dec = this;
    var $el = $(el);
    this._mode._getBibliographicalInfo().then(function then(info) {
      var data = info[targetId];
      if (data) {
        dec.fillBiblData(el, abbr, data);
      }
      else {
        dec._gui_updater.insertText(abbr, 0, "NON-EXISTENT");
      }

      $el.trigger("wed-refresh");
    });
  };

  DispatchMixinP.fillBiblData = function fillBiblData(el, abbr, data) {
    var $el = $(el);
    setTitle($el, data.item ? data.item : data);
    this._gui_updater.insertText(abbr, 0,
                                 btwUtil.biblDataToReferenceText(data));
  };

  DispatchMixinP.sfDecorator = function sfDecorator(root, el) {
    //
    // When editing them, btw:sf contains the semantic field paths, and there
    // are no names.
    //
    // When displaying articles, the paths are in @data-wed-ref, and the btw:sf
    // elements contain the names + path of the semantic fields.
    //

    // We're already wrapped.
    if (domutil.closestByClass(el, "field-view", root)) {
      return;
    }

    var inMode = this._inMode;
    var parent = el.parentNode;
    var before = el.previousSibling;

    var ref;
    if (!inMode) {
      var dataWedRef = el.attributes["data-wed-ref"];
      if (dataWedRef) {
        ref = el.attributes["data-wed-ref"].value;
      }

      // We do not decorate if we have no references.
      if (ref === undefined) {
        return;
      }
    }
    else {
      var dataNode = this._editor.toDataNode(el);
      ref = dataNode.textContent;
    }

    var view = new FieldView({
      // We start the view with a fake field. This will be fixed later.
      model: new Field({
        heading: "",
        path: ref,
      }),

      fetcher: this._sfFetcher,
    });
    view.render();
    view.ui.field[0].innerHTML = "";
    view.ui.field[0].appendChild(el);
    this._gui_updater.insertBefore(
      parent, view.el,
      before ? before.nextSibling : parent.firstChild);

    if (inMode) {
      // When we are editing we want to fill the semantic field with
      // its name and path.
      this._sfFetcher.fetch([ref]).then(function then(resolved) {
        var resolvedRef = resolved[ref];
        if (resolvedRef) {
          el.textContent = resolvedRef.heading + " (" + ref + ")";
        }
        else {
          el.textContent = "Unknown field (" + ref + ")";
        }
      });
    }
  };


  exports.DispatchMixin = DispatchMixin;
});
