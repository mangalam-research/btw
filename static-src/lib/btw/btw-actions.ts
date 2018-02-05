/**
 * Actions for BTWMode.
 * @author Louis-Dominique Dubeau
 */
import * as Bloodhound from "bloodhound";
import * as $ from "jquery";
import * as _ from "lodash";

import { Action, domtypeguards, domutil, EditorAPI, gui, transformation,
         util } from "wed";
import isText = domtypeguards.isText;
import TransformationData = transformation.TransformationData;
import Modal = gui.modal.Modal;
import TypeaheadPopup = gui.typeaheadPopup.TypeaheadPopup;

import { biblDataToReferenceText, BibliographicalItem, biblSuggestionSorter,
         isPrimarySource, Item, PrimarySource } from "./bibliography";
import { BTWDecorator } from "./btw-decorator";
import { BibliographicalInfo, Mode } from "./btw-mode";
import * as btwUtil from "./btw-util";
import * as SFEditor from "./semantic_field_editor/app";

export class SensePtrDialogAction extends Action<TransformationData> {
  execute(data: TransformationData): void {
    const editor = this.editor;

    const dataCaret = editor.caretManager.getDataCaret(true)!;
    const mode = editor.modeTree.getMode(dataCaret.node);
    if (!(mode instanceof Mode)) {
      throw new Error("expected BTW mode");
    }

    const decorator = editor.modeTree.getDecorator(dataCaret.node);
    if (!(decorator instanceof BTWDecorator)) {
      throw new Error("our decorator must be a BTWDecorator");
    }

    const doc = editor.guiRoot.ownerDocument;
    const mappings = mode.getAbsoluteNamespaceMappings();
    const senses = editor.guiRoot.querySelectorAll(
      util.classFromOriginalName("btw:sense", mappings));
    const labels: Element[] = [];
    const radios: Element[] = [];
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < senses.length; ++i) {
      const sense = senses[i];
      let dataNode = $.data(sense, "wed_mirror_node");
      const termNodes = btwUtil.termsForSense(sense, mappings);
      const terms: string[] = [];
      // tslint:disable-next-line:prefer-for-of
      for (let tix = 0; tix < termNodes.length; ++tix) {
        terms.push($.data(termNodes[tix], "wed_mirror_node").textContent);
      }
      const senseLabel = decorator.refmans.getSenseLabel(sense);

      let span = doc.createElement("span");
      span.textContent = ` [${senseLabel}] ${terms.join(", ")}`;
      span.setAttribute("data-wed-id", sense.id);

      let radio = doc.createElement("input");
      radio.type = "radio";
      radio.name = "sense";

      let div = doc.createElement("div");
      div.appendChild(radio);
      div.appendChild(span);

      labels.push(div);
      radios.push(radio);

      const subsenses = domutil.childrenByClass(sense, "btw:subsense");
      for (const subsense of subsenses) {
        dataNode = $.data(subsense, "wed_mirror_node");
        const subsenseLabel = decorator.refmans.getSubsenseLabel(subsense);
        let child = dataNode.firstElementChild;
        let explanation;
        while (child) {
          if (child.tagName === "btw:explanation") {
            explanation = child;
            break;
          }
          child = child.nextElementSibling;
        }

        span = doc.createElement("span");
        span.textContent = ` [${subsenseLabel}] ${explanation.textContent}`;
        span.setAttribute("data-wed-id", subsense.id);

        radio = doc.createElement("input");
        radio.type = "radio";
        radio.name = "sense";

        div = doc.createElement("div");
        div.appendChild(radio);
        div.appendChild(span);

        labels.push(div);
        radios.push(radio);
      }
    }

    const hyperlinkModal = mode.hyperlinkModal;
    const primary = hyperlinkModal.getPrimary()[0] as HTMLButtonElement;
    const body = doc.createElement("div");
    for (const label of labels) {
      body.appendChild(label);
    }
    $(radios).on("click.wed", () => {
      primary.disabled = false;
      primary.classList.remove("disabled");
    });
    primary.disabled = true;
    primary.classList.add("disabled");
    hyperlinkModal.setBody(body);
    hyperlinkModal.modal(() => {
      const clicked = hyperlinkModal.getClickedAsText();
      if (clicked === "Insert") {
        const id = body.querySelector("input[type='radio']:checked")!
              .nextElementSibling!.getAttribute("data-wed-id")!;
        mode.insertPtrTr.execute({ ...data, target: id });
      }
    });
  }
}

export class ExamplePtrDialogAction extends Action<TransformationData> {
  execute(data: TransformationData): void {
    const editor = this.editor;

    const dataCaret = editor.caretManager.getDataCaret(true)!;
    const mode = editor.modeTree.getMode(dataCaret.node);
    if (!(mode instanceof Mode)) {
      throw new Error("expected BTW mode");
    }

    const doc = editor.guiRoot.ownerDocument;
    const mappings = mode.getAbsoluteNamespaceMappings();
    const examples =
      editor.guiRoot.querySelectorAll(domutil.toGUISelector(
        "btw:example, btw:example-explained", mappings));
    const labels: Element[] = [];
    const radios: Element[] = [];
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < examples.length; ++i) {
      const example = examples[i];
      const dataNode = $.data(example, "wed_mirror_node");
      let child = dataNode.firstElementChild;
      let cit;
      while (child) {
        if (child.tagName === "btw:cit") {
          cit = child;
          break;
        }
        child = child.nextElementSibling;
      }

      const abbr = example.querySelector(util.classFromOriginalName("ref",
                                                                    mappings));
      // We skip those examples that do not have a ref in them yet, as links to
      // them are meaningless.
      if (abbr === null) {
        continue;
      }

      const abbrCopy = abbr.cloneNode(true) as Element;
      child = abbrCopy.firstElementChild;
      while (child) {
        const next = child.nextElementSibling;
        if (child.classList.contains("_gui")) {
          abbrCopy.removeChild(child);
        }
        child = next;
      }

      const span = doc.createElement("span");
      span.setAttribute("data-wed-id", example.id);
      span.textContent = ` ${abbrCopy.textContent} ${cit.textContent}`;

      const radio = doc.createElement("input");
      radio.type = "radio";
      radio.name = "example";

      const div = doc.createElement("div");
      div.appendChild(radio);
      div.appendChild(span);

      labels.push(div);
      radios.push(radio);
    }

    const hyperlinkModal = mode.hyperlinkModal;
    const primary = hyperlinkModal.getPrimary()[0] as HTMLButtonElement;
    const body = doc.createElement("div");
    for (const label of labels) {
      body.appendChild(label);
    }

    $(radios).on("click.wed", () => {
      primary.disabled = false;
      primary.classList.remove("disabled");
    });
    primary.disabled = true;
    primary.classList.add("disabled");
    hyperlinkModal.setBody(body);
    hyperlinkModal.modal(() => {
      const clicked = hyperlinkModal.getClickedAsText();
      if (clicked === "Insert") {
        const id = body.querySelector("input[type='radio']:checked")!
              .nextElementSibling!.getAttribute("data-wed-id")!;
        mode.insertPtrTr.execute({ ...data, target: id });
      }
    });
  }
}

const BIBL_SELECTION_MODAL_KEY = "btw-mode.btw-actions.bibl_selection_modal";
function getBiblSelectionModal(editor: EditorAPI): Modal {
  let modal = editor.getModeData(BIBL_SELECTION_MODAL_KEY);
  if (modal) {
    return modal;
  }

  modal = editor.makeModal();
  modal.setTitle("Invalid Selection");
  modal.setBody("<p>The selection should contain only text. The current " +
                "selection contains elements.</p>");
  modal.addButton("Ok", true);
  editor.setModeData(BIBL_SELECTION_MODAL_KEY, modal);

  return modal;
}

// The nonword tokenizer provided by bloodhound.
const nw = Bloodhound.tokenizers.nonword;
function tokenizeItem(item: Item): string {
  return nw(item.title).concat(nw(item.creators), nw(item.date));
}

function tokenizePS(ps: PrimarySource): string {
  return tokenizeItem(ps.item).concat(nw(ps.reference_title));
}

function datumTokenizer(datum: BibliographicalItem): string {
  return isPrimarySource(datum) ? tokenizePS(datum) : tokenizeItem(datum);
}

function renderSuggestion(obj: BibliographicalItem): string {
  let rendered = "";
  let item: Item;
  if (isPrimarySource(obj)) {
    rendered = `${obj.reference_title} --- `;
    item = obj.item;
  }
  else {
    item = obj;
  }

  const creators = item.creators;
  let firstCreator = "***ITEM HAS NO CREATORS***";
  if (creators != null && creators !== "") {
    firstCreator = creators.split(",")[0];
  }

  rendered += `${firstCreator}, ${item.title}`;
  const date = item.date;
  if (date != null && date !== "") {
    rendered += `, ${date}`;
  }

  return `<p><span style='white-space: nowrap'>${rendered}</span></p>`;
}

function makeEngine(options: {}): Bloodhound {
  const engine = new Bloodhound(options);
  engine.sorter = biblSuggestionSorter;
  engine.initialize();
  return engine;
}

export class InsertBiblPtrAction extends Action<{}> {
  execute(data: {}): void {
    const editor = this.editor;
    const dataCaret = editor.caretManager.getDataCaret(true)!;
    const mode = editor.modeTree.getMode(dataCaret.node);
    if (!(mode instanceof Mode)) {
      throw new Error("expected BTW mode");
    }

    let sel = editor.caretManager.sel;
    if (sel !== undefined && sel.collapsed) {
      sel = undefined;
    }

    let range: Range | undefined;
    if (sel !== undefined) {
      // The selection must contain only text.
      let textOnly = false;

      // To contain only text, it must necessarily be well-formed.
      if (sel.wellFormed) {
        const pointedAnchor = sel.anchor.pointedNode;
        const pointedFocus = sel.focus.pointedNode;
        // If it is well-formed, then pointedAnchor and pointedFocus are
        // necessarily siblings.
        // tslint:disable-next-line:prefer-const
        let { start, end } : { start: Node | null | undefined,
                               end: Node | undefined } =
          sel.anchor.compare(sel.focus) < 0 ?
          { start: pointedAnchor, end: pointedFocus } :
          { start: pointedFocus, end: pointedAnchor };

        // It is not possible for start to be undefined. In general, yes. But we
        // are dealing with a well-formed selection. For start to be undefined,
        // it would have to point past the last child of an element, and this
        // would entail that the selection is not well-formed.
        if (start === undefined) {
          throw new Error("unexpected undefined start");
        }

        textOnly = true;
        // Note that if end is undefined, we'll just iterate until we run out of
        // siblings, which is what we want.
        while (textOnly && start !== null && start !== end) {
          textOnly = isText(start);
          start = start.nextSibling;
        }
      }

      if (!textOnly) {
        getBiblSelectionModal(this.editor).modal();
        return;
      }

      range = sel.range;
    }

    const options = { datumTokenizer, queryTokenizer: nw, local: [] };

    const citedEngine = makeEngine(options);
    const zoteroEngine = makeEngine(options);

    const ta = this.makeTypeaheadPopup(citedEngine, zoteroEngine, editor,
                                       range, mode);

    // tslint:disable-next-line:no-floating-promises
    mode.getBibliographicalInfo().then((info: BibliographicalInfo) => {
      const allValues: BibliographicalItem[] = [];
      for (const key of Object.keys(info)) {
        allValues.push(info[key]);
      }

      const citedValues: BibliographicalItem[] = [];
      const refs = editor.guiRoot.querySelectorAll("._real.ref");
      // tslint:disable-next-line:prefer-for-of
      for (let refIx = 0; refIx < refs.length; ++refIx) {
        const ref = refs[refIx];
        const origTarget = ref.getAttribute(util.encodeAttrName("target"))!;
        if (origTarget.lastIndexOf("/bibliography/", 0) !== 0) {
          continue;
        }

        citedValues.push(info[origTarget]);
      }

      zoteroEngine.add(allValues);
      citedEngine.add(citedValues);
      if (range !== undefined) {
        ta.setValue(range.toString());
      }
      ta.hideSpinner();
    });
  }

  private makeTypeaheadPopup(citedEngine: Bloodhound, zoteroEngine: Bloodhound,
                             editor: EditorAPI, range: Range | undefined,
                             mode: Mode): TypeaheadPopup {
    const taOptions = {
      options: {
        autoselect: true,
        hint: true,
        highlight: true,
        minLength: 1,
      },
      datasets: [{
        name: "cited",
        displayKey: biblDataToReferenceText,
        source: citedEngine,
        templates: {
          header: "Cited",
          suggestion: renderSuggestion,
          empty: "Cited does not contain a match.",
        },
      }, {
        name: "zotero",
        displayKey: biblDataToReferenceText,
        source: zoteroEngine,
        templates: {
          header: "Zotero",
          suggestion: renderSuggestion,
          empty: "Zotero does not contain a match.",
        },
      }],
    };

    return editor.editingMenuManager.setupTypeaheadPopup(
      600,
      "Reference",
      taOptions,
      (obj: BibliographicalItem) => {
        if (obj == null) {
          return;
        }
        const newData = { target: obj.abstract_url };
        if (range !== undefined) {
          mode.replaceSelectionWithRefTr.execute(newData);
        }
        else {
          mode.insertRefTr.execute(newData);
        }
      }, undefined, true);
  }
}

const EDIT_SF_MODAL_KEY = "btw-mode.btw-actions.edit_sf_modal";
function getEditSemanticFieldModal(editor: EditorAPI): Modal {
  let modal = editor.getModeData(EDIT_SF_MODAL_KEY);
  if (modal) {
    return modal;
  }

  modal = editor.makeModal({
    resizable: true,
    draggable: true,
  });
  modal.setTitle("Edit Semantic Fields");
  modal.addButton("Commit", true);
  modal.addButton("Cancel");
  const body = modal.getTopLevel()[0].getElementsByClassName("modal-body")[0];
  body.classList.add("sf-editor-modal-body");
  body.style.overflowY = "hidden";
  editor.setModeData(EDIT_SF_MODAL_KEY, modal);

  return modal;
}

export class EditSemanticFieldsAction extends Action<{}> {
  execute(data: {}): void {
    const editor = this.editor;
    const dataCaret = editor.caretManager.getDataCaret(true)!;
    const guiCaret = editor.caretManager.fromDataLocation(dataCaret)!;
    const guiSfsContainer =
      domutil.closestByClass(guiCaret.node, "btw:semantic-fields",
                             editor.guiRoot);
    if (guiSfsContainer === null) {
      throw new Error("unable to acquire btw:semantic-fields");
    }

    const mode = editor.modeTree.getMode(dataCaret.node);
    if (!(mode instanceof Mode)) {
      throw new Error("expected BTW mode");
    }

    const decorator = editor.modeTree.getDecorator(dataCaret.node);
    if (!(decorator instanceof BTWDecorator)) {
      throw new Error("our decorator must be a BTWDecorator");
    }

    const fetcher = decorator.sfFetcher;

    const sfsContainer = editor.toDataNode(guiSfsContainer) as Element;
    const sfs = domutil.dataFindAll(sfsContainer, "btw:sf",
                                    mode.getAbsoluteNamespaceMappings());

    const paths = sfs.map((sf) => sf.textContent!);

    const modal = getEditSemanticFieldModal(editor);

    const fieldToPath = (f) => f.get("path");

    let sfEditor;
    const primary = modal.getPrimary()[0];
    primary.classList.add("disabled");
    modal.setBody("<i class='fa fa-spinner fa-2x fa-spin'></i>");

    const $modalTop = modal.getTopLevel();
    const body =
      $modalTop[0].getElementsByClassName("modal-body")[0] as HTMLElement;
    const content =
      $modalTop[0].getElementsByClassName("modal-content")[0] as HTMLElement;
    const header = $modalTop[0].getElementsByClassName("modal-header")[0];
    const footer = $modalTop[0].getElementsByClassName("modal-footer")[0];

    $modalTop.on("shown.bs.modal.modal", () => {
      // Once we have shown the modal we set its height to the max-height so
      // that the children of the body can use height percentages.
      content.style.height = content.style.maxHeight;
      const contentHeight = content.getBoundingClientRect().height;
      body.style.height =
        `${contentHeight - header.getBoundingClientRect().height -
footer.getBoundingClientRect().height}px`;
    });

    modal.modal(() => {
      const clicked = modal.getClickedAsText();
      if (clicked === "Commit") {
        if (!sfEditor) {
          throw new Error("modal dismissed with primary button " +
                          "while sfEditor is non-existent");
        }

        mode.replaceSemanticFields.execute(
          { newPaths: sfEditor.getChosenFields().map(fieldToPath) });
      }
    });

    fetcher.fetch(paths).then((resolved) => {
      const fields = _.values(resolved);

      // We grab the list of paths from the resolved fields because initially we
      // may have unknown fields, and the list of resolve fields may be shorter
      // than ``paths``.
      // Reminder: fields are plain old JS objects.
      const initialPaths = fields.map((x) => x.path);

      // Clear it before the editor is started.
      modal.setBody("");
      sfEditor = new SFEditor({
        container: body,
        fields: fields,
        fetcher: fetcher,
        searchUrl: mode.semanticFieldFetchUrl,
      });
      sfEditor.start();

      sfEditor.on("sf:chosen:change", () => {
        const newPaths = sfEditor.getChosenFields().map(fieldToPath);
        const method = _.isEqual(initialPaths, newPaths) ? "add" : "remove";
        primary.classList[method]("disabled");
      });
    });
  }
}
