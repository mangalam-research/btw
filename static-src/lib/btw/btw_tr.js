define(function (require, exports, module) {
'use strict';

var oop = require("wed/oop");
var domutil = require("wed/domutil");
var closest = domutil.closest;
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
var makeElement = transformation.makeElement;
var Transformation = transformation.Transformation;

var _indexOf = Array.prototype.indexOf;

function insert_ptr(editor, data) {
    var caret = editor.getDataCaret();
    var parent = caret.node;
    var index = caret.offset;

    // The data.target value is the wed ID target of the ptr. We must
    // find this element and add a data ID.
    var target = editor.gui_root.ownerDocument.getElementById(data.target);
    var data_id = data.target.slice(4);
    target.setAttribute(util.encodeAttrName("xml:id"), data_id);
    $.data(target, "wed_mirror_node").setAttribute(util.encodeAttrName("xml:id"),
                                                   data_id);

    var ptr = makeElement('ptr', {'target': "#" + data_id});
    editor.data_updater.insertAt(parent, index, ptr);

    // The original parent and index information are no necessarily
    // representative because insertAt can do quite a lot of things to
    // insert the node.
    parent = ptr.parentNode;
    editor.setDataCaret(parent, Array.prototype.indexOf.call(parent.childNodes,
                                                             ptr));
}

function insert_ref(editor, data) {
    var caret = editor.getDataCaret();
    var parent = caret.node;
    var index = caret.offset;

    var ptr = makeElement('ref', {'target': data.target});
    editor.data_updater.insertAt(parent, index, ptr);
    var gui_node = editor.fromDataLocation(ptr, 0).node;

    // We must immediately set the caret because it is likely the old
    // caret is no longer valid.
    editor.setGUICaret(gui_node, 0);

    // We do this because if we set the caret immediately, it gets clobbered
    // by the later refreshing of the ref element.
    $(gui_node).one('wed-refresh', function () {
        editor.setGUICaret(
            gui_node,
            _indexOf.call(gui_node.childNodes,
                          domutil.childByClass(gui_node, "_ref_abbr")) + 1);
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
    Transformation.call(this, editor, desc, language, undefined, true,
                        set_language_handler);
}

oop.inherit(SetTextLanguageTr, Transformation);

SetTextLanguageTr.prototype.execute = function(data) {
    data = data || {};
    data.language = this._language;
    Transformation.prototype.execute.call(this, data);
};

function set_language_handler(editor, data) {
    var range = editor.getDataSelectionRange();

    // We don't do anything if the range is collapsed.
    if (!range || range.collapsed)
        return;

    if (!domutil.isWellFormedRange(range)) {
        editor.straddling_modal.modal();
        throw new AbortTransformationException(
            "range is not well-formed");
    }

    var lang_code = btw_util.languageToLanguageCode(data.language);
    var selector = "foreign";
    var data_selector = jqutil.toDataSelector(selector);

    var container = range.startContainer;
    var cl = closest(container, data_selector, editor.data_root);
    if (cl) {
        this._nesting_modal.modal();
        throw new AbortTransformationException(
            "the range does not wholly contain the contents of a parent " +
                "foreign language element");
    }

    var foreign = container.ownerDocument.createElement("div");
    foreign.className = "_real foreign";
    foreign.setAttribute(util.encodeAttrName("xml:lang"), lang_code);
    var cut_ret = editor.data_updater.cut(
        makeDLoc(editor.data_root, range.startContainer, range.startOffset),
        makeDLoc(editor.data_root, range.endContainer, range.endOffset));
    var cut_nodes = cut_ret[1];
    for (var i = 0, el; (el = cut_nodes[i]) !== undefined; ++i)
        foreign.appendChild(el);
    editor.data_updater.insertAt(cut_ret[0], foreign);
    range.selectNodeContents(foreign);
    editor.setDataSelectionRange(range);
}

function RemoveMixedTr(editor, language) {
    this._language = language;
    this._nesting_modal = getNestingModal(editor);
    Transformation.call(this, editor, "Remove mixed-content markup",
                        "Remove mixed-content markup",
                        '<i class="fa fa-eraser"></i>',
                        true,
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

    // Do nothing if we don't have a range.
    if (!range || range.collapsed)
        return;

    if (!domutil.isWellFormedRange(range)) {
        editor.straddling_modal.modal();
        throw new AbortTransformationException(
            "range is not well-formed");
    }

    var cut_ret = editor.data_updater.cut(
        makeDLoc(editor.data_root, range.startContainer, range.startOffset),
        makeDLoc(editor.data_root, range.endContainer, range.endOffset));
    var div = range.startContainer.ownerDocument.createElement("div");
    var new_text = '';
    var cut_nodes = cut_ret[1];
    for(var i = 0, el; (el = cut_nodes[i]) !== undefined; ++i)
        new_text += el.textContent;
    var text_node = range.startContainer.ownerDocument.createTextNode(new_text);

    if (editor.validator.speculativelyValidate(cut_ret[0], text_node)) {
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
        "<i class='fa fa-plus fa-fw'></i>",
        function (editor, data) {
        var caret = editor.getDataCaret();
        var parent = caret.node;
        var index = caret.offset;

        // This is the node that contains btw:none.
        var grandparent = parent.parentNode;

        var actions = editor.mode.getContextualActions("insert", replaced_with,
                                                       grandparent, 0);
        actions[0].execute({
            move_caret_to: makeDLoc(editor.data_root, grandparent, 0),
            element_name: replaced_with
        });
        editor.data_updater.removeNode(parent);
    });
}


exports.insert_ptr = insert_ptr;
exports.insert_ref = insert_ref;
exports.SetTextLanguageTr = SetTextLanguageTr;
exports.RemoveMixedTr = RemoveMixedTr;
exports.make_replace_none = make_replace_none;

});
