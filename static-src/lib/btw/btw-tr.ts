/**
 * Transformations for BTWMode.
 * @author Louis-Dominique Dubeau
 */
import * as $ from "jquery";

import { convert, DLoc, domutil, EditorAPI, exceptions, gui, transformation,
       } from "wed";

import AbortTransformationException = exceptions.AbortTransformationException;
import makeElement = transformation.makeElement;
import Transformation = transformation.Transformation;
import TransformationData = transformation.TransformationData;
import Modal = gui.modal.Modal;

import { BTW_MODE_ORIGIN, languageToLanguageCode } from "./btw-util";

const closest = domutil.closest;
const makeDLoc = DLoc.makeDLoc;

const _indexOf = Array.prototype.indexOf;

export interface TargetedTransformationData extends TransformationData {
  target: string;
}

export function insertPtr(editor: EditorAPI,
                          data: TargetedTransformationData): void {
  const caret = editor.caretManager.getDataCaret()!;
  let parent = caret.node;
  const index = caret.offset;

  // The data.target value is the wed ID target of the ptr. We must find this
  // element and add a data ID.
  const target = editor.guiRoot.ownerDocument!.getElementById(data.target)!;
  const dataId = data.target.slice(4);
  target.setAttribute(convert.encodeAttrName("xml:id"), dataId);
  (domutil.mustGetMirror(target) as Element).setAttributeNS(
    // tslint:disable-next-line:no-http-string
    "http://www.w3.org/XML/1998/namespace", "xml:id", dataId);

  const mode = editor.modeTree.getMode(parent);
  const ename = mode.getAbsoluteResolver().resolveName("ptr")!;

  const ptr = makeElement(parent.ownerDocument!,
                          ename.ns, "ptr", { target: `#${dataId}` });
  editor.dataUpdater.insertAt(parent, index, ptr);

  // The original parent and index information are no necessarily representative
  // because insertAt can do quite a lot of things to insert the node.
  parent = ptr.parentNode!;
  editor.caretManager.setCaret(parent, _indexOf.call(parent.childNodes, ptr));
}

export function insertRef(editor: EditorAPI,
                          data: TargetedTransformationData): void {
  const caret = editor.caretManager.getDataCaret()!;
  const parent = caret.node;
  const index = caret.offset;

  const mode = editor.modeTree.getMode(parent);
  const ename = mode.getAbsoluteResolver().resolveName("ref")!;
  const ptr = makeElement(parent.ownerDocument!, ename.ns, "ref",
                          { target: data.target });
  editor.dataUpdater.insertAt(parent, index, ptr);
  const guiNode = editor.caretManager.fromDataLocation(ptr, 0)!.node;

  // We must immediately set the caret because it is likely the old caret is no
  // longer valid.
  editor.caretManager.setCaret(guiNode, 0);

  // We do this because if we set the caret immediately, it gets clobbered by
  // the later refreshing of the ref element.
  $(guiNode).one("wed-refresh", () => {
    editor.caretManager.setCaret(
      guiNode,
      _indexOf.call(guiNode.childNodes,
                    domutil.childByClass(guiNode, "_ref_abbr")) + 1);
  });
}

export function replaceSelectionWithRef(editor: EditorAPI,
                                        data: TargetedTransformationData):
void {
  const selection = editor.caretManager.sel!;

  if (!selection.wellFormed) {
    throw new Error("malformed selection");
  }

  const [startCaret, endCaret] = selection.asDataCarets()!;
  const cutRet = editor.dataUpdater.cut(startCaret, endCaret);
  editor.caretManager.setCaret(cutRet[0]);
  insertRef(editor, data);
}

const NESTING_MODAL_KEY = "btw_mode.btw-tr.nesting_modal";
function getNestingModal(editor: EditorAPI): Modal {
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

export interface LanguageTransformationData extends TransformationData {
  language: string;
}

function setLanguageHandler(this: SetTextLanguageTr, editor: EditorAPI,
                            data: LanguageTransformationData): void {
  const selection = editor.caretManager.sel;

  // We don't do anything if the selection is collapsed.
  if (selection === undefined || selection.collapsed) {
    return;
  }

  if (!selection.wellFormed) {
    editor.modals.getModal("straddling").modal();
    throw new AbortTransformationException("selection is not well-formed");
  }

  const langCode = languageToLanguageCode(data.language);
  const [start, end] = selection.asDataCarets()!;
  const container = start.node;
  const cl = closest(container, "foreign", editor.dataRoot);
  if (cl !== null) {
    this.nestingModal.modal();
    throw new AbortTransformationException(
      "the selection does not wholly contain the contents of a parent " +
        "foreign language element");
  }

  const mode = editor.modeTree.getMode(start.node);
  const ename = mode.getAbsoluteResolver().resolveName("foreign")!;
  const foreign = makeElement(container.ownerDocument!,
                              ename.ns, "foreign", { "xml:lang": langCode });
  const cutRet = editor.dataUpdater.cut(start, end);
  const cutNodes = cutRet[1];
  for (const el of cutNodes) {
    foreign.appendChild(el);
  }
  editor.dataUpdater.insertAt(cutRet[0], foreign);
  editor.caretManager.setRange(foreign, 0, foreign, foreign.childNodes.length);
}

export class SetTextLanguageTr
extends Transformation<LanguageTransformationData> {
  nestingModal: Modal;

  constructor(editor: EditorAPI, private readonly language: string) {
    super(BTW_MODE_ORIGIN, editor, "transform",
          `Set language to ${language}`,
          setLanguageHandler, {
            abbreviatedDesc: language,
            needsInput: true,
            icon: "",
          });
    this.nestingModal = getNestingModal(editor);
  }

  execute(data: LanguageTransformationData): void {
    // Don't execute if there's no selection.
    const selection = this.editor.caretManager.sel;
    if (selection !== undefined && !selection.collapsed) {
      data.language = this.language;
      super.execute(data);
    }
  }
}

export function makeReplaceNone(editor: EditorAPI,  replacedWith: string):
Transformation {
  return new Transformation(
    BTW_MODE_ORIGIN, editor, "add", `Create new ${replacedWith}`,
    (trEditor, _data) => {
      const caret = trEditor.caretManager.getDataCaret()!;
      const parent = caret.node;

      // This is the node that contains btw:none.
      const grandparent = parent.parentNode!;

      const mode = trEditor.modeTree.getMode(caret.node);
      const actions = mode.getContextualActions("insert", replacedWith,
                                                grandparent, 0);
      actions[0].execute({
        moveCaretTo: makeDLoc(trEditor.dataRoot, grandparent, 0),
        name: replacedWith,
      });
      trEditor.dataUpdater.removeNode(parent);
    });
}

export interface SemanticFieldTransformationData extends TransformationData {
  newPaths: string[];
}

export function replaceSemanticFields(editor: EditorAPI,
                                      data: SemanticFieldTransformationData):
void {
  const dataCaret = editor.caretManager.getDataCaret(true)!;
  const guiCaret = editor.caretManager.fromDataLocation(dataCaret)!;
  const guiSfsContainer = domutil.closestByClass(guiCaret.node,
                                                 "btw:semantic-fields",
                                                 editor.guiRoot);
  if (guiSfsContainer === null) {
    throw new Error("unable to acquire btw:semantic-fields");
  }

  const sfsContainer = editor.toDataNode(guiSfsContainer)!;
  const sfsParent = sfsContainer.parentNode!;
  const sfsIndex = _indexOf.call(sfsParent.childNodes, sfsContainer);
  // Remove the container from the tree.
  editor.dataUpdater.removeNode(sfsContainer);

  // and manipulate it off-line.
  while (sfsContainer.firstChild !== null) {
    sfsContainer.removeChild(sfsContainer.firstChild);
  }

  const doc = sfsContainer.ownerDocument!;
  const newPaths = data.newPaths;
  const mode = editor.modeTree.getMode(sfsContainer);
  const ename = mode.getAbsoluteResolver().resolveName("btw:sf")!;

  for (const path of newPaths) {
    const sf = makeElement(doc, ename.ns, "btw:sf");
    sf.textContent = path;
    sfsContainer.appendChild(sf);
  }

  // Finally, reintroduce it to the data tree.
  editor.dataUpdater.insertNodeAt(sfsParent, sfsIndex, sfsContainer);
  editor.caretManager.setCaret(sfsContainer, 0);
}
