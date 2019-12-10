/**
 * The dispatch logic common to editing and displaying articles.
 * @author Louis-Dominique Dubeau
 */
import "bootstrap-treeview";
import * as $ from "jquery";

import { convert, Decorator, domtypeguards, domutil, gui, labelman,
         treeUpdater } from "wed";
import LabelManager = labelman.LabelManager;
import TreeUpdater = treeUpdater.TreeUpdater;
import tooltip = gui.tooltip.tooltip;
import isElement = domtypeguards.isElement;
import getMirror = domutil.getMirror;
import mustGetMirror = domutil.mustGetMirror;

import { Metadata } from "wed/modes/generic/metadata";

import { biblDataToReferenceText, BibliographicalItem, isPrimarySource,
         Item } from "./bibliography";
import { HeadingDecorator } from "./btw-heading-decorator";
import { BibliographicalInfo } from "./btw-mode";
import { ExampleReferenceManager, WholeDocumentManager } from "./btw-refmans";
import { getOriginalNameIfPossible } from "./btw-util";
import { IDManager } from "./id-manager";
import { MappedUtil } from "./mapped-util";
import { SFFetcher } from "./semantic-field-fetcher";
import * as Field from "./semantic_field_editor/models/field";
import * as FieldView from "./semantic_field_editor/views/field/inline";

const WHEEL = "☸";

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

  tooltip($el, { title, container: "body", trigger: "hover" });
}

const ENCODED_REF_ATTR_NAME = convert.encodeAttrName("ref");

export interface DispatchEditor {
  toDataNode(node: Node): Node;
}

export interface DispatchMode {
  nodesAroundEditableContents(element: Element): [Node | null, Node | null];
  getBibliographicalInfo(): Promise<BibliographicalInfo>;
}

/**
 * This mixin is made to be used by the [[Decorator]] created for BTW's mode and
 * by [["btw_viewer".Viewer]]. It combines decoration methods that are common to
 * editing and viewing articles. If suitable, classes may use this class as a
 * base class instead of as a mixin.
 */
export abstract class DispatchMixin {
  private _inMode!: boolean;

  /* Provided by the class onto which this is mixed: */
  protected readonly abstract editor: DispatchEditor;
  protected readonly abstract mode: DispatchMode;
  protected readonly abstract metadata: Metadata;
  protected readonly abstract headingDecorator: HeadingDecorator;
  protected readonly abstract exampleIdManager: IDManager;
  protected readonly abstract senseSubsenseIdManager: IDManager;
  protected readonly abstract refmans: WholeDocumentManager;
  protected readonly abstract guiUpdater: TreeUpdater;
  protected readonly abstract senseTooltipSelector: string;
  protected readonly abstract sfFetcher: SFFetcher;
  protected readonly abstract mapped: MappedUtil;
  protected abstract languageDecorator(el: Element): void;
  protected abstract noneDecorator(el: Element): void;
  protected abstract elementDecorator(root: Element, el: Element): void;
  /* End... */

  protected init(): void {
    this._inMode = this instanceof Decorator;
  }

  protected dispatch(root: Element, el: Element): void {
    const klass = this.getAdditionalClasses(el);
    if (klass.length !== 0) {
      el.className += ` ${klass}`;
    }

    let skipDefault = false;
    switch (getOriginalNameIfPossible(el)) {
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
    }

    if (!skipDefault) {
      this.elementDecorator(root, el);
    }
  }

  _getIDManagerForRefman(refman: LabelManager | ExampleReferenceManager):
  IDManager {
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
    if (refman !== null) {
      let wedId = el.id;
      if (wedId === "") {
        const id = el.getAttribute(convert.encodeAttrName("xml:id"));
        const idMan = this._getIDManagerForRefman(refman);
        wedId = `BTW-${id !== null ? id : idMan.generate()}`;
        el.id = wedId;
      }

      // We have some reference managers that don't derive from ReferenceManager
      // and thus do not have this method.
      if (refman instanceof LabelManager) {
        refman.allocateLabel(wedId);
      }
    }
  }

  explanationDecorator(root: Element, el: Element): void {
    // Handle explanations that are in btw:example-explained.
    if ((el.parentNode as Element).classList
        .contains("btw:example-explained")) {
      let child = el.firstElementChild;
      while (child !== null) {
        const next = child.nextElementSibling;
        if (child.classList.contains("_explanation_bullet")) {
          this.guiUpdater.removeNode(child);
          break; // There's only one.
        }
        child = next;
      }

      const cit = domutil.siblingByClass(el, "btw:cit");
      // If the next btw:cit element contains Pāli text.
      if (cit !== null &&
          cit.querySelector(
            `*[${convert.encodeAttrName("xml:lang")}='pi-Latn']`) !== null) {
        const div = el.ownerDocument!.createElement("div");
        div.className = "_phantom _decoration_text _explanation_bullet";
        div.style.position = "absolute";
        div.style.left = "-1em";
        div.textContent = WHEEL;
        this.guiUpdater.insertNodeAt(el, 0, div);
        (el as HTMLElement).style.position = "relative";
      }
      this.elementDecorator(root, el);
      return;
    }

    this.elementDecorator(root, el);
    const parent = el.parentNode as Element;
    // Is it in a subsense?
    if (parent.classList.contains("btw:subsense")) {
      const refman = this.refmans.getSubsenseRefman(el)!;
      const label = refman.idToSublabel(parent.id);
      let child = el.firstElementChild;
      let start: Element | undefined;
      while (child !== null) {
        const next = child.nextElementSibling;
        if (child.classList.contains("_explanation_number")) {
          this.guiUpdater.removeNode(child);
        }
        else if (child.classList.contains("__start_label")) {
          start = child;
        }
        child = next;
      }

      // We want to insert it after the start label.
      const div = el.ownerDocument!.createElement("div");
      div.className = "_phantom _decoration_text _explanation_number " +
        "_start_wrapper'";
      div.textContent = `${label}. `;
      this.guiUpdater.insertBefore(el, div,
                                   start !== undefined ? start.nextSibling :
                                   el.firstChild);
    }

    this.headingDecorator.sectionHeadingDecorator(el);
  }

  citDecorator(root: Element, el: Element): void {
    this.elementDecorator(root, el);

    let ref: Element | undefined;
    let child = el.firstElementChild;
    while (child !== null) {
      const next = child.nextElementSibling;
      if (child.classList.contains("_ref_space") ||
          child.classList.contains("_cit_bullet")) {
        this.guiUpdater.removeNode(child);
      }
      else if (child.classList.contains("ref")) {
        ref = child;
      }
      child = next;
    }

    if (ref !== undefined) {
      const space = el.ownerDocument!.createElement("div");
      space.className = "_text _phantom _ref_space";
      space.textContent = " ";
      el.insertBefore(space, ref.nextSibling);
    }

    if (el.querySelector(
      `*[${convert.encodeAttrName("xml:lang")}='pi-Latn']`) !== null) {
      const div = el.ownerDocument!.createElement("div");
      div.className = "_phantom _text _cit_bullet";
      div.style.position = "absolute";
      div.style.left = "-1em";
      div.textContent = WHEEL;
      this.guiUpdater.insertNodeAt(el, 0, div);
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
    let origTarget = el.getAttribute(convert.encodeAttrName("target"));
    // XXX This should become an error one day. The only reason we need this now
    // is that some of the early test files had <ref> elements without targets.
    if (origTarget === null) {
      origTarget = "";
    }

    origTarget = origTarget.trim();

    const doc = root.ownerDocument!;
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
              this.guiUpdater.removeNode(child);
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
        let label: string | undefined;
        if (refman !== null) {
          if (refman instanceof LabelManager) {
            if (refman.name === "sense" || refman.name === "subsense") {
              label = refman.idToLabel(targetId.slice(1));
              label = label !== undefined ? `[${label}]` : undefined;
            }
          }
          else {
            // An empty target can happen when first decorating the document.
            if (target !== null) {
              label = refman.getPositionalLabel(
                mustGetMirror(el) as Element,
                mustGetMirror(target) as Element);
            }
          }
        }

        if (label === undefined) {
          label = targetId;
        }

        a.textContent = label;

        // A ptr contains only attributes, no text, so we can just append.
        const pair = this.mode.nodesAroundEditableContents(el);
        this.guiUpdater.insertBefore(el, text, pair[1]);

        if (target !== null) {
          const targetName = (mustGetMirror(target) as Element).tagName;

          // Reduce the target to something sensible for tooltip text.
          if (targetName === "btw:sense") {
            const terms = target.querySelectorAll(this.mapped.toGUISelector(
              this.senseTooltipSelector));
            let html = "";
            for (let i = 0; i < terms.length; ++i) {
              const term = terms[i];
              html += term.innerHTML;
              if (i < terms.length - 1) {
                html += ", ";
              }
            }
            target = target.ownerDocument!.createElement("div");
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
            this.guiUpdater.removeNode(child);
          }
          child = next;
        }

        const abbr = doc.createElement("div");
        abbr.className = "_text _phantom _ref_abbr";
        this.guiUpdater.insertBefore(el, abbr, el.firstChild);
        const open = doc.createElement("div");
        open.className = "_phantom _decoration_text _ref_paren " +
          "_open_ref_paren _start_wrapper";
        open.textContent = "(";
        this.guiUpdater.insertBefore(el, open, abbr);

        const close = doc.createElement("div");
        close.className = "_phantom _decoration_text " +
          "_ref_paren _close_ref_paren _end_wrapper";
        close.textContent = ")";
        this.guiUpdater.insertBefore(el, close, null);

        // tslint:disable-next-line:no-floating-promises
        this.fetchAndFillBiblData(targetId, el, abbr);
      }
    }
  }

  async fetchAndFillBiblData(targetId: string,
                             el: Element, abbr: Element): Promise<void> {
    const info = await this.mode.getBibliographicalInfo();

    const data = info[targetId];
    if (data !== undefined) {
      this.fillBiblData(el, abbr, data);
    }
    else {
      this.guiUpdater.insertText(abbr, 0, "NON-EXISTENT");
    }

    $(el).trigger("wed-refresh");
  }

  fillBiblData(el: Element, abbr: Element, data: BibliographicalItem): void {
    setTitle($(el as HTMLElement), isPrimarySource(data) ? data.item : data);
    this.guiUpdater.insertText(abbr, 0, biblDataToReferenceText(data));
  }

  sfDecorator(root: Element, el: Element): void {
    //
    // When editing them, ``btw:sf`` contains the semantic field paths, and
    // there are no names.
    //
    // When displaying articles, the paths are in encoded ``ref`` attribute, and
    // the ``btw:sf`` elements contain the names + path of the semantic fields.
    //

    // We're already wrapped.
    if (domutil.closestByClass(el, "field-view", root) !== null) {
      return;
    }

    const inMode = this._inMode;
    const parent = el.parentNode!;
    const before = el.previousSibling;

    let ref: string | undefined;
    if (!inMode) {
      const dataWedRef = el.attributes[ENCODED_REF_ATTR_NAME];
      if (dataWedRef) {
        ref = el.attributes[ENCODED_REF_ATTR_NAME].value;
      }

      // We do not decorate if we have no references.
      if (ref === undefined) {
        return;
      }
    }
    else {
      const dataNode = this.editor.toDataNode(el);
      ref = dataNode.textContent!;
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
    this.guiUpdater.insertBefore(
      parent as Element, view.el,
      before !== null ? before.nextSibling : parent.firstChild);

    if (inMode) {
      // When we are editing we want to fill the semantic field with its name
      // and path.
      this.sfFetcher.fetch([ref]).then(resolved => {
        const resolvedRef = resolved[ref!];
        el.textContent = (resolvedRef !== undefined) ?
          `${resolvedRef.heading_for_display} (${ref})` :
          `Unknown field (${ref})`;
      });
    }
  }

  /**
   * Returns additional classes that should apply to a node.
   *
   * @param node The node to check.
   *
   * @returns A string that contains all the class names separated by spaces. In
   * other words, a string that could be put as the value of the ``class``
   * attribute in an HTML tree.
   */
  getAdditionalClasses(node: Element): string {
    const dataNode = getMirror(node);
    if (dataNode === undefined) {
      return "";
    }

    if (!isElement(dataNode)) {
      throw new Error("the GUI node passed does not correspond to an element");
    }
    return this.metadata.isInline(dataNode) ? "_inline" : "";
  }
}
