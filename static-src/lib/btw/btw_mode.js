/**
 * @module wed/modes/btw/btw_mode
 * @desc Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_mode */
    function (require, exports, module) {
'use strict';

var $ = require("jquery");
var jqutil = require("wed/jqutil");
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
var btw_tr = require("./btw_tr");
var btw_actions = require("./btw_actions");
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
    this._bibl_search_url = options.bibl_search_url;
    this._bibl_abbrev_url = options.bibl_abbrev_url;
    this._bibl_info_url = options.bibl_info_url;
    delete options.bibl_search_url;
    delete options.bibl_info_url;
    delete options.bibl_abbrev_url;
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
}

oop.inherit(BTWMode, Mode);

BTWMode.prototype.init = function (editor) {
    Mode.prototype.init.call(this, editor);

    this._hyperlink_modal = editor.makeModal();
    this._hyperlink_modal.setTitle("Insert hyperlink to sense");
    this._hyperlink_modal.addButton("Insert", true);
    this._hyperlink_modal.addButton("Cancel");

    this._bibliography_modal = editor.makeModal();
    this._bibliography_modal.setTitle("Insert bibliographical reference");
    this._bibliography_modal.addButton("Insert", true);
    this._bibliography_modal.addButton("Cancel");

    this._toolbar = new Toolbar(editor);
    $(editor.widget).prepend(this._toolbar.getTopElement());
    $(editor.widget).on('wed-global-keydown.btw-mode',
                        this._keyHandler.bind(this));

    this.insert_sense_ptr_action = new btw_actions.SensePtrDialogAction(
        editor, "Insert a new hyperlink to a sense");

    this.insert_ptr_tr = new transformation.Transformation(
        editor, "Insert a pointer", btw_tr.insert_ptr);

    this.insert_ref_tr = new transformation.Transformation(
        editor, "Insert a reference", btw_tr.insert_ref);

    this.swap_with_prev_tr = new transformation.Transformation(
        editor, "Swap with previous sibling", undefined,
        "<i class='icon-long-arrow-up'></i>",
        function (editor, data) {
        return transformation.swapWithPreviousHomogeneousSibling(
            editor, data.node);
        });

    this.swap_with_next_tr = new transformation.Transformation(
        editor, "Swap with next sibling", undefined,
        "<i class='icon-long-arrow-down'></i>",
        function (editor, data) {
        return transformation.swapWithNextHomogeneousSibling(
            editor, data.node);
    });

    this.insert_ref_text = new transformation.Transformation(
        this._editor, "Add custom text to reference",
        function (editor, data) {
        var caret = editor.getGUICaret();
        var $ref = $(caret.node).closest(util.classFromOriginalName("ref"));
        var ph = editor.insertTransientPlaceholderAt(caret.make(
            $ref[0], $ref[0].childNodes.length));
        editor.decorator.refreshElement($(dloc.findRoot($ref).node), $ref);
        editor.setGUICaret(ph, 0);

    }.bind(this));

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

    /**
     * @private
     * @property {Array.<TransformationFilter>} transformation_filters
     * A list of transformation filters to apply whenever the
     * getContextualActions method is called.
     */
    this.transformation_filters = [
        { selector: jqutil.toDataSelector(
            ["btw:overview",
             "btw:definition"].join(",")),
          pass: {}
        },
        {
            selector: jqutil.toDataSelector("btw:sense-discrimination"),
            pass: {
                "btw:sense": true
            }
        },
        { // paragraph in a definition
            selector: jqutil.toDataSelector("btw:definition>p"),
            pass: {
                "term": true,
                "btw:sense-emphasis": true,
                "ptr": true
            },
            // filter: [...],
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
        { selector: jqutil.toDataSelector("btw:subsense>btw:citations foreign"),
          pass: {
              "foreign": ["delete-parent"],
              "btw:lemma-instance": true
          }
        },
        { selector: jqutil.toDataSelector("btw:subsense>btw:citations btw:tr"),
          pass: {
              "btw:tr": ["delete-parent"],
              "btw:lemma-instance": true,
              "p": true,
              "lg": true,
              "btw:cit": true
          }
        },
        { selector: util.classFromOriginalName("foreign"),
          pass: {
              "foreign": ["delete-parent"]
          }
        }
    ];
};

BTWMode.prototype._keyHandler = log.wrap(function (e) {
    if (!e.ctrlKey && !e.altKey && e.which === 32)
        return this._assignLanguage(e);
}.bind(this));

// XXX This function needs to be contextual: don't assign
// languages in locations where language are already
// assigned. e.g. citations of primary sources.
BTWMode.prototype._assignLanguage = function (e) {
    var caret = this._editor.getGUICaret();

    if (caret === undefined)
        return true;

    // XXX we do not work with anything else than text nodes.
    if (caret.node.nodeType !== Node.TEXT_NODE)
        return true;

    // Find the previous word
    var offset = caret.node.nodeValue.slice(0, caret.offset).search(/\w+$/);

    // This could happen if the user enters spaces at the start of
    // an element for instance.
    if (offset === -1)
        return true;

    var word = caret.node.nodeValue.slice(offset, caret.offset);

    // XXX hardcoded
    var $new_element;
    if (word === "Abhidharma") {
        $new_element = transformation.wrapTextInElement(
            this._editor.data_updater,
            caret.node, offset, caret.offset, "term", {"xml:lang": "sa-Latn"});
        // Simulate a link
        if ($new_element !== undefined)
            $new_element.contents().wrapAll("<a href='fake'>");
    }

    if ($new_element !== undefined) {
        // Place the caret after the element we just wrapped.
        rangy.getNativeSelection().collapse(
            $new_element.get(0).nextSibling, 0);
        this._editor._caretChangeEmitter(e);
    }

    return true;
};

BTWMode.prototype.makeDecorator = function () {
    var obj = Object.create(BTWDecorator.prototype);
    // Make arg an array and add our extra argument(s).
    var args = Array.prototype.slice.call(arguments);
    args = [this, this._meta].concat(args);
    BTWDecorator.apply(obj, args);
    return obj;
};

BTWMode.prototype._getTransformationRegistry = function () {
    var ret = Mode.prototype._getTransformationRegistry.call(this);
    ret.addTagTransformations("insert", "ref",
                              new btw_actions.InsertBiblPtrDialogAction(
                                  this._editor,
                                  "Insert a new bibliographical reference"));
    return ret;
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
 *    + if ``filter.filter`` is defined and the ``tag`` **is** in it,
 *    then return an empty list.
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
    var ret;
    // We want the first *element* container, selecting div accomplishes this.
    var $container = $(container).closest("div");

    outer_loop: for(var i = 0; i < this.transformation_filters.length; ++i) {
        var filter = this.transformation_filters[i];
        if ($container.is(filter.selector)) {

            if (filter.pass) {
                var tr_types = filter.pass[tag];
                if (!tr_types || // not among those to pass
                    (tr_types !== true && // true means pass
                    tr_types.indexOf(type) === -1))
                    return [];
            }

            if (filter.filter && filter.filter.indexOf(tag) > -1)
                return [];

            if (filter.substitute) {
                for (var j = 0; j < filter.substitute.length; ++j) {
                    var substitute = filter.substitute[j];
                    if (substitute.tag === tag && substitute.type === type) {
                        ret = substitute.actions;
                        break outer_loop;
                    }
                }
            }
            break;
        }
    }

    if (!ret)
        ret = this._tr.getTagTransformations(type, tag);

    // Here we transform the returned array in ways that cannot be
    // captured by transformation_filters.
    return ret.filter(function (x) {
        if (x !== this.insert_ref_text)
            return true;

        return $container[0].childNodes.length === 0;
    }, this);
};

BTWMode.prototype.getStylesheets = function () {
    return [require.toUrl("./btw-mode.css")];
};

BTWMode.prototype.nodesAroundEditableContents = function (parent) {
    var ret = [null, null];
    var start = parent.childNodes[0];
    var $start = $(start);
    // Otherwise, we want to search because a start label may be
    // followed by a .head or ._open_ref_paren.
    while ($(start).is("._gui.__start_label, .head, ._open_ref_paren")) {
        ret[0] = start;
        start = start.nextSibling;
    }

    var end = parent.childNodes[parent.childNodes.length - 1];
    while ($(end).is("._gui.__end_label, ._close_ref_paren")) {
        ret[1] = end;
        end = end.previousSibling;
    }
    return ret;
};

BTWMode.prototype.makePlaceholderFor = function (el) {
    var name = util.getOriginalName(el);
    var ret;

    switch(name) {
    case "term":
        ret = domutil.makePlaceholder("term");
        break;
    default:
        ret = Mode.prototype.makePlaceholderFor.call(this, el);
    }

    return ret;
};

exports.Mode = BTWMode;

});
