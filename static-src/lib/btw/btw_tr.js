define(function (require, exports, module) {
'use strict';

var oop = require("wed/oop");
var domutil = require("wed/domutil");
var $ = require("jquery");
var jqutil = require("wed/jqutil");

var util = require("wed/util");
var sense_refs = require("./btw_refmans").sense_refs;
var btw_util = require("./btw_util");
var action = require("wed/action");
var AbortTransformationException =
        require("wed/exceptions").AbortTransformationException;
var makeDLoc = require("wed/dloc").makeDLoc;

var transformation = require("wed/transformation");
var insertElement = transformation.insertElement;
var makeElement = transformation.makeElement;
var Transformation = transformation.Transformation;

var _indexOf = Array.prototype.indexOf;

function insert_ptr(editor, data) {
    var caret = editor.getDataCaret();
    var parent = caret.node;
    var index = caret.offset;

    var $ptr = transformation.makeElement('ptr', {'target': data.target});
    editor.data_updater.insertAt(parent, index, $ptr.get(0));

    // The original parent and index information are no necessarily
    // representative because insertAt can do quite a lot of things to
    // insert the node.
    parent = $ptr.parent().get(0);
    editor.setDataCaret(parent, Array.prototype.indexOf.call(parent.childNodes,
                                                             $ptr.get(0)));
}

function insert_ref(editor, data) {
    var caret = editor.getDataCaret();
    var parent = caret.node;
    var index = caret.offset;

    var $ptr = transformation.makeElement('ref', {'target': data.target});
    editor.data_updater.insertAt(parent, index, $ptr[0]);
    var gui_node = editor.fromDataLocation($ptr[0], 0).node;
    // We do this because if we set the caret immediately, it gets clobbered
    // by the later refreshing of the ref element.
    $(gui_node).one('wed-refresh', function () {
        editor.setGUICaret(
            gui_node,
            _indexOf.call(gui_node.childNodes,
                          $(gui_node).children("._ref_abbr")[0]) + 1);
    });
}


var NESTING_MODAL_KEY = "btw_mode.btw_tr.nesting_modal";
function getNestingModal(editor) {
    var nesting_modal = editor.getModeData(NESTING_MODAL_KEY);
    if (nesting_modal)
        return nesting_modal;

    nesting_modal = editor.makeModal();
    nesting_modal.setTitle("Invalid nesting");
    nesting_modal.setBody(
        "<p>In this part of the article, you cannot embed one "+
            "language into another.</p>");
    nesting_modal.addButton("Ok", true);
    editor.setModeData(NESTING_MODAL_KEY, nesting_modal);

    return nesting_modal;
}

function SetTextLanguageTr(editor, language) {
    this._language = language;
    this._nesting_modal = getNestingModal(editor);
    var desc = "Set language to " + language;
    Transformation.call(this, editor, desc, language, set_language_handler);
}

oop.inherit(SetTextLanguageTr, Transformation);

SetTextLanguageTr.prototype.execute = function(data) {
    data = data || {};
    data.language = this._language;
    Transformation.prototype.execute.call(this, data);
};

function set_language_handler(editor, data) {
    var range = editor.getDataSelectionRange();
    if (!domutil.isWellFormedRange(range)) {
        editor.straddling_modal.modal();
        throw new AbortTransformationException(
            "range is not well-formed");
    }

    var lang_code = btw_util.languageToLanguageCode(data.language);
    var selector = "foreign";
    var data_selector = jqutil.toDataSelector(selector);

    var container = range.startContainer;
    var $closest = $(container).closest(data_selector);
    if ($closest.length > 0) {
        this._nesting_modal.modal();
        throw new AbortTransformationException(
            "the range does not wholly contain the contents of a parent " +
                "foreign language element");
    }

    var $realization = jqutil.selectorToElements(selector);
    var $foreign = $realization.findAndSelf(
        util.classFromOriginalName("foreign"));
    $foreign.attr(util.encodeAttrName("xml:lang"), lang_code);
    var cut_ret = editor.data_updater.cut(
        makeDLoc(editor.data_tree, range.startContainer, range.startOffset),
        makeDLoc(editor.data_tree, range.endContainer, range.endOffset));
    $foreign.append(cut_ret[1]);
    editor.data_updater.insertAt(cut_ret[0], $realization.get(0));
    range.selectNodeContents($foreign.get(0));
    editor.setDataSelectionRange(range);
}

function RemoveMixedTr(editor, language) {
    this._language = language;
    this._nesting_modal = getNestingModal(editor);
    Transformation.call(this, editor, "Remove mixed-content markup",
                        "Remove mixed-content markup",
                        '<i class="icon-eraser"></i>',
                        remove_mixed_handler);
}

oop.inherit(RemoveMixedTr, Transformation);

var REMOVE_MIXED_MODAL_KEY = "btw_mode.btw_tr.remove_mixed_modal";
function getRemoveMixedModal(editor) {
    var remove_mixed_modal = editor.getModeData(REMOVE_MIXED_MODAL_KEY);
    if (remove_mixed_modal)
        return remove_mixed_modal;

    remove_mixed_modal = editor.makeModal();
    remove_mixed_modal.setTitle("Invalid");
    remove_mixed_modal.setBody(
        "<p>You cannot removed mixed-content markup from this selection "+
            "because the resulting document would be invalid.</p>");
    remove_mixed_modal.addButton("Ok", true);
    editor.setModeData(REMOVE_MIXED_MODAL_KEY, remove_mixed_modal);

    return remove_mixed_modal;
}

function remove_mixed_handler(editor, data) {
    var range = editor.getDataSelectionRange();
    if (!domutil.isWellFormedRange(range)) {
        editor.straddling_modal.modal();
        throw new AbortTransformationException(
            "range is not well-formed");
    }

    var cut_ret = editor.data_updater.cut(
        makeDLoc(editor.data_tree, range.startContainer, range.startOffset),
        makeDLoc(editor.data_tree, range.endContainer, range.endOffset));
    var $div = $("<div>");
    var new_text = $(cut_ret[1]).text();
    var text_node = range.startContainer.ownerDocument.createTextNode(new_text);

    if (editor.validator.speculativelyValidate(range.startContainer,
                                               range.startOffset,
                                               text_node)) {
        getRemoveMixedModal().modal();
        throw new AbortTransformationException(
            "result would be invalid");
    }

    var insert_ret = editor.data_updater.insertText(cut_ret[0], new_text);
    if (insert_ret[0]) {
        range.setStart(insert_ret[0], cut_ret[0].offset);
        range.setEnd(insert_ret[0], range.startOffset + new_text.length);
    }
    else {
        range.setStart(insert_ret[1], 0);
        range.setEnd(insert_ret[1], new_text.length);
    }

    editor.setDataSelectionRange(range);
}

function make_replace_none(editor, replaced_with) {
    return new Transformation(
        editor, "Create new " + replaced_with, undefined,
        "<i class='icon-plus icon-fixed-width'></i>",
        function (editor, data) {
        var caret = editor.getDataCaret();
        var parent = caret.node;
        var index = caret.offset;

        // This is the node that contains btw:none.
        var grandparent = parent.parentNode;

        editor.data_updater.removeNodes(grandparent.childNodes);

        var $el = transformation.makeElement(replaced_with);
        editor.data_updater.insertAt(grandparent, 0, $el[0]);
        var gui_node = editor.fromDataLocation($el[0], 0).node;
        var nodes = editor.mode.nodesAroundEditableContents(gui_node);
        editor.setGUICaret(gui_node,
                           _indexOf.call(gui_node.childNodes, nodes[0]) + 2);
    });
}


exports.insert_ptr = insert_ptr;
exports.insert_ref = insert_ref;
exports.SetTextLanguageTr = SetTextLanguageTr;
exports.RemoveMixedTr = RemoveMixedTr;
exports.make_replace_none = make_replace_none;

});
