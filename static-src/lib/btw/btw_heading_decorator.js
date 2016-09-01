/**
 * @module wed/modes/btw/btw_heading_decorator
 * @desc Module for decorating headings
 * @author Louis-Dominique Dubeau
 */
define(function factory(require, exports, _module) {
  "use strict";

  var util = require("wed/util");
  var domutil = require("wed/domutil");
  var IDManager = require("./id_manager").IDManager;
  var btwUtil = require("./btw_util");

  function HeadingDecorator(refmans, guiUpdater, headingMap, impliedBrackets) {
    this._refmans = refmans;
    this._guiUpdater = guiUpdater;
    if (impliedBrackets === undefined) {
      impliedBrackets = true;
    }
    this._impliedBrackets = impliedBrackets;

    this._collapseHeadingIdManager = new IDManager("collapse-heading-");
    this._collapseIdManager = new IDManager("collapse-");

    // We bind them here so that we have a unique function to use.
    this._boundGetSenseLabel = this._refmans.getSenseLabel.bind(this._refmans);
    this._boundGetSubsenseLabel =
      this._refmans.getSubsenseLabel.bind(this._refmans);

    this._unitHeadingMap = headingMap || {
      "btw:overview": "UNIT 1: OVERVIEW",
      "btw:sense-discrimination": "UNIT 2: SENSE DISCRIMINATION",
      "btw:historico-semantical-data": "UNIT 3: HISTORICO-SEMANTICAL DATA",
      "btw:credits": "UNIT 4: CREDITS",
    };

    this._specs = [{
      selector: "btw:definition",
      heading: "definition",
    }, {
      selector: "btw:sense",
      heading: "SENSE",
      labelF: this._refmans.getSenseLabelForHead.bind(this._refmans),
    }, {
      selector: "btw:english-renditions",
      heading: "English renditions",
    }, {
      selector: "btw:english-rendition",
      heading: "English rendition",
    }, {
      selector: "btw:semantic-fields",
      heading: "semantic categories",
    }, {
      selector: "btw:etymology",
      heading: "etymology",
    }, {
      selector: "btw:sense>btw:explanation",
      heading: "brief explanation of sense",
      labelF: this._boundGetSenseLabel,
    }, {
      selector: "btw:subsense>btw:explanation",
      heading: "brief explanation of sense",
      labelF: this._boundGetSubsenseLabel,
    }, {
      selector: "btw:sense>btw:citations",
      heading: "citations for sense",
      labelF: this._boundGetSenseLabel,
    }, {
      selector: "btw:subsense>btw:citations",
      heading: "citations for sense",
      labelF: this._boundGetSubsenseLabel,
    }, {
      selector: "btw:antonym>btw:citations",
      heading: "citations",
    }, {
      selector: "btw:cognate>btw:citations",
      heading: "citations",
    }, {
      selector: "btw:conceptual-proximate>btw:citations",
      heading: "citations",
    }, {
      selector: "btw:contrastive-section",
      heading: "contrastive section for sense",
      labelF: this._boundGetSenseLabel,
    }, {
      selector: "btw:antonyms",
      heading: "antonyms",
    }, {
      selector: "btw:cognates",
      heading: "cognates",
    }, {
      selector: "btw:conceptual-proximates",
      heading: "conceptual proximates",
    }, {
      selector: "btw:sense>btw:other-citations",
      heading: "other citations for sense",
      labelF: this._boundGetSenseLabel,
    }, {
      selector: "btw:other-citations",
      heading: "other citations",
    }];

    // Convert the selectors to actual selectors.
    var specs = this._specs;
    for (var sIx = 0; sIx < specs.length; ++sIx) {
      var spec = specs[sIx];
      spec.data_selector = domutil.toGUISelector(spec.selector);
    }
  }

  var nextHead = 0;
  function allocateHeadID() {
    return "BTW-H-" + ++nextHead;
  }

  HeadingDecorator.prototype.addSpec = function addSpec(spec) {
    this._specs = this._specs.filter(function filter(x) {
      return x.selector !== spec.selector;
    });
    spec.data_selector = domutil.toGUISelector(spec.selector);
    this._specs.push(spec);
  };

  HeadingDecorator.prototype.unitHeadingDecorator =
    function unitHeadingDecorator(el) {
      var child = el.firstElementChild;
      while (child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("head")) {
          this._guiUpdater.removeNode(child);
          break; // There's only one.
        }
        child = next;
      }

      var name = util.getOriginalName(el);
      var headStr = this._unitHeadingMap[name];
      if (headStr === undefined) {
        throw new Error("found an element with name " + name +
                        ", which is not handled");
      }

      var head = el.ownerDocument.createElement("div");
      head.className = "head _phantom _start_wrapper";
      head.innerHTML = headStr;
      head.id = allocateHeadID();
      this._guiUpdater.insertNodeAt(el, 0, head);
    };

  HeadingDecorator.prototype.sectionHeadingDecorator =
    function sectionHeadingDecorator(el, specs, headStr) {
      var child = el.firstElementChild;
      var next;
      while (child) {
        next = child.nextElementSibling;
        if (child.classList.contains("head")) {
          this._guiUpdater.removeNode(child);
          break; // There's only one.
        }
        child = next;
      }

      var collapse = false;
      if (headStr === undefined) {
        var name = util.getOriginalName(el);
        var spec;
        for (var sIx = 0; sIx < this._specs.length; ++sIx) {
          spec = this._specs[sIx];
          if (el.matches(spec.data_selector)) {
            break;
          }
        }

        if (spec === undefined) {
          throw new Error("found an element with name " + name +
                          ", which is not handled");
        }

        if (spec.heading !== null) {
          var labelF = spec.labelF;
          headStr = (labelF) ? spec.heading + " " + labelF(el) : spec.heading;
        }

        if (spec.suffix) {
          headStr += spec.suffix;
        }

        collapse = spec.collapse;
      }

      if (headStr !== undefined) {
        if (!collapse) {
          var head = el.ownerDocument.createElement("div");
          head.className = "head _phantom _start_wrapper";
          head.textContent = this._impliedBrackets ?
            ("[" + headStr + "]") : headStr;
          head.id = allocateHeadID();
          this._guiUpdater.insertNodeAt(el, 0, head);
        }
        else {
          // If collapse is a string, it is shorthand for a collapse
          // object with the field `kind` set to the value of the
          // string.
          if (typeof collapse === "string") {
            collapse = {
              kind: collapse,
            };
          }
          var collapsible = btwUtil.makeCollapsible(
            el.ownerDocument,
            collapse.kind,
            this._collapseHeadingIdManager.generate(),
            this._collapseIdManager.generate(),
            { panel: collapse.additional_classes });
          var group = collapsible.group;
          var panelBody = collapsible.content;
          collapsible.heading.textContent = headStr;

          next = el.nextSibling;
          var parent = el.parentNode;
          this._guiUpdater.removeNode(el);
          panelBody.appendChild(el);
          this._guiUpdater.insertBefore(parent,
                                        group, next);
        }
      }
    };

  HeadingDecorator.prototype._updateHeadingsFor =
    function _updateHeadingsFor(el, func) {
      // Refresh the headings that use the sense label.
      for (var sIx = 0; sIx < this._specs.length; ++sIx) {
        var spec = this._specs[sIx];
        if (spec.labelF === func) {
          var subheaders = el.querySelectorAll(spec.data_selector);
          for (var shIx = 0; shIx < subheaders.length; ++shIx) {
            var sh = subheaders[shIx];
            this.sectionHeadingDecorator(sh);
          }
        }
      }
    };

  HeadingDecorator.prototype.updateHeadingsForSubsense =
    function updateHeadingsForSubsense(subsense) {
      // Refresh the headings that use the subsense label.
      this._updateHeadingsFor(subsense, this._boundGetSubsenseLabel);
    };

  HeadingDecorator.prototype.updateHeadingsForSense =
    function updateHeadingsForSense(sense) {
      // Refresh the headings that use the sense label.
      this._updateHeadingsFor(sense, this._boundGetSenseLabel);
    };

  exports.HeadingDecorator = HeadingDecorator;
});
