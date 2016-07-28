/**
 * @module wed/modes/btw/btw_decorator
 * @desc Toolbar for BTWMode.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_decorator */ function btwDecorator(
  require, exports, _module) {
  "use strict";

  var Decorator = require("wed/decorator").Decorator;
  var refmans = require("./btw_refmans");
  var oop = require("wed/oop");
  var $ = require("jquery");
  var util = require("wed/util");
  var log = require("wed/log");
  var inputTriggerFactory = require("wed/input_trigger_factory");
  var keyConstants = require("wed/key_constants");
  var domutil = require("wed/domutil");
  var transformation = require("wed/transformation");
  var updaterDOMListener = require("wed/updater_domlistener");
  var btwUtil = require("./btw_util");
  var idManager = require("./id_manager");
  var contextMenu = require("wed/gui/context_menu");
  var tooltip = require("wed/gui/tooltip").tooltip;
  var validate = require("salve/validate");
  var makeDLoc = require("wed/dloc").makeDLoc;
  var DispatchMixin = require("./btw_dispatch").DispatchMixin;
  var HeadingDecorator = require("./btw_heading_decorator").HeadingDecorator;
  require("wed/jquery.findandself");
  var closestByClass = domutil.closestByClass;
  var closest = domutil.closest;
  var SFFetcher = require("./semantic_field_fetcher");

  var _indexOf = Array.prototype.indexOf;

  function BTWDecorator(semanticFieldFetchUrl, mode, meta) {
    Decorator.apply(this, Array.prototype.slice.call(arguments, 3));
    DispatchMixin.call(this);

    this._gui_root = this._editor.gui_root;
    this._gui_domlistener =
      new updaterDOMListener.Listener(this._gui_root, this._gui_updater);
    this._mode = mode;
    this._meta = meta;
    this._sense_subsense_id_manager = new idManager.IDManager("S.");
    this._example_id_manager = new idManager.IDManager("E.");
    this._refmans = new refmans.WholeDocumentManager();
    this._heading_decorator = new HeadingDecorator(
      this._refmans, this._gui_updater);
    this._sense_tooltip_selector = "btw:english-rendition>btw:english-term";
    this._sfFetcher = new SFFetcher(semanticFieldFetchUrl, undefined,
                                    ["changerecords"]);

    this._senses_for_refresh_subsenses = [];

    this._label_levels = {};
    [
      "btw:entry",
      "btw:lemma",
      "btw:overview",
      "btw:credits",
      "btw:definition",
      "btw:sense-discrimination",
      "btw:sense",
      "btw:subsense",
      "btw:english-renditions",
      "btw:english-rendition",
      "term",
      "btw:english-term",
      "btw:semantic-fields",
      "btw:sf",
      "btw:explanation",
      "btw:citations",
      "p",
      "ptr",
      "foreign",
      "btw:historico-semantical-data",
      "btw:etymology",
      "ref",
      "btw:sense-emphasis",
      "btw:lemma-instance",
      "btw:antonym-instance",
      "btw:cognate-instance",
      "btw:conceptual-proximate-instance",
      "btw:contrastive-section",
      "btw:antonyms",
      "btw:cognates",
      "btw:conceptual-proximates",
      "btw:other-citations",
      "btw:term",
      "btw:none",
    ].forEach(function each(x) {
      this._label_levels[x] = 2;
    }.bind(this));

    /**
     * @private
     * @typedef VisibleAbsenceSpec
     * @type {Object}
     * @property {String} parent A jQuery selector indicating the
     * parent(s) for which to create visible absences.
     * @property {Array.<String>} children An array
     * indicating the children for which to create visible absences.
     */

    // The following array is going to be transformed into the data
    // structure just described above.
    this._visible_absence_specs = [
      {
        parent: domutil.toGUISelector("btw:sense"),
        children: ["btw:subsense", "btw:explanation",
                   "btw:citations", "btw:other-citations",
                   "btw:contrastive-section"],
      },
      {
        parent: domutil.toGUISelector("btw:citations"),
        children: ["btw:example", "btw:example-explained"],
      },
      {
        parent: domutil.toGUISelector(
          "btw:subsense, btw:antonym, btw:cognate, btw:conceptual-proximate"),
        children: ["btw:other-citations"],
      },
      {
        parent: domutil.toGUISelector(
          "btw:example, btw:example-explained"),
        children: ["btw:semantic-fields"],
      },
      {
        parent: domutil.toGUISelector("btw:other-citations"),
        children: ["btw:cit", "btw:semantic-fields"],
      },
    ];
  }

  oop.inherit(BTWDecorator, Decorator);
  oop.implement(BTWDecorator, DispatchMixin);

  var BTWDecoratorP = BTWDecorator.prototype;

  BTWDecoratorP.addHandlers = function addHandlers() {
    this._domlistener.addHandler(
      "added-element",
      util.classFromOriginalName("btw:entry"),
      function added(root, parent, prev, next, el) {
        this.addedEntryHandler(root, el);
      }.bind(this));

    this._domlistener.addHandler(
      "included-element",
      util.classFromOriginalName("btw:sense"),
      function included(root, tree, parent, prev, next, el) {
        this.includedSenseHandler(root, el);
      }.bind(this));

    this._gui_domlistener.addHandler(
      "excluding-element",
      util.classFromOriginalName("btw:sense"),
      function excluded(root, tree, parent, prev, next, el) {
        this.excludingSenseHandler(el);
      }.bind(this));

    this._domlistener.addHandler(
      "included-element",
      util.classFromOriginalName("btw:subsense"),
      function included(root, tree, parent, prev, next, el) {
        this.includedSubsenseHandler(root, el);
      }.bind(this));

    this._gui_domlistener.addHandler(
      "excluding-element",
      util.classFromOriginalName("btw:subsense"),
      function excluding(root, tree, parent, prev, next, el) {
        this.excludingSubsenseHandler(root, el);
      }.bind(this));

    this._gui_domlistener.addHandler(
      "excluded-element",
      util.classFromOriginalName("btw:example, btw:example-explained"),
      function excluded(root, tree, parent, prev, next, el) {
        this.excludedExampleHandler(root, el);
      }.bind(this));

    this._gui_domlistener.addHandler(
      "children-changing",
      domutil.toGUISelector("ref, ref *"),
      function changing(root, added, removed, prev, next, el) {
        this._refChangedInGUI(root, closestByClass(el, "ref", root));
      }.bind(this));

    this._gui_domlistener.addHandler(
      "text-changed",
      domutil.toGUISelector("ref, ref *"),
      function changed(root, el) {
        this._refChangedInGUI(root, closestByClass(el, "ref", root));
      }.bind(this));

    this._domlistener.addHandler(
      "included-element",
      util.classFromOriginalName("*"),
      function included(root, tree, parent, prev, next, el) {
        this.refreshElement(root, el);
      }.bind(this));

    // This is needed to handle cases when an btw:cit acquires or
    // loses Pāli text.
    this._domlistener.addHandler(
      "excluding-element",
      domutil.toGUISelector("btw:cit foreign"),
      function excluding(root, tree, parent, prev, next, el) {
        var cit = closestByClass(el, "btw:cit", root);
        // Refresh after the element is removed.
        var dec = this;
        setTimeout(function refresh() {
          dec.refreshElement(root, cit);
          dec.refreshElement(root, domutil.siblingByClass(
            cit, "btw:explanation"));
        }, 0);
      }.bind(this));

    this._domlistener.addHandler(
      "included-element",
      domutil.toGUISelector("btw:cit foreign"),
      function included(root, tree, parent, prev, next, el) {
        var cit = closestByClass(el, "btw:cit", root);
        this.refreshElement(root, cit);
        this.refreshElement(root, domutil.siblingByClass(
          cit, "btw:explanation"));
      }.bind(this));


    this._domlistener.addHandler(
      "children-changed",
      util.classFromOriginalName("*"),
      function changed(root, added, removed, prev, next, el) {
        var removedFlag = false;
        var i;
        var r;
        for (i = 0; !removedFlag && i < removed.length; ++i) {
          r = removed[i];
          removedFlag = r.nodeType === Node.TEXT_NODE ||
            r.classList.contains("_real") ||
            r.classList.contains("_phantom_wrap");
        }

        if (!removedFlag) {
          var addedFlag = false;
          for (i = 0; !addedFlag && i < added.length; ++i) {
            r = added[i];
            addedFlag = r.nodeType === Node.TEXT_NODE ||
              r.classList.contains("_real") ||
              r.classList.contains("_phantom_wrap");
          }

          if (addedFlag) {
            this.refreshElement(root, el);
          }
        }
        else {
          // Refresh the element **after** the data is removed.
          setTimeout(function refresh() {
            this.refreshElement(root, el);
          }.bind(this), 0);
        }
      }.bind(this));

    this._domlistener.addHandler(
      "trigger",
      "included-sense",
      this.includedSenseTriggerHandler.bind(this));

    this._domlistener.addHandler(
      "trigger",
      "refresh-subsenses",
      this.refreshSubsensesTriggerHandler.bind(this));

    this._domlistener.addHandler(
      "trigger",
      "refresh-sense-ptrs",
      this.refreshSensePtrsHandler.bind(this));

    // Handlers for our gui_domlistener

    this._gui_domlistener.addHandler(
      "included-element",
      ".head",
      function included() {
        this._gui_domlistener.trigger("refresh-navigation-trigger");
      }.bind(this));

    this._gui_domlistener.addHandler(
      "excluded-element",
      ".head",
      function excluded() {
        this._gui_domlistener.trigger("refresh-navigation-trigger");
      }.bind(this));

    this._gui_domlistener.addHandler("trigger",
                                     "refresh-navigation-trigger",
                                     this._refreshNavigationHandler.bind(this));
    this._gui_domlistener.startListening();

    Decorator.prototype.addHandlers.apply(this, arguments);
    inputTriggerFactory.makeSplitMergeInputTrigger(
      this._editor,
      "p",
      keyConstants.ENTER,
      keyConstants.BACKSPACE,
      keyConstants.DELETE);
  };

  BTWDecoratorP.addedEntryHandler = function addedEntryHandler(root, el) {
    //
    // Perform general checks before we start decorating anything.
    //
    var i;
    var limit;
    var id;

    var dataEl = $.data(el, "wed_mirror_node");
    var sensesSubsenses = domutil.dataFindAll(dataEl,
                                              "btw:sense, btw:subsense");
    for (i = 0, limit = sensesSubsenses.length; i < limit; ++i) {
      var s = sensesSubsenses[i];
      id = s.getAttribute("xml:id");
      if (id) {
        this._sense_subsense_id_manager.seen(id, true);
      }
    }

    var examples = domutil.dataFindAll(dataEl,
                                       "btw:example, btw:example-explained");
    for (i = 0, limit = examples.length; i < limit; ++i) {
      var ex = examples[i];
      id = ex.getAttribute("xml:id");
      if (id) {
        this._example_id_manager.seen(id, true);
      }
    }
  };

  BTWDecoratorP.refreshElement = function refreshElement(root, el) {
    // Skip elements which would already have been removed from
    // the tree. Unlikely but...
    if (!root.contains(el)) {
      return;
    }

    this.refreshVisibleAbsences(root, el);

    this.dispatch(root, el);

    //
    // This mode makes the validator work while it is decorating the
    // GUI tree. Therefore, the position of errors *can* be erroneous
    // when these errors are generated while the GUI tree is being
    // decorated. So we need to restart the validation to fix the
    // erroneous error markers.
    //
    // We want to do it only if there *are* validation errors in this
    // element.
    //
    var error = false;
    var child = el.firstElementChild;
    while (child) {
      error = child.classList.contains("wed-validation-error");
      if (error) {
        break;
      }

      child = child.nextElementSibling;
    }

    if (error) {
      this._editor.validator.restartAt($.data(el, "wed-mirror-node"));
    }
  };

  BTWDecoratorP.elementDecorator = function elementDecorator(root, el) {
    var origName = util.getOriginalName(el);
    Decorator.prototype.elementDecorator.call(
      this, root, el, this._label_levels[origName] || 1,
      log.wrap(this._contextMenuHandler.bind(this, true)),
      log.wrap(this._contextMenuHandler.bind(this, false)));
  };

  BTWDecoratorP.noneDecorator = function noneDecorator(root, el) {
    this._gui_updater.removeNodes(el.childNodes);
    var text = el.ownerDocument.createElement("div");
    text.className = "_text _phantom";
    text.innerHTML = "ø";
    this._gui_updater.insertBefore(el, text, null);
  };

  function menuClickHandler(editor, guiLoc, items, ev) {
    if (editor.getGUICaret() === undefined) {
      editor.setGUICaret(guiLoc);
    }
    // eslint-disable-next-line no-new
    new contextMenu.ContextMenu(editor.my_window.document,
                                ev.clientX, ev.clientY, items);
    return false;
  }

  function singleClickHandler(dataLoc, tr, root, el, ev) {
    if (this._editor.getDataCaret() === undefined) {
      this._editor.setDataCaret(dataLoc);
    }
    tr.bound_terminal_handler(ev);
    this.refreshElement(root, el);
  }

  BTWDecoratorP.refreshVisibleAbsences = function refreshVisibleAbsences(root,
                                                                         el) {
    var found;
    var spec;
    for (var i = 0, limit = this._visible_absence_specs.length; i < limit; ++i) {
      spec = this._visible_absence_specs[i];
      if (el.matches(spec.parent)) {
        found = spec;
        break;
      }
    }

    var child = el.firstElementChild;
    while (child) {
      var next = child.nextElementSibling;
      if (child.classList.contains("_va_instantiator")) {
        this._gui_updater.removeNode(child);
      }
      child = next;
    }

    if (found) {
      var node = this._editor.toDataNode(el);
      var origErrors = this._editor.validator.getErrorsFor(node);

      // Create a hash table that we can use for later tests.
      var origStrings = Object.create(null);
      for (var oeIx = 0, oeLimit = origErrors.length; oeIx < oeLimit; ++oeIx) {
        origStrings[origErrors[oeIx].error.toString()] = true;
      }

      var children = found.children;
      for (var specIx = 0, specLimit = children.length; specIx < specLimit;
           ++specIx) {
        spec = children[specIx];

        var ename = this._mode._resolver.resolveName(spec);
        var locations = this._editor.validator.possibleWhere(
          node, new validate.Event("enterStartTag", ename.ns,
                                   ename.name));

        // Narrow it down to locations where adding the element
        // won't cause a subsequent problem.
        var filteredLocations = [];
        var lix;
        var l;
        // eslint-disable-next-line no-labels, no-restricted-syntax
        locationLoop:
        for (lix = 0; lix < locations.length; ++lix) {
          l = locations[lix];
          // We clone only the node itself and its first level
          // children.
          var clone = node.cloneNode(false);
          var div = clone.ownerDocument.createElement("div");
          div.appendChild(clone);

          child = node.firstChild;
          while (child) {
            clone.appendChild(child.cloneNode(false));
            child = child.nextSibling;
          }

          clone.insertBefore(
            transformation.makeElement(clone.ownerDocument,
                                       ename.ns, spec),
            clone.childNodes[l] || null);

          var errors =
                this._editor.validator.speculativelyValidateFragment(
                  node.parentNode,
                  _indexOf.call(node.parentNode.childNodes, node), div);

          // What we are doing here is reducing the errors only
          // to those that indicate that the added element would
          // be problematic.
          for (var eix = 0; eix < errors.length; ++eix) {
            var err = errors[eix];
            var errMsg = err.error.toString();
            if (err.node === clone &&
                // We want only errors that were not
                // originally present.
                !origStrings[errMsg] &&
                // And that are about a tag not being allowed.
                errMsg.lastIndexOf("tag not allowed here: ", 0) ===
                0) {
              // There's nothing to be done with this location.
              // eslint-disable-next-line no-labels
              continue locationLoop;
            }
          }

          filteredLocations.push(l);
        }
        locations = filteredLocations;

        // No suitable location.
        if (!locations.length) {
          continue;
        }

        for (lix = 0; lix < locations.length; ++lix) {
          l = locations[lix];
          var dataLoc = makeDLoc(this._editor.data_root, node, l);
          var data = { name: spec, move_caret_to: dataLoc };
          var guiLoc = this._gui_updater.fromDataLocation(dataLoc);

          var tuples = [];
          var actions = this._mode.getContextualActions("insert", spec, node,
                                                        l);
          for (var actIx = 0; actIx < actions.length; ++actIx) {
            var act = actions[actIx];
            tuples.push([act, data, act.getLabelFor(data)]);
          }

          var control = el.ownerDocument.createElement("button");
          control.className = "_gui _phantom _va_instantiator btn " +
            "btn-instantiator btn-xs";
          control.setAttribute("href", "#");
          var $control = $(control);
          if (this._editor.preferences.get("tooltips")) {
            // Get tooltips from the current mode
            tooltip($control, {
              title: this._editor.mode.shortDescriptionFor(spec),
              container: $control,
              delay: { show: 1000 },
              placement: "auto top",
              trigger: "hover",
            });
          }

          if (tuples.length > 1) {
            control.innerHTML = " + " + spec;

            // Convert the tuples to actual menu items.
            var items = [];
            for (var tix = 0; tix < tuples.length; ++tix) {
              var tup = tuples[tix];
              var li = el.ownerDocument.createElement("li");
              li.innerHTML = "<a tabindex='0' href='#'>" + tup[2] +
                "</a>";
              var $a = $(li.firstChild);
              $a.click(tup[1], tup[0].bound_handler);
              $a.mousedown(false);
              items.push(li);
            }

            $control.click(menuClickHandler.bind(undefined, this._editor,
                                                 guiLoc, items));
          }
          else if (tuples.length === 1) {
            control.innerHTML = tuples[0][2];
            $control.mousedown(false);
            $control.click(tuples[0][1],
                           singleClickHandler.bind(this, dataLoc, tuples[0][0],
                                                   root, el));
          }
          this._gui_updater.insertNodeAt(guiLoc, control);
        }
      }
    }
  };

  BTWDecoratorP.idDecorator = function idDecorator(root, el) {
    DispatchMixin.prototype.idDecorator.call(this, root, el);
    this._domlistener.trigger("refresh-sense-ptrs");
  };

  BTWDecoratorP.refreshSensePtrsHandler = function refreshSensePtrsHandler(
    root) {
    var ptrs = root.getElementsByClassName("ptr");
    for (var i = 0; i < ptrs.length; ++i) {
      this.linkingDecorator(root, ptrs[i], true);
    }
  };

  /**
   * This function works exactly like the one in {@link
   * module:btw_dispatch~DispatchMixin DispatchMixin} except that it
   * takes the additional ``final_`` parameter.
   *
   * @param {boolean} final_ Whether there will be any more changes to
   * this ptr or not.
   */
  BTWDecoratorP.linkingDecorator = function linkingDecorator(root, el,
                                                             isPtr, final_) {
    DispatchMixin.prototype.linkingDecorator.call(this, root, el, isPtr);

    // What we are doing here is taking care of updating links to
    // examples when the reference to the bibliographical source they
    // contain is updated. These updates happen asynchronously.
    if (isPtr && !final_) {
      var doc = el.ownerDocument;
      var origTarget = el.getAttribute(util.encodeAttrName("target"));
      if (!origTarget) {
        origTarget = "";
      }

      origTarget = origTarget.trim();

      if (origTarget.lastIndexOf("#", 0) !== 0) {
        return;
      }

      // Internal target
      // Add BTW in front because we want the target used by wed.
      var targetId = origTarget.replace(/#(.*)$/, "#BTW-$1");

      // Find the referred element. Slice to drop the #.
      var target = doc.getElementById(targetId.slice(1));

      if (!target) {
        return;
      }

      if (!(target.classList.contains("btw:example") ||
            target.classList.contains("btw:example-explained"))) {
        return;
      }

      // Get the ref element that olds the reference to the
      // bibliographical item, and set an event handler to make sure
      // we update *this* ptr, when the ref changes.
      var ref = target.querySelector(domutil.toGUISelector("btw:cit>ref"));

      $(ref).on("wed-refresh", function refresh() {
        this.linkingDecorator(root, el, isPtr);
      }.bind(this));
    }
  };

  BTWDecoratorP.includedSenseHandler = function includedSenseHandler(root, el) {
    this.idDecorator(root, el);
    this._domlistener.trigger("included-sense");
  };

  BTWDecoratorP.excludingSenseHandler = function excludingSenseHandler(el) {
    this._deleteLinksPointingTo(el);
    // Yep, we trigger the included-sense trigger.
    this._domlistener.trigger("included-sense");
  };

  BTWDecoratorP.includedSubsenseHandler = function includedSubsenseHandler(
    root, el) {
    this.idDecorator(root, el);
    this.refreshSubsensesForSense(root, el.parentNode);
  };

  BTWDecoratorP.excludingSubsenseHandler = function excludingSubsenseHandler(
    root, el) {
    this._deleteLinksPointingTo(el);
    this.refreshSubsensesForSense(root, el.parentNode);
  };

  BTWDecoratorP._deleteLinksPointingTo = function _deleteLinksPointingTo(el) {
    var id = el.getAttribute(util.encodeAttrName("xml:id"));

    // Whereas using querySelectorAll does not **generally** work,
    // using this selector, which selects only on attribute values,
    // works.
    var selector = "*[target='#" + id + "']";

    var links = this._editor.data_root.querySelectorAll(selector);
    for (var i = 0; i < links.length; ++i) {
      this._editor.data_updater.removeNode(links[i]);
    }
  };

  BTWDecoratorP.excludedExampleHandler = function excludedExampleHandler(
    root, el) {
    this._deleteLinksPointingTo(el);
  };

  BTWDecoratorP.includedSenseTriggerHandler =
    function includedSenseTriggerHandler(root) {
      var senses = root.getElementsByClassName("btw:sense");
      if (senses.length) {
        this._refmans.getRefmanForElement(senses[0]).deallocateAll();
      }
      for (var i = 0; i < senses.length; ++i) {
        var sense = senses[i];
        this.idDecorator(root, sense);
        this._heading_decorator.sectionHeadingDecorator(sense);
        this._heading_decorator.updateHeadingsForSense(sense);
        this.refreshSubsensesForSense(root, sense);
      }
    };

  BTWDecoratorP.refreshSubsensesForSense = function refreshSubsensesForSense(
    root, sense) {
    // The indexOf search ensures we don't put duplicates in the list.
    if (this._senses_for_refresh_subsenses.indexOf(sense) === -1) {
      this._senses_for_refresh_subsenses.push(sense);
      this._domlistener.trigger("refresh-subsenses");
    }
  };

  BTWDecoratorP.refreshSubsensesTriggerHandler =
    function refreshSubsensesTriggerHandler(root) {
      // Grab the list before we try to do anything.
      var senses = this._senses_for_refresh_subsenses;
      this._senses_for_refresh_subsenses = [];
      senses.forEach(function each(sense) {
        this._refreshSubsensesForSense(root, sense);
      }.bind(this));
    };

  BTWDecoratorP._refreshSubsensesForSense = function _refreshSubsensesForSense(
    root, sense) {
    var refman = this._refmans.getSubsenseRefman(sense);
    refman.deallocateAll();

    // This happens if the sense was removed from the document.
    if (!this._editor.gui_root.contains(sense)) {
      return;
    }

    var subsenses = sense.getElementsByClassName("btw:subsense");
    for (var i = 0; i < subsenses.length; ++i) {
      var subsense = subsenses[i];
      this.idDecorator(root, subsense);
      var explanation = domutil.childByClass("btw:explanantion");
      if (explanation) {
        this.explanationDecorator(root, explanation);
      }

      this._heading_decorator.updateHeadingsForSubsense(subsense);
    }
  };

  BTWDecoratorP._refChangedInGUI = function _refChangedInGUI(root, el) {
    var example = closest(el, domutil.toGUISelector(
      "btw:example, btw:example-explained"));

    if (!example) {
      return;
    }

    var id = example.getAttribute(util.encodeAttrName("xml:id"));
    if (!id) {
      return;
    }

    // Find the referred element.
    var ptrs = root.querySelectorAll(util.classFromOriginalName("ptr") + "[" +
                                     util.encodeAttrName("target") + "='#" +
                                     id + "']");

    for (var i = 0, limit = ptrs.length; i < limit; ++i) {
      this.refreshElement(root, ptrs[i]);
    }
  };


  BTWDecoratorP.languageDecorator = function languageDecorator(el) {
    var lang = el.getAttribute(util.encodeAttrName("xml:lang"));
    var prefix = lang.slice(0, 2);
    if (prefix !== "en") {
      el.classList.add("_btw_foreign");
      // $el.css("background-color", "#DFCFAF");
      // // Chinese is not commonly italicized.
      if (prefix !== "zh") {
        // $el.css("font-style", "italic");
        el.classList.add("_btw_foreign_italics");
      }

      var label = btwUtil.languageCodeToLabel(lang);
      if (label === undefined) {
        throw new Error("unknown language: " + lang);
      }
      label = label.split("; ")[0];
      tooltip($(el), { title: label, container: "body", trigger: "hover" });
    }
  };


  BTWDecoratorP._refreshNavigationHandler = function _refreshNavigationHandler(
  ) {
    var doc = this._gui_root.ownerDocument;
    var prevAtDepth = [doc.createElement("li")];

    function getParent(depth) {
      var parent = prevAtDepth[depth];
      if (!parent) {
        parent = doc.createElement("li");
        prevAtDepth[depth] = parent;
        var grandparent = getParent(depth - 1);
        grandparent.appendChild(parent);
      }
      return parent;
    }

    var heads = this._gui_root.getElementsByClassName("head");
    for (var i = 0; i < heads.length; ++i) {
      var el = heads[i];
      // This is the list of DOM parents that do have a head
      // child, i.e. which participate in navigation.
      var parents = [];
      var parent = el.parentNode;
      while (parent) {
        if (domutil.childByClass(parent, "head")) {
          parents.push(parent);
        }

        if (parent === this._gui_root) {
          break; // Don't go beyond this point.
        }

        parent = parent.parentNode;
      }

      // This will never be less than 1 because the current
      // element's parent satisfies the selectors above.
      var myDepth = parents.length;

      parent = el.parentNode;
      var origName = util.getOriginalName(parent);

      var li = doc.createElement("li");
      li.className = "btw-navbar-item";
      li.innerHTML = "<a class='navbar-link' href='#" + el.id +
        "'>" + el.textContent + "</a>";

      // getContextualActions needs to operate on the data tree.
      var dataParent = $.data(parent, "wed_mirror_node");

      // btw:explanation is the element that gets the heading that
      // marks the start of a sense. So we need to adjust.
      if (origName === "btw:explanation") {
        var parentSubsense = dataParent.parentNode;
        if (parentSubsense.tagName === "btw:subsense") {
          origName = "btw:subsense";
          dataParent = parentSubsense;
        }
      }

      // Add contextmenu handlers depending on the type of parent
      // we are dealing with.
      var a = li.firstChild;
      li.setAttribute("data-wed-for", origName);

      var $el = $(el);
      if (origName === "btw:sense" ||
          origName === "btw:english-rendition" ||
          origName === "btw:subsense") {
        $(a).on("contextmenu", { node: dataParent },
                this._navigationContextMenuHandler.bind(this));
        a.innerHTML += " <i class='fa fa-cog'></i>";
        var oldIcon = domutil.childByClass(el, "fa");
        if (oldIcon) {
          oldIcon.parentNode.removeChild(oldIcon);
        }
        el.innerHTML += " <i class='fa fa-cog'></i>";
        // We must remove all previous handlers.
        $el.off("wed-context-menu");
        $el.on("wed-context-menu", { node: dataParent },
               this._navigationContextMenuHandler.bind(this));
      }
      else {
        // We turn off context menus on the link and on the header.
        $(a).on("contextmenu", false);
        $el.on("wed-context-menu", false);
      }
      el.setAttribute("data-wed-custom-context-menu", true);

      getParent(myDepth - 1).appendChild(li);
      prevAtDepth[myDepth] = li;
    }

    this._editor.setNavigationList(
      Array.prototype.slice.call(prevAtDepth[0].children));
  };

  BTWDecoratorP._navigationContextMenuHandler = log.wrap(
    function _navigationContextMenuHandler(wedEv, ev) {
      // ev is undefined if called from the context menu. In this case,
      // wedEv contains all that we want.
      if (!ev) {
        ev = wedEv;
      }
      // node is the node in the data tree which corresponds to the
      // navigation item for which a context menu handler was required
      // by the user.
      var node = wedEv.data.node;
      var origName = node.tagName;

      // container, offset: location of the node in its parent.
      var container = node.parentNode;
      var offset = _indexOf.call(container.childNodes, node);

      // List of items to put in the contextual menu.
      var tuples = [];

      //
      // Create "insert" transformations for siblings that could be
      // inserted before this node.
      //
      var actions = this._mode.getContextualActions("insert", origName,
                                                    container, offset);
      // data to pass to transformations
      var data = { name: origName,
                   move_caret_to: makeDLoc(this._editor.data_root,
                                           container, offset) };
      var actIx;
      var act;
      for (actIx = 0; actIx < actions.length; ++actIx) {
        act = actions[actIx];
        tuples.push([act, data, act.getLabelFor(data) +
                     " before this one"]);
      }

      //
      // Create "insert" transformations for siblings that could be
      // inserted after this node.
      //
      actions = this._mode.getContextualActions("insert", origName,
                                                container, offset + 1);

      data = { name: origName, move_caret_to: makeDLoc(
        this._editor.data_root, container, offset + 1) };
      for (actIx = 0; actIx < actions.length; ++actIx) {
        act = actions[actIx];
        tuples.push([act, data,
                     act.getLabelFor(data) + " after this one"]);
      }

      var target = ev.target;
      var doc = ev.target.ownerDocument;
      var navList = closestByClass(target, "nav-list", document.body);
      if (navList) {
        // This context menu was invoked in the navigation list.

        var thisLi = closest(target, "li", navList);
        var siblingLinks = [];
        var parent = thisLi.parentNode;
        var child = parent.firstElementChild;
        while (child) {
          if (child.getAttribute("data-wed-for") === origName) {
            siblingLinks.push(child);
          }
          child = child.nextElementSibling;
        }

        // If the node has siblings we potentially add swap with previous
        // and swap with next.
        if (siblingLinks.length > 1) {
          data = { name: origName, node: node,
                   move_caret_to: makeDLoc(this._editor.data_root,
                                          container, offset) };
          // However, don't add swap with prev if we are first.
          if (!siblingLinks[0].contains(ev.currentTarget)) {
            tuples.push(
              [this._mode.swapWithPrevTr, data,
               this._mode.swapWithPrevTr.getLabelFor(data)]);
          }

          // Don't add swap with next if we are last.
          if (!siblingLinks[siblingLinks.length - 1]
              .contains(ev.currentTarget)) {
            tuples.push(
              [this._mode.swapWithNextTr, data,
               this._mode.swapWithNextTr.getLabelFor(data)]);
          }
        }
      }
      else {
        // Set the caret to be inside the head
        this._editor.setGUICaret(target, 0);
      }

      // Delete the node
      data = { node: node, name: origName,
               move_caret_to: makeDLoc(this._editor.data_root, node, 0) };
      actions = this._mode.getContextualActions("delete-element", origName,
                                                node, 0);
      for (actIx = 0; actIx < actions.length; ++actIx) {
        act = actions[actIx];
        tuples.push([act, data, act.getLabelFor(data)]);
      }

      var li;

      // Convert the tuples to actual menu items.
      var items = [];

      // Put the documentation link first.
      var docUrl = this._mode.documentationLinkFor(origName);
      if (docUrl) {
        li = doc.createElement("li");
        var a = this._editor.makeDocumentationLink(docUrl);
        li.appendChild(a);
        items.push(li);
      }

      for (var tix = 0; tix < tuples.length; ++tix) {
        var tup = tuples[tix];
        li = doc.createElement("li");
        li.innerHTML = "<a tabindex='0' href='#'>" + tup[2] + "</a>";
        var $a = $(li.firstChild);
        $a.mousedown(false);
        $a.click(tup[1], tup[0].bound_handler);
        items.push(li);
      }

      // eslint-disable-next-line no-new
      new contextMenu.ContextMenu(this._editor.my_window.document,
                                   ev.clientX, ev.clientY, items);

      return false;
    });


  exports.BTWDecorator = BTWDecorator;
});
