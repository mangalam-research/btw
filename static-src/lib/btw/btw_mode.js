define(function (require, exports, module) {
'use strict';

var $ = require("jquery");
var util = require("wed/util");
var log = require("wed/log");
var Mode = require("wed/modes/generic/generic").Mode;
var oop = require("wed/oop");
var BTWDecorator = require("./btw_decorator").BTWDecorator;
var transformation = require("wed/transformation");
var Toolbar = require("./btw_toolbar").Toolbar;
var rangy = require("rangy");
var btw_meta = require("./btw_meta");
var domutil = require("wed/domutil");
var btw_tr = require("./btw_tr");
var btw_actions = require("./btw_actions");
require("jquery.cookie");

var prefix_to_uri = {
    "btw": "http://mangalamresearch.org/ns/btw-storage",
    "tei": "http://www.tei-c.org/ns/1.0",
    "xml": "http://www.w3.org/XML/1998/namespace",
    "": "http://www.tei-c.org/ns/1.0"
};

function BTWMode (options) {
    options.meta = btw_meta;
    this._bibl_abbrev_url = options.bibl_abbrev_url;
    this._bibl_info_url = options.bibl_info_url;
    delete options.bibl_info_url;
    delete options.bibl_abbrev_url;
    Mode.call(this, options);
    Object.keys(prefix_to_uri).forEach(function (k) {
        this._resolver.definePrefix(k, prefix_to_uri[k]);
    }.bind(this));
    this._contextual_menu_items = [];
    this._headers = {
        "X-CSRFToken": $.cookie("csrftoken")
    };
}

oop.inherit(BTWMode, Mode);

BTWMode.optionResolver = function (options, callback) {
    callback(options);
};


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

    this.insert_bibl_ptr_action = new btw_actions.InsertBiblPtrDialogAction(
        editor, "Insert a new bibliographical reference.");

    this.transformation_filters = [
        { selector: util.classFromOriginalName("btw:definition") + ">" +
          util.classFromOriginalName("p"), // paragraph in a definition
          pass: ["term", "btw:sense-emphasis", "ptr"],
          // filter: [...],
          substitute: [ {tag: "ptr", actions: [this.insert_sense_ptr_action,
                                              this.insert_bibl_ptr_action]} ]
        },
        { selector: util.classFromOriginalName("ptr"),
          pass: []
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
    var caret = this._editor.getCaret();

    if (caret === undefined)
        return true;

    // XXX we do not work with anything else than text nodes.
    if (caret[0].nodeType !== Node.TEXT_NODE)
        return true;

    // Find the previous word
    var offset = caret[0].nodeValue.slice(0, caret[1]).search(/\w+$/);

    // This could happen if the user enters spaces at the start of
    // an element for instance.
    if (offset === -1)
        return true;

    var word = caret[0].nodeValue.slice(offset, caret[1]);

    // XXX hardcoded
    var $new_element;
    if (word === "Abhidharma") {
        $new_element = transformation.wrapTextInElement(
            this._editor.data_updater,
            caret[0], offset, caret[1], "term", {"xml:lang": "sa-Latn"});
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


BTWMode.prototype.getContextualActions = function (type, tag,
                                                   container, offset) {
    // We want the first *element* container, selecting div accomplishes this.
    var $container = $(container).closest("div");
    for(var i = 0; i < this.transformation_filters.length; ++i) {
        var filter = this.transformation_filters[i];
        if ($container.is(filter.selector)) {

            if (filter.pass && filter.pass.indexOf(tag) === -1)
                return [];

            if (filter.filter && filter.filter.indexOf(tag) > -1)
                return [];

            if (filter.substitute) {
                for (var j = 0; j < filter.substitute.length; ++j) {
                    var substitute = filter.substitute[j];
                    if (substitute.tag === tag) {
                        return substitute.actions;
                    }
                }
            }
        }
    }

    return this._tr.getTagTransformations(type, tag);
};

BTWMode.prototype.getContextualMenuItems = function () {
    var items = [];
    var caret = this._editor.getCaret();
    var $container = $(caret[0]);
    var ptr = $container.closest(util.classFromOriginalName("ptr")).get(0);
    if (ptr)
        this._tr.getTagTransformations("delete-element", "ptr").forEach(
            function (x) {
            var data = {node: this._editor.toDataNode(ptr),
                        element_name: "ptr"};
            items.push([x.getDescriptionFor(data), data,
                        transformation.moveDataCaretFirst(
                            this._editor,
                            this._editor.toDataCaret(ptr, 0),
                            x)]);
        }.bind(this));

    var ref = $container.closest(util.classFromOriginalName("ref")).get(0);
    if (ref) {
        var data = {node: this._editor.toDataNode(ref), element_name: "ref" };
        this._tr.getTagTransformations("delete-element", "ref").forEach(
            function (x) {
            items.push([x.getDescriptionFor(data), data,
                        transformation.moveDataCaretFirst(
                            this._editor,
                            this._editor.toDataCaret(ref, 0),
                            x)]);
        }.bind(this));
        var tr = new transformation.Transformation(
            this._editor, "Insert reference text",
            function (editor, node, element_name, data) {
            var gui_node =
                this._editor.pathToNode(this._editor.data_updater.nodeToPath(node));
            this._editor.insertPlaceholderAt(gui_node,
                                             gui_node.childNodes.length - 1);
            this._editor.setCaret(gui_node.lastChild.previousSibling, 0);
        }.bind(this));
        items.push([tr.getDescriptionFor(data), data,
                    transformation.moveDataCaretFirst(
                        this._editor,
                        this._editor.toDataCaret(ref, 0),
                        tr)]);
    }

    return items.concat(this._contextual_menu_items);
};

BTWMode.prototype.getStylesheets = function () {
    return [require.toUrl("./btw.css")];
};

BTWMode.prototype.nodesAroundEditableContents = function (parent) {
    var ret = [null, null];
    var start = parent.childNodes[0];
    while ($(start).is("._gui, .head")) {
        ret[0] = start;
        start = start.nextSibling;
    }
    var end = parent.childNodes[parent.childNodes.length - 1];
    while ($(end).is("._gui")) {
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
