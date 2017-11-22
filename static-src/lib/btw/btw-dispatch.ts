/**
 * The dispatch logic common to editing and displaying articles.
 * @author Louis-Dominique Dubeau
 */
import "bootstrap-treeview";
import * as $ from "jquery";

import { Decorator } from "wed/decorator";
import * as domutil from "wed/domutil";
import { tooltip } from "wed/gui/tooltip";
import * as util from "wed/util";

import { biblDataToReferenceText, BibliographicalItem, isPrimarySource,
         Item } from "./bibliography";
import * as btwUtil from "./btw-util";
import { IDManager } from "./id-manager";
import { SFFetcher } from "./semantic-field-fetcher";
import * as Field from "./semantic_field_editor/models/field";
import * as FieldView from "./semantic_field_editor/views/field/inline";

const WHEEL = "☸";

// TEMPORARY TYPE DEFINITIONS
/* tslint:disable: no-any */
type Editor = any;
type Meta = any;
type Mode = any;
type HeadingDecorator = any;
type WholeDocumentManager = any;
type GUIUpdater = any;
type Refman = any;
/* tslint:enable: no-any */
// END TEMPORARY TYPE DEFINITIONS

function setTitle($el: JQuery, data: Item): void {
  const creators = data.creators;
  let firstCreator = "***ITEM HAS NO CREATORS***";
  if (creators != null && creators !== "") {
    firstCreator = creators.split(",")[0];
  }

  let title = `${firstCreator}, ${data.title}`;
  const date = data.date;
  if (date != null && date !== "") {
    title += `, ${date}`;
  }

  tooltip($el, { title: title, container: "body", trigger: "hover" });
}

/**
 * This mixin is made to be used by the [[Decorator]] created for BTW's mode and
 * by [["btw_viewer".Viewer]]. It combines decoration methods that are common to
 * editing and viewing articles.
 */
export abstract class DispatchMixin {
  private readonly _inMode: boolean;

  /* Provided by the class onto which this is mixed: */
  readonly abstract _editor: Editor;
  readonly abstract meta: Meta;
  readonly abstract mode: Mode;
  readonly abstract headingDecorator: HeadingDecorator;
  readonly abstract exampleIdManager: IDManager;
  readonly abstract senseSubsenseIdManager: IDManager;
  readonly abstract refmans: WholeDocumentManager;
  readonly abstract _gui_updater: GUIUpdater;
  readonly abstract senseTooltipSelector: string;
  readonly abstract sfFetcher: SFFetcher;
  abstract languageDecorator(el: Element): void;
  abstract noneDecorator(el: Element): void;
  abstract elementDecorator(root: Element, el: Element): void;
  /* End... */

  constructor() {
    this._inMode = this instanceof Decorator;
  }

  protected dispatch(root: Element, el: Element): void {
    const klass = this.meta.getAdditionalClasses(el);
    if (klass.length) {
      el.className += ` ${klass}`;
    }

    const name = util.getOriginalName(el);
    let skipDefault = false;
    switch (name) {
    case "btw:overview":
    case "btw:sense-discrimination":
    case "btw:historico-semantical-data":
    case "btw:credits":
      this.headingDecorator.unitHeadingDecorator(el);
      break;
    case "btw:definition":
    case "btw:english-renditions":
    case "btw:english-rendition":
    case "btw:etymology":
    case "btw:contrastive-section":
    case "btw:antonyms":
    case "btw:cognates":
    case "btw:conceptual-proximates":
    case "btw:other-citations":
    case "btw:citations":
      this.headingDecorator.sectionHeadingDecorator(el);
      break;
    case "btw:semantic-fields":
      this.headingDecorator.sectionHeadingDecorator(el);
      break;
    case "btw:sf":
      this.sfDecorator(root, el);
      skipDefault = true;
      break;
    case "ptr":
      this.ptrDecorator(root, el);
      break;
    case "foreign":
      this.languageDecorator(el);
      break;
    case "ref":
      this.refDecorator(root, el);
      break;
    case "btw:example":
      this.idDecorator(root, el);
      break;
    case "btw:cit":
      this.citDecorator(root, el);
      skipDefault = true; // citDecorator calls elementDecorator
      break;
    case "btw:explanation":
      this.explanationDecorator(root, el);
      skipDefault = true; // explanationDecorator calls elementDecorator
      break;
    case "btw:none":
      this.noneDecorator(el);
      // THIS ELEMENT DOES NOT GET THE REGULAR DECORATION.
      skipDefault = true;
      break;
    default:
      break;
    }

    if (!skipDefault) {
      this.elementDecorator(root, el);
    }
  }

  _getIDManagerForRefman(refman: Refman): IDManager {
    switch (refman.name) {
    case "sense":
    case "subsense":
      return this.senseSubsenseIdManager;
    case "example":
      return this.exampleIdManager;
    default:
      throw new Error(`unexpected name: ${refman.name}`);
    }
  }

  idDecorator(_root: Element, el: Element): void {
    const refman = this.refmans.getRefmanForElement(el);
    if (refman) {
      let wedId = el.id;
      if (wedId === "") {
        const id = el.getAttribute(util.encodeAttrName("xml:id"));
        const idMan = this._getIDManagerForRefman(refman);
        wedId = `BTW-${id !== null ? id : idMan.generate()}`;
        el.id = wedId;
      }

      // We have some reference managers that don't derive from ReferenceManager
      // and thus do not have this method.
      if (refman.allocateLabel) {
        refman.allocateLabel(wedId);
      }
    }
  }

  explanationDecorator(root: Element, el: Element): void {
    let child;
    let next;
    let div; // Damn hoisting...
    // Handle explanations that are in btw:example-explained.
    if ((el.parentNode as Element).classList
        .contains("btw:example-explained")) {
      child = el.firstElementChild;
      while (child) {
        next = child.nextElementSibling;
        if (child.classList.contains("_explanation_bullet")) {
          this._gui_updater.removeNode(child);
          break; // There's only one.
        }
        child = next;
      }

      const cit = domutil.siblingByClass(el, "btw:cit");
      // If the next btw:cit element contains Pāli text.
      if (cit &&
          cit.querySelector(
            `*[${util.encodeAttrName("xml:lang")}='pi-Latn']`)) {
        div = el.ownerDocument.createElement("div");
        div.className = "_phantom _decoration_text _explanation_bullet";
        div.style.position = "absolute";
        div.style.left = "-1em";
        div.textContent = WHEEL;
        this._gui_updater.insertNodeAt(el, 0, div);
        (el as HTMLElement).style.position = "relative";
      }
      this.elementDecorator(root, el);
      return;
    }

    this.elementDecorator(root, el);
    let label;
    const parent = el.parentNode as Element;
    // Is it in a subsense?
    if (parent.classList.contains("btw:subsense")) {
      const refman = this.refmans.getSubsenseRefman(el);
      label = refman.idToSublabel(parent.id);
      child = el.firstElementChild;
      let start;
      while (child) {
        next = child.nextElementSibling;
        if (child.classList.contains("_explanation_number")) {
          this._gui_updater.removeNode(child);
        }
        else if (child.classList.contains("__start_label")) {
          start = child;
        }
        child = next;
      }

      // We want to insert it after the start label.
      div = el.ownerDocument.createElement("div");
      div.className = "_phantom _decoration_text _explanation_number " +
        "_start_wrapper'";
      div.textContent = `${label}. `;
      this._gui_updater.insertBefore(el, div,
                                     start ? start.nextSibling : el.firstChild);
    }

    this.headingDecorator.sectionHeadingDecorator(el);
  }

  citDecorator(root: Element, el: Element): void {
    this.elementDecorator(root, el);

    let ref;
    let child = el.firstElementChild;
    while (child !== null) {
      const next = child.nextElementSibling;
      if (child.classList.contains("_ref_space") ||
          child.classList.contains("_cit_bullet")) {
        this._gui_updater.removeNode(child);
      }
      else if (child.classList.contains("ref")) {
        ref = child;
      }
      child = next;
    }

    if (ref) {
      const space = el.ownerDocument.createElement("div");
      space.className = "_text _phantom _ref_space";
      space.textContent = " ";
      el.insertBefore(space, ref.nextSibling);
    }

    if (el.querySelector(`*[${util.encodeAttrName("xml:lang")}='pi-Latn']`) !==
       null) {
      const div = el.ownerDocument.createElement("div");
      div.className = "_phantom _text _cit_bullet";
      div.style.position = "absolute";
      div.style.left = "-1em";
      div.textContent = WHEEL;
      this._gui_updater.insertNodeAt(el, 0, div);
      (el as HTMLElement).style.position = "relative";
    }
  }

  ptrDecorator(root: Element, el: Element): void {
    this.linkingDecorator(root, el, true);
  }

  refDecorator(root: Element, el: Element): void {
    this.linkingDecorator(root, el, false);
  }

  // tslint:disable-next-line:cyclomatic-complexity max-func-body-length
  linkingDecorator(root: Element, el: Element, isPtr: boolean): void {
    let origTarget = el.getAttribute(util.encodeAttrName("target"));
    // XXX This should become an error one day. The only reason we need this now
    // is that some of the early test files had <ref> elements without targets.
    if (origTarget === null) {
      origTarget = "";
    }

    origTarget = origTarget.trim();

    const doc = root.ownerDocument;
    if (origTarget.lastIndexOf("#", 0) === 0) {
      // Internal target
      // Add BTW in front because we want the target used by wed.
      const targetId = origTarget.replace(/#(.*)$/, "#BTW-$1");

      const text = doc.createElement("div");
      text.className = "_text _phantom _linking_deco";
      const a = doc.createElement("a");
      a.className = "_phantom";
      a.setAttribute("href", targetId);
      text.appendChild(a);
      if (isPtr) {
        // _linking_deco is used locally to make this function idempotent
        {
          let child = el.firstElementChild;
          while (child !== null) {
            const next = child.nextElementSibling;
            if (child.classList.contains("_linking_deco")) {
              this._gui_updater.removeNode(child);
              break; // There is only one.
            }
            child = next;
          }
        }

        const refman = this.refmans.getRefmanForElement(el);

        // Find the referred element. Slice to drop the #.
        let target = doc.getElementById(targetId.slice(1));

        // An undefined or null refman can happen when first decorating the
        // document.
        let label;
        if (refman != null) {
          if (refman.name === "sense" || refman.name === "subsense") {
            label = refman.idToLabel(targetId.slice(1));
            label = label !== undefined ? `[${label}]` : undefined;
          }
          else {
            // An empty target can happen when first decorating the document.
            if (target !== null) {
              label = refman.getPositionalLabel(this._editor.toDataNode(el),
                                                this._editor.toDataNode(target),
                                                targetId.slice(1));
            }
          }
        }

        if (label === undefined) {
          label = targetId;
        }

        a.textContent = label;

        // A ptr contains only attributes, no text, so we can just append.
        const pair = this.mode.nodesAroundEditableContents(el);
        this._gui_updater.insertBefore(el, text, pair[1]);

        if (target !== null) {
          const targetName = util.getOriginalName(target);

          // Reduce the target to something sensible for tooltip text.
          if (targetName === "btw:sense") {
            const terms = target.querySelectorAll(domutil.toGUISelector(
              this.senseTooltipSelector));
            let html = "";
            for (let i = 0; i < terms.length; ++i) {
              const term = terms[i];
              html += term.innerHTML;
              if (i < terms.length - 1) {
                html += ", ";
              }
            }
            target = target.ownerDocument.createElement("div");
            // tslint:disable-next-line:no-inner-html
            target.innerHTML = html;
          }
          else if (targetName === "btw:subsense") {
            let child = target.firstElementChild;
            while (child !== null) {
              if (child.classList.contains("btw:explanation")) {
                target = child.cloneNode(true) as HTMLElement;
                break;
              }
              child = child.nextElementSibling;
            }
          }
          else if (targetName === "btw:example") {
            target = null;
          }

          if (target !== null) {
            const nodes =
              target.querySelectorAll(".head, ._gui, ._explanation_number");
            // tslint:disable-next-line:prefer-for-of
            for (let nodeIx = 0; nodeIx < nodes.length; ++nodeIx) {
              const node = nodes[nodeIx];
              node.parentNode!.removeChild(node);
            }
            tooltip($(text), { title: `<div>${target.innerHTML}</div>`,
                               html: true,
                               container: "body",
                               trigger: "hover" });
          }
        }
      }
      else {
        throw new Error("internal error: ref with unexpected target");
      }
    }
    else {
      // External target
      const biblPrefix = "/bibliography/";
      if (origTarget.lastIndexOf(biblPrefix, 0) === 0) {
        // Bibliographical reference...
        if (isPtr) {
          throw new Error("internal error: bibliographic " +
                          "reference recorded as ptr");
        }

        const targetId = origTarget;

        // It is okay to skip the tree updater for these operations.
        let child = el.firstElementChild;
        while (child !== null) {
          const next = child.nextElementSibling;
          if (child.classList.contains("_ref_abbr") ||
              child.classList.contains("_ref_paren")) {
            this._gui_updater.removeNode(child);
          }
          child = next;
        }

        const abbr = doc.createElement("div");
        abbr.className = "_text _phantom _ref_abbr";
        this._gui_updater.insertBefore(el, abbr, el.firstChild);
        const open = doc.createElement("div");
        open.className = "_phantom _decoration_text _ref_paren " +
          "_open_ref_paren _start_wrapper";
        open.textContent = "(";
        this._gui_updater.insertBefore(el, open, abbr);

        const close = doc.createElement("div");
        close.className = "_phantom _decoration_text " +
          "_ref_paren _close_ref_paren _end_wrapper";
        close.textContent = ")";
        this._gui_updater.insertBefore(el, close);

        this.fetchAndFillBiblData(targetId, el, abbr);
      }
    }
  }

  fetchAndFillBiblData(targetId: string, el: Element, abbr: Element): void {
    this.mode.getBibliographicalInfo().then((info) => {
      const data = info[targetId];
      if (data) {
        this.fillBiblData(el, abbr, data);
      }
      else {
        this._gui_updater.insertText(abbr, 0, "NON-EXISTENT");
      }

      $(el).trigger("wed-refresh");
    });
  }

  fillBiblData(el: Element, abbr: Element, data: BibliographicalItem): void {
    const $el = $(el);
    setTitle($el, isPrimarySource(data) ? data.item : data);
    this._gui_updater.insertText(abbr, 0, biblDataToReferenceText(data));
  }

  sfDecorator(root: Element, el: Element): void {
    //
    // When editing them, btw:sf contains the semantic field paths, and there
    // are no names.
    //
    // When displaying articles, the paths are in @data-wed-ref, and the btw:sf
    // elements contain the names + path of the semantic fields.
    //

    // We're already wrapped.
    if (domutil.closestByClass(el, "field-view", root)) {
      return;
    }

    const inMode = this._inMode;
    const parent = el.parentNode!;
    const before = el.previousSibling;

    let ref;
    if (!inMode) {
      const dataWedRef = el.attributes["data-wed-ref"];
      if (dataWedRef) {
        ref = el.attributes["data-wed-ref"].value;
      }

      // We do not decorate if we have no references.
      if (ref === undefined) {
        return;
      }
    }
    else {
      const dataNode = this._editor.toDataNode(el);
      ref = dataNode.textContent;
    }

    const view = new FieldView({
      // We start the view with a fake field. This will be fixed later.
      model: new Field({
        heading: "",
        path: ref,
      }),

      fetcher: this.sfFetcher,
    });
    view.render();
    // tslint:disable-next-line:no-inner-html
    view.ui.field[0].innerHTML = "";
    view.ui.field[0].appendChild(el);
    this._gui_updater.insertBefore(
      parent, view.el,
      before !== null ? before.nextSibling : parent.firstChild);

    if (inMode) {
      // When we are editing we want to fill the semantic field with its name
      // and path.
      this.sfFetcher.fetch([ref]).then((resolved) => {
        const resolvedRef = resolved[ref];
        el.textContent = (resolvedRef !== undefined) ?
          `${resolvedRef.heading_for_display} (${ref})` :
          `Unknown field (${ref})`;
      });
    }
  }
}
