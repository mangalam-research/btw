/**
 * Transformations for BTWMode.
 * @author Louis-Dominique Dubeau
 */
import * as $ from "jquery";

import { makeDLoc } from "wed/dloc";
import * as domutil from "wed/domutil";
import { AbortTransformationException } from "wed/exceptions";
import * as transformation from "wed/transformation";
import * as util from "wed/util";

import * as btwUtil from "./btw-util";

const makeElement = transformation.makeElement;
const Transformation = transformation.Transformation;
const closest = domutil.closest;

const _indexOf = Array.prototype.indexOf;

// TEMPORARY TYPE DEFINITIONS
/* tslint:disable: no-any */
type Modal = any;
type Editor = any;
type Transformation = any;
type TransformationData = any;
/* tslint:enable: no-any */
// END TEMPORARY TYPE DEFINITIONS

export function insertPtr(editor: Editor, data: TransformationData): void {
  const caret = editor.getDataCaret();
  let parent = caret.node;
  const index = caret.offset;

  // The data.target value is the wed ID target of the ptr. We must find this
  // element and add a data ID.
  const target = editor.gui_root.ownerDocument.getElementById(data.target);
  const dataId = data.target.slice(4);
  target.setAttribute(util.encodeAttrName("xml:id"), dataId);
  $.data(target, "wed_mirror_node").setAttributeNS(
    // tslint:disable-next-line:no-http-string
    "http://www.w3.org/XML/1998/namespace", "xml:id", dataId);

  const ename = editor.mode.getAbsoluteResolver().resolveName("ptr");

  const ptr = makeElement(parent.ownerDocument,
                          ename.ns, "ptr", { target: `#${dataId}` });
  editor.data_updater.insertAt(parent, index, ptr);

  // The original parent and index information are no necessarily representative
  // because insertAt can do quite a lot of things to insert the node.
  parent = ptr.parentNode;
  editor.setDataCaret(parent, _indexOf.call(parent.childNodes, ptr));
}

export function insertRef(editor: Editor, data: TransformationData): void {
  const caret = editor.getDataCaret();
  const parent = caret.node;
  const index = caret.offset;

  const ename = editor.mode.getAbsoluteResolver().resolveName("ref");
  const ptr = makeElement(parent.ownerDocument, ename.ns, "ref",
                          { target: data.target });
  editor.data_updater.insertAt(parent, index, ptr);
  const guiNode = editor.fromDataLocation(ptr, 0).node;

  // We must immediately set the caret because it is likely the old caret is no
  // longer valid.
  editor.setGUICaret(guiNode, 0);

  // We do this because if we set the caret immediately, it gets clobbered by
  // the later refreshing of the ref element.
  $(guiNode).one("wed-refresh", () => {
    editor.setGUICaret(
      guiNode,
      _indexOf.call(guiNode.childNodes,
                    domutil.childByClass(guiNode, "_ref_abbr")) as number + 1);
  });
}

export function replaceSelectionWithRef(editor: Editor,
                                        data: TransformationData): void {
  const range = editor.getDataSelectionRange();
  if (!domutil.isWellFormedRange(range)) {
    throw new Error("malformed range");
  }

  const startCaret = makeDLoc(editor.data_root,
                            range.startContainer, range.startOffset);
  const endCaret = makeDLoc(editor.data_root,
                          range.endContainer, range.endOffset);

  const cutRet = editor.data_updater.cut(startCaret, endCaret);
  editor.setDataCaret(cutRet[0]);
  insertRef(editor, data);
}

const NESTING_MODAL_KEY = "btw_mode.btw-tr.nesting_modal";
function getNestingModal(editor: Editor): Modal {
  let nestingModal = editor.getModeData(NESTING_MODAL_KEY);
  if (nestingModal) {
    return nestingModal;
  }

  nestingModal = editor.makeModal();
  nestingModal.setTitle("Invalid nesting");
  nestingModal.setBody("<p>In this part of the article, you cannot embed one " +
                       "language into another.</p>");
  nestingModal.addButton("Ok", true);
  editor.setModeData(NESTING_MODAL_KEY, nestingModal);

  return nestingModal;
}

function setLanguageHandler(this: SetTextLanguageTr, editor: Editor,
                            data: TransformationData): void {
  const range = editor.getDataSelectionRange();

  // We don't do anything if the range is collapsed.
  if (!range || range.collapsed) {
    return;
  }

  if (!domutil.isWellFormedRange(range)) {
    editor.straddling_modal.modal();
    throw new AbortTransformationException(
      "range is not well-formed");
  }

  const langCode = btwUtil.languageToLanguageCode(data.language);
  const selector = "foreign";
  const dataSelector = domutil.toGUISelector(selector);

  const container = range.startContainer;
  const cl = closest(container, dataSelector, editor.data_root);
  if (cl) {
    this.nestingModal.modal();
    throw new AbortTransformationException(
      "the range does not wholly contain the contents of a parent " +
        "foreign language element");
  }

  const ename = editor.mode.getAbsoluteResolver().resolveName("foreign");
  const foreign = makeElement(container.ownerDocument,
                            ename.ns, "foreign", { "xml:lang": langCode });
  const cutRet = editor.data_updater.cut(
    makeDLoc(editor.data_root, range.startContainer, range.startOffset),
    makeDLoc(editor.data_root, range.endContainer, range.endOffset));
  const cutNodes = cutRet[1];
  for (const el of cutNodes) {
    foreign.appendChild(el);
  }
  editor.data_updater.insertAt(cutRet[0], foreign);
  range.selectNodeContents(foreign);
  editor.setDataSelectionRange(range);
}

export class SetTextLanguageTr extends Transformation {
  nestingModal: Modal;

  constructor(editor: Editor, private readonly language: string) {
    super(editor, undefined, `Set language to ${language}`, language, undefined,
          true, setLanguageHandler);
    this.nestingModal = getNestingModal(editor);
  }

  execute(data: TransformationData = {}): void {
    data.language = this.language;
    super.execute(data);
  }
}

const REMOVE_MIXED_MODAL_KEY = "btw_mode.btw-tr.remove_mixed_modal";
function getRemoveMixedModal(editor: Editor): Modal {
  let removeMixedModal = editor.getModeData(REMOVE_MIXED_MODAL_KEY);
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

function removeMixedHandler(editor: Editor, _data: TransformationData): void {
  const range = editor.getDataSelectionRange();

  // Do nothing if we don't have a range.
  if (!range || range.collapsed) {
    return;
  }

  if (!domutil.isWellFormedRange(range)) {
    editor.straddling_modal.modal();
    throw new AbortTransformationException("range is not well-formed");
  }

  const cutRet = editor.data_updater.cut(
    makeDLoc(editor.data_root, range.startContainer, range.startOffset),
    makeDLoc(editor.data_root, range.endContainer, range.endOffset));
  let newText = "";
  const cutNodes = cutRet[1];
  for (const el of cutNodes) {
    newText += el.textContent;
  }
  const textNode = range.startContainer.ownerDocument.createTextNode(newText);

  if (editor.validator.speculativelyValidate(cutRet[0], textNode)) {
    getRemoveMixedModal(editor).modal();
    throw new AbortTransformationException("result would be invalid");
  }

  const insertRet = editor.data_updater.insertText(cutRet[0], newText);
  if (insertRet[0]) {
    range.setStart(insertRet[0], cutRet[0].offset);
    range.setEnd(insertRet[0], range.startOffset as number + newText.length);
  }
  else {
    range.setStart(insertRet[1], 0);
    range.setEnd(insertRet[1], newText.length);
  }

  editor.setDataSelectionRange(range);
}

export class RemoveMixedTr extends Transformation {
  constructor(editor: Editor) {
    super(editor, "delete", "Remove mixed-content markup",
          "Remove mixed-content markup", "<i class='fa fa-eraser'></i>", true,
          removeMixedHandler);
  }
}

export function makeReplaceNone(editor: Editor,
                                replacedWith: string): Transformation {
  return new Transformation(
    editor, "add", `Create new ${replacedWith}`,
    (trEditor, _data) => {
      const caret = trEditor.getDataCaret();
      const parent = caret.node;

      // This is the node that contains btw:none.
      const grandparent = parent.parentNode;

      const actions = trEditor.mode.getContextualActions("insert", replacedWith,
                                                         grandparent, 0);
      actions[0].execute({
        move_caret_to: makeDLoc(trEditor.data_root, grandparent, 0),
        name: replacedWith,
      });
      trEditor.data_updater.removeNode(parent);
    });
}

export function replaceSemanticFields(editor: Editor,
                                      data: TransformationData): void {
  // XXX const editor = this._editor;
  const dataCaret = editor.getDataCaret(true);
  const guiCaret = editor.fromDataLocation(dataCaret);
  const guiSfsContainer = domutil.closestByClass(guiCaret.node,
                                                 "btw:semantic-fields",
                                                 editor.gui_root);
  if (!guiSfsContainer) {
    throw new Error("unable to acquire btw:semantic-fields");
  }

  const sfsContainer = editor.toDataNode(guiSfsContainer);
  const sfsParent = sfsContainer.parentNode;
  const sfsIndex = _indexOf.call(sfsParent.childNodes, sfsContainer);
  // Remove the container from the tree.
  editor.data_updater.removeNode(sfsContainer);

  // and manipulate it off-line.
  while (sfsContainer.firstChild) {
    sfsContainer.removeChild(sfsContainer.firstChild);
  }

  const doc = sfsContainer.ownerDocument;
  const newPaths = data.newPaths;
  const ename = editor.mode.getAbsoluteResolver().resolveName("btw:sf");

  for (const path of newPaths) {
    const sf = makeElement(doc, ename.ns, "btw:sf");
    sf.textContent = path;
    sfsContainer.appendChild(sf);
  }

  // Finally, reintroduce it to the data tree.
  editor.data_updater.insertNodeAt(sfsParent, sfsIndex, sfsContainer);
  editor.setDataCaret(sfsContainer, 0);
}
