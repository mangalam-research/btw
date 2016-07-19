/**
 * @module wed/modes/btw/btw_mode
 * @desc Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_mode */ function btwMode(require,
                                                                    exports,
                                                                    _module) {
  "use strict";

  var $ = require("jquery");
  var util = require("wed/util");
  var log = require("wed/log");
  var Mode = require("wed/modes/generic/generic").Mode;
  var oop = require("wed/oop");
  var dloc = require("wed/dloc");
  var BTWDecorator = require("./btw_decorator").BTWDecorator;
  var transformation = require("wed/transformation");
  var Toolbar = require("./btw_toolbar").Toolbar;
  var btwMeta = require("./btw_meta");
  var domutil = require("wed/domutil");
  var btwTr = require("./btw_tr");
  var btwActions = require("./btw_actions");
  var Validator = require("./btw_validator").Validator;
  var Promise = require("bluebird").Promise;
  require("jquery.cookie");
  require("rangy");

  /**
   * @class
   * @extends module:wed/modes/generic/generic~Mode
   */
  function BTWMode(options) {
    options.meta = {
      path: btwMeta,
      options: {
        metadata: require.toUrl("./btw-storage-metadata.json"),
      },
    };
    this._bibl_url = options.bibl_url;
    delete options.bibl_url;
    // We can initiate this right away.
    this._getBibliographicalInfo();
    Mode.call(this, options);
    this._contextual_menu_items = [];
    this._headers = {
      "X-CSRFToken": $.cookie("csrftoken"),
    };

    this._wed_options.metadata = {
      name: "BTW Mode",
      authors: ["Louis-Dominique Dubeau"],
      description: "This is a mode for use with BTW.",
      license: "MPL 2.0",
      copyright: "2013 Mangalam Research Center for Buddhist Languages",
    };

    this._wed_options.label_levels.max = 2;
    this._wed_options.attributes = "hide";
  }

  oop.inherit(BTWMode, Mode);

  var BTWModeP = BTWMode.prototype;
  BTWModeP.init = function init(editor) {
    Mode.prototype.init.call(this, editor);

    this._hyperlinkModal = editor.makeModal();
    this._hyperlinkModal.setTitle("Insert hyperlink to sense");
    this._hyperlinkModal.addButton("Insert", true);
    this._hyperlinkModal.addButton("Cancel");

    editor.setNavigationList("");

    this.insertSensePtrAction = new btwActions.SensePtrDialogAction(
      editor, "Insert a new hyperlink to a sense",
      undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.insertExamplePtrAction = new btwActions.ExamplePtrDialogAction(
      editor, "Insert a new hyperlink to an example",
      undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.insertPtrTr = new transformation.Transformation(
      editor, "add", "Insert a pointer", btwTr.insertPtr);

    this.insertRefTr = new transformation.Transformation(
      editor, "add", "Insert a reference", btwTr.insertRef);

    this.replaceSelectionWithRefTr = new transformation.Transformation(
      editor, "wrap", "Replace the selection with a reference",
      btwTr.replaceSelectionWithRefTr);

    this.swapWithPrevTr = new transformation.Transformation(
      editor, "swap-with-previous", "Swap with previous sibling", undefined,
      "<i class='fa fa-long-arrow-up fa-fw'></i>",
      function transform(trEditor, data) {
        return transformation.swapWithPreviousHomogeneousSibling(
          trEditor, data.node);
      });

    this.swapWithNextTr = new transformation.Transformation(
      editor, "swap-with-next", "Swap with next sibling", undefined,
      "<i class='fa fa-long-arrow-down fa-fw'></i>",
      function transform(trEditor, data) {
        return transformation.swapWithNextHomogeneousSibling(
          trEditor, data.node);
      });

    this.replaceNoneWithAntonym = btwTr.makeReplaceNone(editor, "btw:antonym");

    this.replaceNoneWithCognate = btwTr.makeReplaceNone(editor, "btw:cognate");

    this.replaceNoneWithConceptualProximate =
      btwTr.makeReplaceNone(editor, "btw:conceptual-proximate");

    this.insertRefText = new transformation.Transformation(
      editor, "add", "Add custom text to reference",
      function transform(trEditor, _data) {
        var caret = trEditor.getGUICaret();
        var ref = $(caret.node).closest(util.classFromOriginalName("ref"))[0];
        var ph = trEditor.insertTransientPlaceholderAt(caret.make(
          ref, ref.childNodes.length));
        trEditor.decorator.refreshElement(dloc.findRoot(ref).node, ref);
        trEditor.setGUICaret(ph, 0);
      });

    this.insertBiblPtr = new btwActions.InsertBiblPtrAction(
      editor,
      "Insert a new bibliographical reference",
      "",
      "<i class='fa fa-book fa-fw'></i>",
      true);

    // Yes, we inherit from InsertBiblPtrAction even though we are
    // replacing.
    this.replaceBiblPtr = new btwActions.InsertBiblPtrAction(
      editor,
      "Replace the selection with a bibliographical reference",
      "",
      "<i class='fa fa-book fa-fw'></i>",
      true);

    this._toolbar = new Toolbar(this, editor);
    var toolbarTop = this._toolbar.getTopElement();
    editor.widget.insertBefore(toolbarTop, editor.widget.firstChild);
    $(editor.widget).on("wed-global-keydown.btw-mode",
                        this._keyHandler.bind(this));
    editor.excludeFromBlur(toolbarTop);

    /**
     * @private
     * @typedef Substitution
     * @type {Object}
     * @property {String} tag The tag name for which to perform the
     * substitution.
     * @property {String} type The type of transformations for which
     * to perform the substitution.
     * @property {Array.<module:action~Action>} actions The actions to
     * substitute for this tag.
     */

    /**
     * This is an object whose keys are the name of tags. The values
     * can be <code>true</code> if we pass all types of
     * transformations, or a list of transformation types.
     *
     * @private
     * @typedef Pass
     * @type {Object}
     *
     */

    /**
     * @private
     * @typedef TransformationFilter
     * @type {Object}
     * @property {String} selector A jQuery selector.
     * @property {Pass} pass
     * @property {Array.<String>} filter A list of element names.
     * @property {Array.<Substitution>} substitute A list of substitutions.
     * @property {Array.<module:wed/transformation~Transformation>} An
     * array of transformations to add.
     */

    var passInCit = {
      "btw:lemma-instance": true,
      "btw:antonym-instance": true,
      "btw:cognate-instance": true,
      "btw:conceptual-proximate-instance": true,
      p: true,
      lg: true,
      ref: ["insert", "wrap"],
    };

    var passInTr = $.extend({}, passInCit);
    delete passInTr.ref;

    var passInForeign = $.extend({}, passInTr);
    delete passInForeign.p;
    delete passInForeign.lg;
    passInForeign.foreign = ["delete-parent", "unwrap"];

    /**
     * @private
     * @property {Array.<TransformationFilter>} transformationFilters
     * A list of transformation filters to apply whenever the
     * getContextualActions method is called.
     */
    this.transformationFilters = [
      { selector: domutil.toGUISelector(
        ["btw:overview",
         "btw:definition"].join(",")),
        pass: {},
      },
      {
        selector: domutil.toGUISelector("btw:sense-discrimination"),
        pass: {
          "btw:sense": true,
        },
      },
      { // paragraph in a definition
        selector: domutil.toGUISelector("btw:definition>p"),
        pass: {
          "btw:sense-emphasis": true,
          ptr: true,
        },
        substitute: [{ tag: "ptr",
                       type: "insert",
                       actions: [this.insertSensePtrAction],
                      }],
      },
      { selector: util.classFromOriginalName("ptr"),
        pass: { ptr: ["delete-parent"] },
      },
      { selector: util.classFromOriginalName("ref"),
        pass: {
          ref: ["delete-parent", "insert"],
        },
        substitute: [
          { tag: "ref", type: "insert", actions: [this.insertRefText] },
        ],
      },
      { selector: util.classFromOriginalName("btw:citations"),
        substitute: [
          { tag: "ptr", type: "insert",
            actions: [this.insertExamplePtrAction] },
        ],
      },
      { selector: domutil.toGUISelector("btw:tr"),
        pass: passInTr,
      },
      { selector: domutil.toGUISelector("btw:cit"),
        pass: passInCit,
        substitute: [
          { tag: "ref",
            type: "insert",
            actions: [this.insertBiblPtr],
          },
          { tag: "ref",
            type: "wrap",
            actions: [this.replaceBiblPtr],
          },
        ],
      },
      { selector: domutil.toGUISelector(
        "btw:citations foreign, btw:other-citations foreign"),
        pass: passInForeign,
      },
      { selector: util.classFromOriginalName("foreign"),
        pass: {
          foreign: ["delete-parent", "unwrap"],
        },
      },
      { selector: domutil.toGUISelector("btw:antonyms>btw:none"),
        substitute: [
          { tag: "btw:none",
            type: "delete-parent",
            actions: [this.replaceNoneWithAntonym] },
        ],
      },
      { selector: domutil.toGUISelector("btw:cognates>btw:none"),
        substitute: [
          { tag: "btw:none",
            type: "delete-parent",
            actions: [this.replaceNoneWithCognate] },
        ],
      },
      { selector: domutil.toGUISelector("btw:conceptual-proximates>btw:none"),
        substitute: [
          { tag: "btw:none",
            type: "delete-parent",
            actions: [this.replaceNoneWithConceptualProximate] },
        ],
      },
      {
        selector: util.classFromOriginalName("btw:term"),
        // We don't want to let anything go through because this
        // can contain only text or a foreign element.
        pass: {},
      },
      {
        selector: util.classFromOriginalName("lg"),
        pass: {
          l: true,
        },
      },
      { selector: domutil.toGUISelector("*"),
        substitute: [
          { tag: "ref", type: "insert", actions: [this.insertBiblPtr] },
          { tag: "ref", type: "wrap", actions: [this.replaceBiblPtr] },
        ],
      },
    ];
  };

  BTWModeP._getBibliographicalInfo = function _getBibliographicalInfo() {
    if (this._getBibliographicalInfoPromise) {
      return this._getBibliographicalInfoPromise;
    }

    var promise = this._getBibliographicalInfoPromise =
          Promise.resolve($.ajax({
            url: this._bibl_url,
            headers: {
              Accept: "application/json",
            },
          })).bind(this)
          .catch(function catchHandler(_jqXHR) {
            throw new Error("cannot load bibliographical information");
          }).then(function then(data) {
            var urlToItem = Object.create(null);
            for (var i = 0; i < data.length; ++i) {
              var item = data[i];
              urlToItem[item.abstract_url] = item;
            }
            return urlToItem;
          });

    return promise;
  };

  BTWModeP._keyHandler = log.wrap(function keyHandler(_wedEvent, _ev) {
    // This is where we'd handle keys that are special to this mode if
    // we needed them.
  });

  BTWModeP.makeDecorator = function makeDecorator(_domlistener) {
    var obj = Object.create(BTWDecorator.prototype);
    // Make arg an array and add our extra argument(s).
    var args = Array.prototype.slice.call(arguments);
    args = [this, this._meta].concat(args);
    BTWDecorator.apply(obj, args);

    // This is as good a place as any where to attach listeners to the
    // data updater directly. Note that we attach to the updater
    // rather than the domlistener because otherwise we would trigger
    // a data update from a GUI update, which is likely to result in
    // issues. (Crash, infinite loop, etc.)

    var noneEName = this._resolver.resolveName("btw:none");
    this._editor.data_updater.addEventListener(
      "deleteNode",
      function deleteNode(ev) {
        var el = ev.node;
        if (!(el.tagName === "btw:antonym" ||
              el.tagName === "btw:cognate" ||
              el.tagName === "btw:conceptual-proximate")) {
          return;
        }

        if (ev.former_parent.childElementCount === 0) {
          this._editor.data_updater.insertBefore(
            ev.former_parent,
            transformation.makeElement(el.ownerDocument,
                                       noneEName.ns, "btw:none"),
            null);
        }
      }.bind(this));

    this._editor.data_updater.addEventListener(
      "insertNodeAt",
      function insertNodeAt(ev) {
        var ed = this._editor;

        function processNode(node) {
          if (!node.childNodes.length) {
            ed.data_updater.insertBefore(
              node,
              transformation.makeElement(node.ownerDocument,
                                         noneEName.ns,
                                         "btw:none"), null);
          }
        }
        function processList(nodes) {
          for (var i = 0; i < nodes.length; ++i) {
            var node = nodes[i];
            processNode(node);
          }
        }

        var node = ev.node;

        if (node.nodeType !== Node.ELEMENT_NODE) {
          return;
        }

        var antonyms = node.getElementsByTagName("btw:antonyms");
        var cognates = node.getElementsByTagName("btw:cognates");
        var cps = node.getElementsByTagName("btw:conceptual-proximates");
        processList(antonyms);
        processList(cognates);
        processList(cps);

        if (node.tagName === "btw:antonyms" ||
            node.tagName === "btw:cognates" ||
            node.tagName === "btw:conceptual-proximates") {
          processNode(node);
        }
      }.bind(this));

    return obj;
  };

  /**
   *
   * {@link module:wed/modes/btw/btw_mode~BTWMode#transformationFilters
   * transformationFilters} are used as follows:
   *
   * - for each ``filter``, if ``filter.selector`` matches ``container``:
   *
   *    + if ``filter.pass`` is defined and ``filter.pass[tag]`` is:
   *
   *      * ``undefined``, then return an empty list.
   *
   *      * is ``true``, then continue.
   *
   *      * is defined, a list and ``type`` is absent from it, then return an
   *        empty list.
   *
   *    + if ``filter.substitute`` is defined and the ``tag`` and
   *      ``type`` parameters equal the ``tag`` and ``type`` properties
   *      of any of the substitutions in the list, then return the
   *      ``actions`` property of the substitution.
   *
   *  - if the method has not returned earlier return the
   *  transformations from the transformation registry.
   *
   * <!-- This is copied from the method in the parent class. -->
   * @param {Array.<String>|String} type The type or types of
   * transformations to return.
   * @param {String} tag The tag name we are interested in.
   * @param {Node} container The position in the data tree.
   * @param {Integer} offset The position in the data tree.
   * @returns {Array.<module:action~Action>} An array
   * of actions.
   */
  BTWModeP.getContextualActions = function getContextualActions(type,
                                                                tag,
                                                                container,
                                                                offset) {
    var el = (container.nodeType === Node.TEXT_NODE) ?
          container.parentNode : container;
    var guiEl = $.data(el, "wed_mirror_node");


    if (!(type instanceof Array)) {
      type = [type];
    }

    //
    // Special case:
    //
    // None of the non-inline elements should be able to be unwrapped.
    //
    if (!this._meta.isInline(guiEl)) {
      var unwrap = type.indexOf("unwrap");
      if (unwrap !== -1) {
        type.splice(unwrap, 1);
      }
    }

    var ret = [];
    for (var i = 0; i < this.transformationFilters.length; ++i) {
      var filter = this.transformationFilters[i];
      if (guiEl.matches(filter.selector)) {
        // eslint-disable-next-line no-labels, no-restricted-syntax
        typeLoop:
        for (var tix = 0; tix < type.length; ++tix) {
          var t = type[tix];

          if (filter.pass) {
            var trTypes = filter.pass[tag];
            if (!trTypes || // not among those to pass
                (trTypes !== true && // true means pass
                 trTypes.indexOf(t) === -1)) {
              // Skip this type...
              continue;
            }
          }

          if (filter.substitute) {
            for (var j = 0; j < filter.substitute.length; ++j) {
              var substitute = filter.substitute[j];
              if (substitute.tag === tag && substitute.type === t) {
                ret = ret.concat(substitute.actions);
                // eslint-disable-next-line no-labels
                break typeLoop;
              }
            }
          }

          ret = ret.concat(Mode.prototype.getContextualActions.call(
            this, t, tag, container, offset));
        }

        // First match of a selector ends the process.
        break;
      }
    }

    // Here we transform the returned array in ways that cannot be
    // captured by transformationFilters.
    return ret.filter(function filterFn(x) {
      // We want insertRefText to be included only if the current
      // container does not have children.
      if (x !== this.insertRefText) {
        return true;
      }

      return el.childNodes.length === 0;
    }, this);
  };

  BTWModeP.getStylesheets = function getStylesheets() {
    return [require.toUrl("./btw-mode.css")];
  };

  BTWModeP.getValidator = function getValidator() {
    return new Validator(this._editor.gui_root, this._editor.data_root);
  };

  exports.Mode = BTWMode;
});
