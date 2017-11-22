/**
 * Actions for BTWMode.
 * @author Louis-Dominique Dubeau
 */
import * as $ from "jquery";
import * as _ from "lodash";
// Yep, Bloodhound is provided by typeahead.
import * as Bloodhound from "typeahead";

import { Action } from "wed/action";
import * as domutil from "wed/domutil";
import * as util from "wed/util";

import { biblDataToReferenceText, biblSuggestionSorter, BibliographicalItem,
         isPrimarySource, Item, PrimarySource } from "./bibliography";
import { BibliographicalInfo } from "./btw-mode";
import * as btwUtil from "./btw-util";
import * as SFEditor from "./semantic_field_editor/app";

// TEMPORARY TYPE DEFINITIONS
/* tslint:disable: no-any */
type Editor = any;
type Modal = any;
/* tslint:enable: no-any */
// END TEMPORARY TYPE DEFINITIONS

export class SensePtrDialogAction extends Action {
  /* from parent */
  private _editor: Editor;
  /* END from parent */

  // tslint:disable-next-line:no-any
  constructor(...args: any[]) {
    super(...args);
  }

  // tslint:disable-next-line:no-any
  execute(data: any): void {
    const editor = this._editor;

    const doc = editor.gui_root.ownerDocument;
    const senses = editor.gui_root.querySelectorAll(
      util.classFromOriginalName("btw:sense"));
    const labels: Element[] = [];
    const radios: Element[] = [];
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < senses.length; ++i) {
      const sense = senses[i];
      let dataNode = $.data(sense, "wed_mirror_node");
      const termNodes = btwUtil.termsForSense(sense);
      const terms: string[] = [];
      // tslint:disable-next-line:prefer-for-of
      for (let tix = 0; tix < termNodes.length; ++tix) {
        terms.push($.data(termNodes[tix], "wed_mirror_node").textContent);
      }
      const senseLabel = editor.decorator.refmans.getSenseLabel(sense);

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
        const subsenseLabel =
          editor.decorator.refmans.getSubsenseLabel(subsense);
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

    const hyperlinkModal = editor.mode.hyperlinkModal;
    const primary = hyperlinkModal.getPrimary()[0];
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
        const id = body.querySelector("input[type='radio']:checked")
              .nextElementSibling.getAttribute("data-wed-id");
        data.target = id;
        editor.mode.insertPtrTr.execute(data);
      }
    });
  }
}

export class ExamplePtrDialogAction extends Action {
  /* from parent */
  private _editor: Editor;
  /* END from parent */

  // tslint:disable-next-line:no-any
  constructor(...args: any[]) {
    super(...args);
  }

  // tslint:disable-next-line:no-any
  execute(data: any): void {
    const editor = this._editor;

    const doc = editor.gui_root.ownerDocument;
    const examples = editor.gui_root.querySelectorAll(domutil.toGUISelector(
      "btw:example, btw:example-explained"));
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

      let abbr = example.querySelector(util.classFromOriginalName("ref"));
      // We skip those examples that do not have a ref in them yet,
      // as links to them are meaningless.
      if (!abbr) {
        continue;
      }

      abbr = abbr.cloneNode(true);
      child = abbr.firstElementChild;
      while (child) {
        const next = child.nextElementSibling;
        if (child.classList.contains("_gui")) {
          abbr.removeChild(child);
        }
        child = next;
      }

      const span = doc.createElement("span");
      span.setAttribute("data-wed-id", example.id);
      span.textContent =
        ` ${abbr ? `${abbr.textContent} ` : ""}${cit.textContent}`;

      const radio = doc.createElement("input");
      radio.type = "radio";
      radio.name = "example";

      const div = doc.createElement("div");
      div.appendChild(radio);
      div.appendChild(span);

      labels.push(div);
      radios.push(radio);
    }

    const hyperlinkModal = editor.mode.hyperlinkModal;
    const primary = hyperlinkModal.getPrimary()[0];
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
        const id = body.querySelector("input[type='radio']:checked")
              .nextElementSibling.getAttribute("data-wed-id");
        data.target = id;
        editor.mode.insertPtrTr.execute(data);
      }
    });
  }
}

const BIBL_SELECTION_MODAL_KEY = "btw-mode.btw-actions.bibl_selection_modal";
function getBiblSelectionModal(editor: Editor): Modal {
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

export class InsertBiblPtrAction extends Action {
  /* from parent */
  private _editor: Editor;
  /* END from parent */

  // tslint:disable-next-line:no-any
  constructor(...args: any[]) {
    super(...args);
  }

  // tslint:disable-next-line:no-any max-func-body-length
  execute(data: any): void {
    const editor = this._editor;
    let range = editor.getSelectionRange();

    if (range && range.collapsed) {
      range = undefined;
    }

    if (range) {
      const nodes = range.getNodes();
      let nonText = false;
      for (let i = 0; !nonText && i < nodes.length; ++i) {
        if (nodes[i].nodeType !== Node.TEXT_NODE) {
          nonText = true;
        }
      }

      // The selection must contain only text.
      if (nonText) {
        getBiblSelectionModal(this._editor).modal();
        return;
      }
    }

    const text = range && range.toString();

    const options = {
      datumTokenizer: datumTokenizer,
      queryTokenizer: nw,
      local: [],
    };

    const citedEngine = new Bloodhound(options);
    const zoteroEngine = new Bloodhound(options);

    citedEngine.sorter = biblSuggestionSorter;
    zoteroEngine.sorter = biblSuggestionSorter;

    citedEngine.initialize();
    zoteroEngine.initialize();

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
        source: citedEngine.ttAdapter(),
        templates: {
          header: "Cited",
          suggestion: renderSuggestion,
          empty: " does not contain a match.",
        },
      }, {
        name: "zotero",
        displayKey: biblDataToReferenceText,
        source: zoteroEngine.ttAdapter(),
        templates: {
          header: "Zotero",
          suggestion: renderSuggestion,
          empty: " does not contain a match.",
        },
      }],
    };

    const pos = editor.computeContextMenuPosition(undefined, true);
    const ta = editor.displayTypeaheadPopup(
      pos.left, pos.top, 600, "Reference",
      taOptions,
      (obj) => {
        if (!obj) {
          return;
        }

        data.target = obj.abstract_url;
        if (range) {
          editor.mode.replaceSelectionWithRefTr.execute(data);
        }
        else {
          editor.mode.insertRefTr.execute(data);
        }
      });

    editor.mode.getBibliographicalInfo().then((info: BibliographicalInfo) => {
      const allValues: string[] = [];
      const keys = Object.keys(info);
      for (const key of keys) {
        allValues.push(info[key]);
      }

      const citedValues: string[] = [];
      const refs = editor.gui_root.querySelectorAll("._real.ref");
      // tslint:disable-next-line:prefer-for-of
      for (let refIx = 0; refIx < refs.length; ++refIx) {
        const ref = refs[refIx];
        const origTarget = ref.getAttribute(util.encodeAttrName("target"));
        if (origTarget.lastIndexOf("/bibliography/", 0) !== 0) {
          continue;
        }

        citedValues.push(info[origTarget]);
      }

      zoteroEngine.add(allValues);
      citedEngine.add(citedValues);
      if (range) {
        ta.setValue(text);
      }
      ta.hideSpinner();
    });
  }
}

const EDIT_SF_MODAL_KEY = "btw-mode.btw-actions.edit_sf_modal";
function getEditSemanticFieldModal(editor: Editor): Modal {
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

export class EditSemanticFieldsAction extends Action {
  /* from parent */
  private _editor: Editor;
  /* END from parent */

  // tslint:disable-next-line:no-any
  constructor(...args: any[]) {
    super(...args);
  }

  // tslint:disable-next-line:no-any
  execute(data: any): void {
    const editor = this._editor;
    const dataCaret = editor.getDataCaret(true);
    const guiCaret = editor.fromDataLocation(dataCaret);
    const guiSfsContainer =
      domutil.closestByClass(guiCaret.node, "btw:semantic-fields",
                             editor.gui_root);
    if (!guiSfsContainer) {
      throw new Error("unable to acquire btw:semantic-fields");
    }

    const sfsContainer = editor.toDataNode(guiSfsContainer);
    const sfs = domutil.dataFindAll(sfsContainer, "btw:sf");

    const paths = sfs.map((sf) => sf.textContent);

    const modal = getEditSemanticFieldModal(editor);
    const mode = editor.mode;
    const fetcher = editor.decorator.sfFetcher;

    const fieldToPath = (f) => f.get("path");

    let sfEditor;
    const primary = modal.getPrimary()[0];
    primary.classList.add("disabled");
    modal.setBody("<i class='fa fa-spinner fa-2x fa-spin'></i>");

    const $modalTop = modal.getTopLevel();
    const body = $modalTop[0].getElementsByClassName("modal-body")[0];
    const content = $modalTop[0].getElementsByClassName("modal-content")[0];
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

        data.newPaths = sfEditor.getChosenFields().map(fieldToPath);
        editor.mode.replaceSemanticFields.execute(data);
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
