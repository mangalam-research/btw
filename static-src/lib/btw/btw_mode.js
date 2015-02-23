/**
 * @module wed/modes/btw/btw_mode
 * @desc Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_mode */
    function (require, exports, module) {
'use strict';

var $ = require("jquery");
var util = require("wed/util");
var log = require("wed/log");
var Mode = require("wed/modes/generic/generic").Mode;
var oop = require("wed/oop");
var dloc = require("wed/dloc");
var BTWDecorator = require("./btw_decorator").BTWDecorator;
var transformation = require("wed/transformation");
var Toolbar = require("./btw_toolbar").Toolbar;
var rangy = require("rangy");
var btw_meta = require("./btw_meta");
var domutil = require("wed/domutil");
var key = require("wed/key");
var btw_tr = require("./btw_tr");
var btw_actions = require("./btw_actions");
var Validator = require("./btw_validator").Validator;
var Promise = require("bluebird").Promise;
require("jquery.cookie");

/**
 * @class
 * @extends module:wed/modes/generic/generic~Mode
 */
function BTWMode (options) {
    options.meta = {
        path: btw_meta,
        options: {
            metadata: require.toUrl('./btw-storage-metadata.json')
        }
    };
    this._bibl_url = options.bibl_url;
    delete options.bibl_url;
    // We can initiate this right away.
    this._getBibliographicalInfo();
    Mode.call(this, options);
    this._contextual_menu_items = [];
    this._headers = {
        "X-CSRFToken": $.cookie("csrftoken")
    };

    this._wed_options.metadata = {
        name: "BTW Mode",
        authors: ["Louis-Dominique Dubeau"],
        description: "This is a mode for use with BTW.",
        license: "MPL 2.0",
        copyright: "2013 Mangalam Research Center for Buddhist Languages"
    };

    this._wed_options.label_levels.max = 2;
    this._wed_options.attributes = "hide";
}

oop.inherit(BTWMode, Mode);

BTWMode.prototype.init = function (editor) {
    Mode.prototype.init.call(this, editor);

    this._hyperlink_modal = editor.makeModal();
    this._hyperlink_modal.setTitle("Insert hyperlink to sense");
    this._hyperlink_modal.addButton("Insert", true);
    this._hyperlink_modal.addButton("Cancel");

    editor.setNavigationList("");

    this.insert_sense_ptr_action = new btw_actions.SensePtrDialogAction(
        editor, "Insert a new hyperlink to a sense",
        undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.insert_example_ptr_action = new btw_actions.ExamplePtrDialogAction(
        editor, "Insert a new hyperlink to an example",
        undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.insert_ptr_tr = new transformation.Transformation(
        editor, "add", "Insert a pointer", btw_tr.insert_ptr);

    this.insert_ref_tr = new transformation.Transformation(
        editor, "add", "Insert a reference", btw_tr.insert_ref);

    this.replace_selection_with_ref_tr = new transformation.Transformation(
        editor, "wrap", "Replace the selection with a reference",
        btw_tr.replace_selection_with_ref);

    this.swap_with_prev_tr = new transformation.Transformation(
        editor, "swap-with-previous", "Swap with previous sibling", undefined,
        "<i class='fa fa-long-arrow-up fa-fw'></i>",
        function (editor, data) {
        return transformation.swapWithPreviousHomogeneousSibling(
            editor, data.node);
        });

    this.replace_none_with_antonym =
        btw_tr.make_replace_none(editor, "btw:antonym");

    this.replace_none_with_cognate =
        btw_tr.make_replace_none(editor, "btw:cognate");

    this.replace_none_with_conceptual_proximate =
        btw_tr.make_replace_none(editor, "btw:conceptual-proximate");

    this.swap_with_next_tr = new transformation.Transformation(
        editor, "swap-with-next", "Swap with next sibling", undefined,
        "<i class='fa fa-long-arrow-down fa-fw'></i>",
        function (editor, data) {
        return transformation.swapWithNextHomogeneousSibling(
            editor, data.node);
    });

    this.insert_ref_text = new transformation.Transformation(
        this._editor, "add", "Add custom text to reference",
        function (editor, data) {
        var caret = editor.getGUICaret();
        var ref = $(caret.node).closest(util.classFromOriginalName("ref"))[0];
        var ph = editor.insertTransientPlaceholderAt(caret.make(
            ref, ref.childNodes.length));
        editor.decorator.refreshElement(dloc.findRoot(ref).node, ref);
        editor.setGUICaret(ph, 0);

    }.bind(this));

    this.insert_bibl_ptr = new btw_actions.InsertBiblPtrAction(
        this._editor,
        "Insert a new bibliographical reference",
        "",
        "<i class='fa fa-book fa-fw'></i>",
        true);

    // Yes, we inherit from InsertBiblPtrAction even though we are
    // replacing.
    this.replace_bibl_ptr = new btw_actions.InsertBiblPtrAction(
        this._editor,
        "Replace the selection with a bibliographical reference",
        "",
        "<i class='fa fa-book fa-fw'></i>",
        true);

    this._toolbar = new Toolbar(this, editor);
    var toolbar_top = this._toolbar.getTopElement();
    editor.widget.insertBefore(toolbar_top, editor.widget.firstChild);
    $(editor.widget).on('wed-global-keydown.btw-mode',
                        this._keyHandler.bind(this));
    editor.excludeFromBlur(toolbar_top);

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

    var pass_in_cit = {
        "btw:lemma-instance": true,
        "btw:antonym-instance": true,
        "btw:cognate-instance": true,
        "btw:conceptual-proximate-instance": true,
        "p": true,
        "lg": true,
        "ref": ["insert", "wrap"]
    };

    var pass_in_tr = $.extend({}, pass_in_cit);
    delete pass_in_tr.ref;

    var pass_in_foreign = $.extend({}, pass_in_tr);
    delete pass_in_foreign.p;
    delete pass_in_foreign.lg;
    pass_in_foreign.foreign = ["delete-parent", "unwrap"];

    /**
     * @private
     * @property {Array.<TransformationFilter>} transformation_filters
     * A list of transformation filters to apply whenever the
     * getContextualActions method is called.
     */
    this.transformation_filters = [
        { selector: domutil.toGUISelector(
            ["btw:overview",
             "btw:definition"].join(",")),
          pass: {}
        },
        {
            selector: domutil.toGUISelector("btw:sense-discrimination"),
            pass: {
                "btw:sense": true
            }
        },
        { // paragraph in a definition
            selector: domutil.toGUISelector("btw:definition>p"),
            pass: {
                "btw:sense-emphasis": true,
                "ptr": true
            },
            substitute: [ {tag: "ptr",
                           type: "insert", actions: [this.insert_sense_ptr_action]} ]
        },
        { selector: util.classFromOriginalName("ptr"),
          pass: { "ptr": ["delete-parent"] }
        },
        { selector: util.classFromOriginalName("ref"),
          pass: {
              "ref": ["delete-parent", "insert"]
          },
          substitute: [
              {tag: "ref", type: "insert", actions: [this.insert_ref_text]}
          ]
        },
        { selector: util.classFromOriginalName("btw:citations"),
          substitute: [
              {tag: "ptr", type: "insert",
               actions: [this.insert_example_ptr_action] }
          ]
        },
        { selector: domutil.toGUISelector("btw:tr"),
          pass: pass_in_tr
        },
        { selector: domutil.toGUISelector("btw:cit"),
          pass: pass_in_cit,
          substitute: [
              { tag: "ref",
                type: "insert",
                actions: [ this.insert_bibl_ptr]
              },
              { tag: "ref",
                type: "wrap",
                actions: [ this.replace_bibl_ptr]
              }
          ]
        },
        { selector: domutil.toGUISelector(
            "btw:citations foreign, btw:other-citations foreign"),
          pass: pass_in_foreign
        },
        { selector: util.classFromOriginalName("foreign"),
          pass: {
              "foreign": ["delete-parent", "unwrap"]
          }
        },
        { selector: domutil.toGUISelector("btw:antonyms>btw:none"),
          substitute: [
              { tag: "btw:none",
                type: "delete-parent",
                actions: [this.replace_none_with_antonym] }
          ]
        },
        { selector: domutil.toGUISelector("btw:cognates>btw:none"),
          substitute: [
              { tag: "btw:none",
                type: "delete-parent",
                actions: [this.replace_none_with_cognate] }
          ]
        },
        { selector: domutil.toGUISelector("btw:conceptual-proximates>btw:none"),
          substitute: [
              { tag: "btw:none",
                type: "delete-parent",
                actions: [this.replace_none_with_conceptual_proximate] }
          ]
        },
        {
            selector: util.classFromOriginalName("btw:term"),
            // We don't want to let anything go through because this
            // can contain only text or a foreign element.
            pass: {}
        },
        {
            selector: util.classFromOriginalName("lg"),
            pass: {
                "l": true
            }
        },
        { selector: domutil.toGUISelector("*"),
          substitute: [
              { tag: "ref",
                type: "insert",
                actions: [ this.insert_bibl_ptr]
              },
              { tag: "ref",
                type: "wrap",
                actions: [ this.replace_bibl_ptr]
              }
          ]
        },
    ];
};

BTWMode.prototype._getBibliographicalInfo = function () {
    if (this._getBibliographicalInfo_promise)
        return this._getBibliographicalInfo_promise;

    var promise = this._getBibliographicalInfo_promise =
            Promise.resolve($.ajax({
        url: this._bibl_url,
        headers: {
            Accept: "application/json"
        }
    })).bind(this)
    .catch(function (jqXHR) {
        throw new Error("cannot load bibliographical information");
    }).then(function (data) {
        var url_to_item = Object.create(null);
        for (var i = 0, item; (item = data[i]); ++i) {
            url_to_item[item.url] = item;
        }
        return url_to_item;
    });

    return promise;
};

BTWMode.prototype._keyHandler = log.wrap(function (wed_event, ev) {
    // This is where we'd handle keys that are special to this mode if
    // we needed them.
});

BTWMode.prototype.makeDecorator = function (domlistener) {
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

    var none_ename = this._resolver.resolveName('btw:none');
    this._editor.data_updater.addEventListener("deleteNode",
                                               function (ev) {
        var el = ev.node;
        if (!(el.tagName === "btw:antonym" ||
              el.tagName === "btw:cognate" ||
              el.tagName === "btw:conceptual-proximate"))
            return;
        if (ev.former_parent.childElementCount === 0)
            this._editor.data_updater.insertBefore(
                ev.former_parent,
                transformation.makeElement(el.ownerDocument,
                                           none_ename.ns, 'btw:none'),
                null);
    }.bind(this));

    this._editor.data_updater.addEventListener("insertNodeAt",
                                               function (ev) {
        var ed = this._editor;

        function processNode(node) {
            if (!node.childNodes.length)
                ed.data_updater.insertBefore(
                    node,
                    transformation.makeElement(node.ownerDocument,
                                               none_ename.ns,
                                               'btw:none'), null);
        }
        function processList(nodes) {
            for (var i = 0, node; (node = nodes[i]); ++i) {
                processNode(node);
            }
        }

        var node = ev.node;

        if (node.nodeType !== Node.ELEMENT_NODE)
            return;

        var antonyms = node.getElementsByTagName("btw:antonyms");
        var cognates = node.getElementsByTagName("btw:cognates");
        var cps = node.getElementsByTagName("btw:conceptual-proximates");
        processList(antonyms);
        processList(cognates);
        processList(cps);

        if (node.tagName === "btw:antonyms" ||
            node.tagName === "btw:cognates" ||
            node.tagName === "btw:conceptual-proximates")
            processNode(node);

    }.bind(this));


    return obj;
};

/**
 *
 * {@link module:wed/modes/btw/btw_mode~BTWMode#transformation_filters
 * transformation_filters} are used as follows:
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
BTWMode.prototype.getContextualActions = function (type, tag,
                                                   container, offset) {
    var el = (container.nodeType === Node.TEXT_NODE) ?
            container.parentNode : container;
    var gui_el = $.data(el, "wed_mirror_node");


    if (!(type instanceof Array))
        type = [type];

    //
    // Special case:
    //
    // None of the non-inline elements should be able to be unwrapped.
    //
    if (!this._meta.isInline(gui_el)) {
        var unwrap = type.indexOf("unwrap");
        if (unwrap !== -1)
            type.splice(unwrap, 1);
    }

    var ret = [];
    filter_loop:
    for(var i = 0; i < this.transformation_filters.length; ++i) {
        var filter = this.transformation_filters[i];
        if (gui_el.matches(filter.selector)) {

            type_loop:
            for(var tix = 0; tix < type.length; ++tix) {
                var t = type[tix];

                if (filter.pass) {
                    var tr_types = filter.pass[tag];
                    if (!tr_types || // not among those to pass
                        (tr_types !== true && // true means pass
                         tr_types.indexOf(t) === -1))
                        // Skip this type...
                        continue type_loop;
                }

                if (filter.substitute) {
                    for (var j = 0; j < filter.substitute.length; ++j) {
                        var substitute = filter.substitute[j];
                        if (substitute.tag === tag && substitute.type === t) {
                            ret = ret.concat(substitute.actions);
                            break type_loop;
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
    // captured by transformation_filters.
    return ret.filter(function (x) {

        // We want insert_ref_text to be included only if the current
        // container does not have children.
        if (x !== this.insert_ref_text)
            return true;

        return el.childNodes.length === 0;
    }, this);
};

BTWMode.prototype.getStylesheets = function () {
    return [require.toUrl("./btw-mode.css")];
};

BTWMode.prototype.getValidator = function () {
    return new Validator(this._editor.gui_root, this._editor.data_root);
};
exports.Mode = BTWMode;

});
