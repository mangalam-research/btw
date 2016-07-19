/**
 * @module wed/modes/btw/btw_tr
 * @desc Transformations for BTWMode.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_tr */ function (require,
                                                             exports,
                                                             _module) {
  "use strict";

  var oop = require("wed/oop");
  var domutil = require("wed/domutil");
  var closest = domutil.closest;
  var $ = require("jquery");

  var util = require("wed/util");
  var btwUtil = require("./btw_util");
  var AbortTransformationException =
        require("wed/exceptions").AbortTransformationException;
  var makeDLoc = require("wed/dloc").makeDLoc;

  var transformation = require("wed/transformation");
  var makeElement = transformation.makeElement;
  var Transformation = transformation.Transformation;

  var _indexOf = Array.prototype.indexOf;

  function insertPtr(editor, data) {
    var caret = editor.getDataCaret();
    var parent = caret.node;
    var index = caret.offset;

    // The data.target value is the wed ID target of the ptr. We must
    // find this element and add a data ID.
    var target = editor.gui_root.ownerDocument.getElementById(data.target);
    var dataId = data.target.slice(4);
    target.setAttribute(util.encodeAttrName("xml:id"), dataId);
    $.data(target, "wed_mirror_node").setAttributeNS(
      "http://www.w3.org/XML/1998/namespace", "xml:id", dataId);

    var ename = editor.mode.getAbsoluteResolver().resolveName("ptr");

    var ptr = makeElement(parent.ownerDocument,
                          ename.ns, "ptr", { "target": "#" + dataId });
    editor.data_updater.insertAt(parent, index, ptr);

    // The original parent and index information are no necessarily
    // representative because insertAt can do quite a lot of things to
    // insert the node.
    parent = ptr.parentNode;
    editor.setDataCaret(parent, Array.prototype.indexOf.call(parent.childNodes,
                                                             ptr));
  }

  function insertRef(editor, data) {
    var caret = editor.getDataCaret();
    var parent = caret.node;
    var index = caret.offset;

    var ename = editor.mode.getAbsoluteResolver().resolveName("ref");
    var ptr = makeElement(parent.ownerDocument, ename.ns, "ref",
                          { target: data.target });
    editor.data_updater.insertAt(parent, index, ptr);
    var guiNode = editor.fromDataLocation(ptr, 0).node;

    // We must immediately set the caret because it is likely the old
    // caret is no longer valid.
    editor.setGUICaret(guiNode, 0);

    // We do this because if we set the caret immediately, it gets clobbered
    // by the later refreshing of the ref element.
    $(guiNode).one("wed-refresh", function refresh() {
      editor.setGUICaret(
        guiNode,
        _indexOf.call(guiNode.childNodes,
                      domutil.childByClass(guiNode, "_ref_abbr")) + 1);
    });
  }

  function replaceSelectionWithRef(editor, data) {
    var range = editor.getDataSelectionRange();
    if (!domutil.isWellFormedRange(range)) {
      throw new Error("malformed range");
    }

    var startCaret = makeDLoc(editor.data_root,
                              range.startContainer, range.startOffset);
    var endCaret = makeDLoc(editor.data_root,
                            range.endContainer, range.endOffset);

    var cutRet = editor.data_updater.cut(startCaret, endCaret);
    editor.setDataCaret(cutRet[0]);
    insertRef(editor, data);
  }


  var NESTING_MODAL_KEY = "btw_mode.btw_tr.nesting_modal";
  function getNestingModal(editor) {
    var nestingModal = editor.getModeData(NESTING_MODAL_KEY);
    if (nestingModal) {
      return nestingModal;
    }

    nestingModal = editor.makeModal();
    nestingModal.setTitle("Invalid nesting");
    nestingModal.setBody(
      "<p>In this part of the article, you cannot embed one " +
        "language into another.</p>");
    nestingModal.addButton("Ok", true);
    editor.setModeData(NESTING_MODAL_KEY, nestingModal);

    return nestingModal;
  }

  function setLanguageHandler(editor, data) {
    var range = editor.getDataSelectionRange();

    // We don't do anything if the range is collapsed.
    if (!range || range.collapsed) {
      return;
    }

    if (!domutil.isWellFormedRange(range)) {
      editor.straddling_modal.modal();
      throw new AbortTransformationException(
        "range is not well-formed");
    }

    var langCode = btwUtil.languageToLanguageCode(data.language);
    var selector = "foreign";
    var dataSelector = domutil.toGUISelector(selector);

    var container = range.startContainer;
    var cl = closest(container, dataSelector, editor.data_root);
    if (cl) {
      this._nestingModal.modal();
      throw new AbortTransformationException(
        "the range does not wholly contain the contents of a parent " +
          "foreign language element");
    }

    var ename = editor.mode.getAbsoluteResolver().resolveName("foreign");
    var foreign = makeElement(container.ownerDocument,
                              ename.ns, "foreign", { "xml:lang": langCode });
    var cutRet = editor.data_updater.cut(
      makeDLoc(editor.data_root, range.startContainer, range.startOffset),
      makeDLoc(editor.data_root, range.endContainer, range.endOffset));
    var cutNodes = cutRet[1];
    for (var i = 0; i < cutNodes.length; ++i) {
      var el = cutNodes[i];
      foreign.appendChild(el);
    }
    editor.data_updater.insertAt(cutRet[0], foreign);
    range.selectNodeContents(foreign);
    editor.setDataSelectionRange(range);
  }

  function SetTextLanguageTr(editor, language) {
    this._language = language;
    this._nestingModal = getNestingModal(editor);
    var desc = "Set language to " + language;
    Transformation.call(this, editor, undefined, desc, language, undefined,
                        true, setLanguageHandler);
  }

  oop.inherit(SetTextLanguageTr, Transformation);

  SetTextLanguageTr.prototype.execute = function execute(data) {
    data = data || {};
    data.language = this._language;
    Transformation.prototype.execute.call(this, data);
  };

  var REMOVE_MIXED_MODAL_KEY = "btw_mode.btw_tr.remove_mixed_modal";
  function getRemoveMixedModal(editor) {
    var removeMixedModal = editor.getModeData(REMOVE_MIXED_MODAL_KEY);
    if (removeMixedModal) {
      return removeMixedModal;
    }

    removeMixedModal = editor.makeModal();
    removeMixedModal.setTitle("Invalid");
    removeMixedModal.setBody(
      "<p>You cannot removed mixed-content markup from this selection " +
        "because the resulting document would be invalid.</p>");
    removeMixedModal.addButton("Ok", true);
    editor.setModeData(REMOVE_MIXED_MODAL_KEY, removeMixedModal);

    return removeMixedModal;
  }

  function removeMixedHandler(editor, _data) {
    var range = editor.getDataSelectionRange();

    // Do nothing if we don't have a range.
    if (!range || range.collapsed) {
      return;
    }

    if (!domutil.isWellFormedRange(range)) {
      editor.straddling_modal.modal();
      throw new AbortTransformationException(
        "range is not well-formed");
    }

    var cutRet = editor.data_updater.cut(
      makeDLoc(editor.data_root, range.startContainer, range.startOffset),
      makeDLoc(editor.data_root, range.endContainer, range.endOffset));
    var newText = "";
    var cutNodes = cutRet[1];
    for (var i = 0; i < cutNodes.length; ++i) {
      var el = cutNodes[i];
      newText += el.textContent;
    }
    var textNode = range.startContainer.ownerDocument.createTextNode(newText);

    if (editor.validator.speculativelyValidate(cutRet[0], textNode)) {
      getRemoveMixedModal().modal();
      throw new AbortTransformationException(
        "result would be invalid");
    }

    var insertRet = editor.data_updater.insertText(cutRet[0], newText);
    if (insertRet[0]) {
      range.setStart(insertRet[0], cutRet[0].offset);
      range.setEnd(insertRet[0], range.startOffset + newText.length);
    }
    else {
      range.setStart(insertRet[1], 0);
      range.setEnd(insertRet[1], newText.length);
    }

    editor.setDataSelectionRange(range);
  }

  function RemoveMixedTr(editor, language) {
    this._language = language;
    this._nestingModal = getNestingModal(editor);
    Transformation.call(this, editor, "delete", "Remove mixed-content markup",
                        "Remove mixed-content markup",
                        "<i class='fa fa-eraser'></i>",
                        true,
                        removeMixedHandler);
  }

  oop.inherit(RemoveMixedTr, Transformation);

  function makeReplaceNone(editor, replacedWith) {
    return new Transformation(
      editor, "add", "Create new " + replacedWith,
      function add(trEditor, _data) {
        var caret = trEditor.getDataCaret();
        var parent = caret.node;

        // This is the node that contains btw:none.
        var grandparent = parent.parentNode;

        var actions = trEditor.mode.getContextualActions("insert", replacedWith,
                                                       grandparent, 0);
        actions[0].execute({
          move_caret_to: makeDLoc(trEditor.data_root, grandparent, 0),
          name: replacedWith,
        });
        trEditor.data_updater.removeNode(parent);
      });
  }


  exports.insertPtr = insertPtr;
  exports.insertRef = insertRef;
  exports.replaceSelectionWithRef = replaceSelectionWithRef;
  exports.SetTextLanguageTr = SetTextLanguageTr;
  exports.RemoveMixedTr = RemoveMixedTr;
  exports.makeReplaceNone = makeReplaceNone;
});
