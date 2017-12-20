/**
 * Toolbar for BTWMode.
 * @author Louis-Dominique Dubeau
 */
import * as $ from "jquery";
import * as salve from "salve";

import { Action } from "wed/action";
import { Decorator } from "wed/decorator";
import { DLoc } from "wed/dloc";
import { Listener as DOMListener } from "wed/domlistener";
import * as domutil from "wed/domutil";
import { closest, closestByClass } from "wed/domutil";
import * as contextMenu from "wed/gui/context-menu";
import { tooltip } from "wed/gui/tooltip";
import { GUIUpdater } from "wed/gui-updater";
import * as inputTriggerFactory from "wed/input-trigger-factory";
import "wed/jquery.findandself";
import * as keyConstants from "wed/key-constants";
import { LabelManager } from "wed/labelman";
import { GenericModeOptions } from "wed/modes/generic/generic";
import { Metadata } from "wed/modes/generic/metadata";
import { makeElement, Transformation, TransformationData } from "wed/transformation";
import * as updaterDOMListener from "wed/domlistener";
import * as util from "wed/util";

import { DispatchMixin } from "./btw-dispatch";
import { HeadingDecorator } from "./btw-heading-decorator";
import { Mode } from "./btw-mode";
import * as refmans from "./btw-refmans";
import * as btwUtil from "./btw-util";
import { IDManager } from "./id-manager";
import { SFFetcher } from "./semantic-field-fetcher";

const _indexOf = Array.prototype.indexOf;
const makeDLoc = DLoc.makeDLoc;

// TEMPORARY TYPE DEFINITIONS
/* tslint:disable: no-any */
type Editor = any;
/* tslint:enable: no-any */
// END TEMPORARY TYPE DEFINITIONS

interface VisibleAbsenceSpec {
  /**
   * A jQuery selector indicating the parent(s) for which to create visible
   * absences.
   */
  parent: string;
  /** An array indicating the children for which to create visible absences. */
  children: string[];
}

// tslint:disable-next-line:no-any
function menuClickHandler(editor: Editor, guiLoc: DLoc, items: any,
                          ev: JQueryMouseEventObject): boolean {
  if (editor.caretManager.caret === undefined) {
    editor.caretManager.setCaret(guiLoc);
  }
  // tslint:disable-next-line:no-unused-expression
  new contextMenu.ContextMenu(editor.my_window.document,
                              ev.clientX, ev.clientY, items);
  return false;
}

export class BTWDecorator extends Decorator {
  private readonly mode: Mode;
  private readonly guiRoot: Element;
  private readonly guiDOMListener: DOMListener;
  private readonly senseSubsenseIdManager: IDManager;
  private readonly exampleIdManager: IDManager;
  private readonly refmans: refmans.WholeDocumentManager;
  private readonly headingDecorator: HeadingDecorator;
  private readonly senseTooltipSelector: string;
  private readonly sfFetcher: SFFetcher;
  private sensesForRefreshSubsenses: Element[];
  private readonly labelLevels: Record<string, number> = Object.create(null);
  private readonly visibleAbsenceSpecs: VisibleAbsenceSpec[];
  /* tslint:enable: no-any */

  // Methods provided by the mixin.
  dispatch: (root: Element, el: Element) => void;
  explanationDecorator: (root: Element, el: Element) => void;
  // End of methods provided by the mixin.

  constructor(semanticFieldFetchUrl: string, mode: Mode,
              protected readonly metadata: Metadata,
              protected readonly options: GenericModeOptions,
              domlistener: DOMListener,
              editor: Editor, guiUpdater: GUIUpdater) {
    super(domlistener, editor, guiUpdater);
    DispatchMixin.call(this);

    this.metadata = metadata;
    this.guiRoot = this.editor.gui_root;
    this.guiDOMListener =
      new updaterDOMListener.Listener(this.guiRoot, this.guiUpdater);
    this.mode = mode;
    this.senseSubsenseIdManager = new IDManager("S.");
    this.exampleIdManager = new IDManager("E.");
    this.refmans = new refmans.WholeDocumentManager();
    this.headingDecorator = new HeadingDecorator(this.refmans,
                                                   this.guiUpdater);
    this.senseTooltipSelector = "btw:english-rendition>btw:english-term";
    this.sfFetcher = new SFFetcher(semanticFieldFetchUrl, undefined,
                                   ["changerecords"]);

    this.sensesForRefreshSubsenses = [];

    [
      "btw:entry",
      "btw:lemma",
      "btw:overview",
      "btw:credits",
      "btw:definition",
      "btw:sense-discrimination",
      "btw:sense",
      "btw:subsense",
      "btw:english-renditions",
      "btw:english-rendition",
      "term",
      "btw:english-term",
      "btw:semantic-fields",
      "btw:sf",
      "btw:explanation",
      "btw:citations",
      "p",
      "ptr",
      "foreign",
      "btw:historico-semantical-data",
      "btw:etymology",
      "ref",
      "btw:sense-emphasis",
      "btw:lemma-instance",
      "btw:antonym-instance",
      "btw:cognate-instance",
      "btw:conceptual-proximate-instance",
      "btw:contrastive-section",
      "btw:antonyms",
      "btw:cognates",
      "btw:conceptual-proximates",
      "btw:other-citations",
      "btw:term",
      "btw:none",
    ].forEach((x) => {
      this.labelLevels[x] = 2;
    });

    // The following array is going to be transformed into the data
    // structure just described above.
    this.visibleAbsenceSpecs = [{
      parent: domutil.toGUISelector("btw:sense"),
      children: ["btw:subsense", "btw:explanation",
                 "btw:citations", "btw:other-citations",
                 "btw:contrastive-section"],
    }, {
      parent: domutil.toGUISelector("btw:citations"),
      children: ["btw:example", "btw:example-explained"],
    }, {
      parent: domutil.toGUISelector(
        "btw:subsense, btw:antonym, btw:cognate, btw:conceptual-proximate"),
      children: ["btw:other-citations"],
    }, {
      parent: domutil.toGUISelector("btw:example, btw:example-explained"),
      children: ["btw:semantic-fields"],
    }, {
      parent: domutil.toGUISelector("btw:other-citations"),
      children: ["btw:cit", "btw:semantic-fields"],
    }];
  }

  // tslint:disable-next-line:max-func-body-length
  addHandlers(): void {
    const dl = this.domlistener;
    const gdl = this.guiDOMListener;

    dl.addHandler("added-element",
                  util.classFromOriginalName("btw:entry"),
                  (_root, _parent, _prev, _next, el) =>  {
                    this.addedEntryHandler(el);
                  });

    dl.addHandler("included-element",
                  util.classFromOriginalName("btw:sense"),
                  (root, _tree, _parent, _prev, _next, el) => {
                    this.includedSenseHandler(root, el);
                  });

    gdl.addHandler("excluding-element",
                   util.classFromOriginalName("btw:sense"),
                   (_root, _tree, _parent, _prev, _next, el) => {
                     this.excludingSenseHandler(el);
                   });

    dl.addHandler("included-element",
                  util.classFromOriginalName("btw:subsense"),
                  (root, _tree, _parent, _prev, _next, el) => {
                    this.includedSubsenseHandler(root, el);
                  });

    gdl.addHandler("excluding-element",
                   util.classFromOriginalName("btw:subsense"),
                   (root, _tree, _parent, _prev, _next, el) => {
                     this.excludingSubsenseHandler(root, el);
                   });

    gdl.addHandler("excluded-element",
                   util.classFromOriginalName("btw:example, " +
                                              "btw:example-explained"),
                   (_root, _tree, _parent, _prev, _next, el) => {
                     this.excludedExampleHandler(el);
                   });

    gdl.addHandler("children-changing",
                   domutil.toGUISelector("ref, ref *"),
                   (root, _added, _removed, _prev, _next, el) => {
                     this._refChangedInGUI(root,
                                           closestByClass(el, "ref", root)!);
                   });

    gdl.addHandler("text-changed",
                   domutil.toGUISelector("ref, ref *"),
                   (root, el) => {
                     this._refChangedInGUI(root,
                                           closestByClass(el, "ref", root)!);
                   });

    dl.addHandler("included-element",
                  util.classFromOriginalName("*"),
                  (root, _tree, _parent, _prev, _next, el) => {
                    this.refreshElement(root, el);
                  });

    // This is needed to handle cases when an btw:cit acquires or loses Pāli
    // text.
    dl.addHandler("excluding-element",
                  domutil.toGUISelector("btw:cit foreign"),
                  (root, _tree, _parent, _prev, _next, el) => {
                    const cit = closestByClass(el, "btw:cit", root)!;
                    // Refresh after the element is removed.
                    setTimeout(() => {
                      this.refreshElement(root, cit);
                      this.refreshElement(root, domutil.siblingByClass(
                        cit, "btw:explanation")!);
                    }, 0);
                  });

    dl.addHandler("included-element",
                  domutil.toGUISelector("btw:cit foreign"),
                  (root, _tree, _parent, _prev, _next, el) => {
                    const cit = closestByClass(el, "btw:cit", root)!;
                    this.refreshElement(root, cit);
                    this.refreshElement(root, domutil.siblingByClass(
                      cit, "btw:explanation")!);
                  });

    dl.addHandler("children-changed",
                  util.classFromOriginalName("*"),
                  (root, added, removed, _prev, _next, el) => {
                    let removedFlag = false;
                    for (const r of removed) {
                      removedFlag = r.nodeType === Node.TEXT_NODE ||
                        r.classList.contains("_real") ||
                        r.classList.contains("_phantom_wrap");
                      if (removedFlag) {
                        break;
                      }
                    }

                    if (!removedFlag) {
                      let addedFlag = false;
                      for (const r of added) {
                        addedFlag = r.nodeType === Node.TEXT_NODE ||
                          r.classList.contains("_real") ||
                          r.classList.contains("_phantom_wrap");
                        if (addedFlag) {
                          break;
                        }
                      }

                      if (addedFlag) {
                        this.refreshElement(root, el);
                      }
                    }
                    else {
                      // Refresh the element **after** the data is removed.
                      setTimeout(() => {
                        this.refreshElement(root, el);
                      }, 0);
                    }
                  });

    dl.addHandler("trigger",
                  "included-sense",
                  this.includedSenseTriggerHandler.bind(this));

    dl.addHandler("trigger",
                  "refresh-subsenses",
                  this.refreshSubsensesTriggerHandler.bind(this));

    dl.addHandler("trigger",
                  "refresh-sense-ptrs",
                  this.refreshSensePtrsHandler.bind(this));

    gdl.addHandler("included-element",
                   ".head",
                   () => {
                     gdl.trigger("refresh-navigation-trigger");
                   });

    gdl.addHandler("excluded-element",
                   ".head",
                   () => {
                     gdl.trigger("refresh-navigation-trigger");
                   });

    gdl.addHandler("trigger", "refresh-navigation-trigger",
                   this._refreshNavigationHandler.bind(this));
    gdl.startListening();

    super.addHandlers();
    inputTriggerFactory.makeSplitMergeInputTrigger(this.editor,
                                                   "p",
                                                   keyConstants.ENTER,
                                                   keyConstants.BACKSPACE,
                                                   keyConstants.DELETE);
  }

  addedEntryHandler(el: Element): void {
    //
    // Perform general checks before we start decorating anything.
    //
    const dataEl = $.data(el, "wed_mirror_node");
    const sensesSubsenses = domutil.dataFindAll(dataEl,
                                                "btw:sense, btw:subsense");
    for (const s of sensesSubsenses) {
      const id = s.getAttribute("xml:id");
      if (id !== null) {
        this.senseSubsenseIdManager.seen(id, true);
      }
    }

    const examples = domutil.dataFindAll(dataEl,
                                       "btw:example, btw:example-explained");
    for (const ex of examples) {
      const id = ex.getAttribute("xml:id");
      if (id !== null) {
        this.exampleIdManager.seen(id, true);
      }
    }
  }

  refreshElement(root: Element, el: Element): void {
    // Skip elements which would already have been removed from the
    // tree. Unlikely but...
    if (!root.contains(el)) {
      return;
    }

    this.refreshVisibleAbsences(root, el);

    this.dispatch(root, el);

    //
    // This mode makes the validator work while it is decorating the GUI
    // tree. Therefore, the position of errors *can* be erroneous when these
    // errors are generated while the GUI tree is being decorated. So we need to
    // restart the validation to fix the erroneous error markers.
    //
    // We want to do it only if there *are* validation errors in this element.
    //
    let error = false;
    let child = el.firstElementChild;
    while (child !== null) {
      error = child.classList.contains("wed-validation-error");
      if (error) {
        break;
      }

      child = child.nextElementSibling;
    }

    if (error) {
      this.editor.validator.restartAt($.data(el, "wed-mirror-node"));
    }
  }

  elementDecorator(root: Element, el: Element): void {
    const origName = util.getOriginalName(el);
    const level = this.labelLevels[origName];
    super.elementDecorator(root, el, level !== undefined ? level : 1,
                           this.contextMenuHandler.bind(this, true),
                           this.contextMenuHandler.bind(this, false));
  }

  noneDecorator(el: Element):  void {
    this.guiUpdater.removeNodes(Array.from(el.childNodes));
    const text = el.ownerDocument.createElement("div");
    text.className = "_text _phantom";
    text.textContent = "ø";
    this.guiUpdater.insertBefore(el, text, null);
  }

  private singleClickHandler(dataLoc: DLoc,
                             tr: Transformation<TransformationData>,
                             root: Element,
                             el: Element, ev: JQueryMouseEventObject): void {
    if (this.editor.caretManager.getDataCaret() === undefined) {
      this.editor.caretManager.setCaret(dataLoc);
    }
    tr.boundTerminalHandler(ev);
    this.refreshElement(root, el);
  }

  // tslint:disable-next-line:max-func-body-length cyclomatic-complexity
  refreshVisibleAbsences(root: Element, el: Element): void {
    let found: VisibleAbsenceSpec | undefined;
    for (const spec of this.visibleAbsenceSpecs) {
      if (el.matches(spec.parent)) {
        found = spec;
        break;
      }
    }

    let topChild = el.firstElementChild;
    while (topChild !== null) {
      const next = topChild.nextElementSibling;
      if (topChild.classList.contains("_va_instantiator")) {
        this.guiUpdater.removeNode(topChild);
      }
      topChild = next;
    }

    if (found === undefined) {
      return;
    }

    const node = this.editor.toDataNode(el);
    const origErrors = this.editor.validator.getErrorsFor(node);

    // Create a hash table that we can use for later tests.
    const origStrings = Object.create(null);
    for (const err of origErrors) {
      origStrings[err.error.toString()] = true;
    }

    for (const spec of found.children) {
      const ename = this.mode.getAbsoluteResolver().resolveName(spec)!;
      let locations = this.editor.validator.possibleWhere(
        node, new salve.Event("enterStartTag", ename.ns, ename.name));

      // Narrow it down to locations where adding the element won't cause a
      // subsequent problem.
      const filteredLocations: number[] = [];

      locationLoop:
      for (const l of locations) {
        // We clone only the node itself and its first level children.
        const clone = node.cloneNode(false);
        const div = clone.ownerDocument.createElement("div");
        div.appendChild(clone);

        let child = node.firstChild;
        while (child !== null) {
          clone.appendChild(child.cloneNode(false));
          child = child.nextSibling;
        }

        const insertAt = clone.childNodes[l];
        clone.insertBefore(makeElement(clone.ownerDocument, ename.ns, spec),
                           insertAt !== undefined ? insertAt : null);

        const errors =
          this.editor.validator.speculativelyValidateFragment(
            node.parentNode!,
            _indexOf.call(node.parentNode!.childNodes, node), div);

        // What we are doing here is reducing the errors only to those that
        // indicate that the added element would be problematic.
        if (errors !== false) {
          for (const err of errors) {
            const errMsg = err.error.toString();
            if (err.node === clone &&
                // We want only errors that were not originally present.
                !origStrings[errMsg] &&
                // And that are about a tag not being allowed.
                errMsg.lastIndexOf("tag not allowed here: ", 0) === 0) {
              // There's nothing to be done with this location.
              continue locationLoop;
            }
          }
        }

        filteredLocations.push(l);
      }
      locations = filteredLocations;

      // No suitable location.
      if (locations.length === 0) {
        continue;
      }

      for (const l of locations) {
        const dataLoc = DLoc.mustMakeDLoc(this.editor.data_root, node, l);
        const data = { name: spec, moveCaretTo: dataLoc };
        const guiLoc = this.guiUpdater.fromDataLocation(dataLoc);
        if (guiLoc === null) {
          throw new Error("cannot get GUI location from data location");
        }

        const actions =
          this.mode.getContextualActions("insert", spec, node, l);
        const tuples: [Action<{}>, TransformationData, string][] = [];
        for (const act of actions) {
          tuples.push([act, data, act.getLabelFor(data)]);
        }

        const control = el.ownerDocument.createElement("button");
        control.className =
          "_gui _phantom _va_instantiator btn btn-instantiator btn-xs";
        control.setAttribute("href", "#");
        const $control = $(control);
        if (this.editor.preferences.get("tooltips")) {
          // Get tooltips from the current mode
          tooltip($control, {
            title: this.editor.mode.shortDescriptionFor(spec),
            // We are cheating. The documented interface states that container
            // should be a string. However, passing a JQuery object works.
            container: $control as any,
            delay: { show: 1000 },
            placement: "auto top",
            trigger: "hover",
          });
        }

        if (tuples.length > 1) {
          // tslint:disable-next-line:no-inner-html
          control.innerHTML = ` + ${spec}`;

          // Convert the tuples to actual menu items.
          const items: Element[] = [];
          for (const tup of tuples) {
            const li = el.ownerDocument.createElement("li");
            // tslint:disable-next-line:no-inner-html
            li.innerHTML = `<a tabindex='0' href='#'>${tup[2]}</a>`;
            const $a = $(li.firstChild!);
            $a.click(tup[1], tup[0].boundHandler);
            $a.mousedown(false);
            items.push(li);
          }

          $control.click(menuClickHandler.bind(undefined, this.editor,
                                               guiLoc, items));
        }
        else if (tuples.length === 1) {
          // tslint:disable-next-line:no-inner-html
          control.innerHTML = tuples[0][2];
          $control.mousedown(false);
          $control.click(tuples[0][1],
                         this.singleClickHandler.bind(this,
                                                      dataLoc, tuples[0][0],
                                                      root, el));
        }
        this.guiUpdater.insertNodeAt(guiLoc, control);
      }
    }
  }

  idDecorator(root: Element, el: Element): void {
    DispatchMixin.prototype.idDecorator.call(this, root, el);
    this.domlistener.trigger("refresh-sense-ptrs");
  }

  refreshSensePtrsHandler(root: Element): void {
    const ptrs = root.getElementsByClassName("ptr");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < ptrs.length; ++i) {
      this.linkingDecorator(root, ptrs[i], true);
    }
  }

  /**
   * This function works exactly like the one in [[DispatchMixin]] except that
   * it takes the additional ``final_`` parameter.
   *
   * @param final_ Whether there will be any more changes to
   * this ptr or not.
   */
  linkingDecorator(root: Element, el: Element, isPtr: boolean,
                   final_: boolean = false): void {
    DispatchMixin.prototype.linkingDecorator.call(this, root, el, isPtr);

    // What we are doing here is taking care of updating links to examples when
    // the reference to the bibliographical source they contain is
    // updated. These updates happen asynchronously.
    if (isPtr && !final_) {
      const doc = el.ownerDocument;
      let origTarget = el.getAttribute(util.encodeAttrName("target"));
      if (origTarget === null) {
        origTarget = "";
      }

      origTarget = origTarget.trim();

      if (origTarget.lastIndexOf("#", 0) !== 0) {
        return;
      }

      // Internal target
      // Add BTW in front because we want the target used by wed.
      const targetId = origTarget.replace(/#(.*)$/, "#BTW-$1");

      // Find the referred element. Slice to drop the #.
      const target = doc.getElementById(targetId.slice(1));

      if (target === null) {
        return;
      }

      if (!(target.classList.contains("btw:example") ||
            target.classList.contains("btw:example-explained"))) {
        return;
      }

      // Get the ref element that olds the reference to the
      // bibliographical item, and set an event handler to make sure
      // we update *this* ptr, when the ref changes.
      const ref = target.querySelector(domutil.toGUISelector("btw:cit>ref"))!;

      $(ref).on("wed-refresh", () => {
        this.linkingDecorator(root, el, isPtr);
      });
    }
  }

  includedSenseHandler(root: Element, el: Element): void {
    this.idDecorator(root, el);
    this.domlistener.trigger("included-sense");
  }

  excludingSenseHandler(el: Element): void {
    this._deleteLinksPointingTo(el);
    // Yep, we trigger the included-sense trigger.
    this.domlistener.trigger("included-sense");
  }

  includedSubsenseHandler(root: Element, el: Element): void {
    this.idDecorator(root, el);
    this.refreshSubsensesForSense(el.parentNode as Element);
  }

  excludingSubsenseHandler(root: Element, el: Element): void {
    this._deleteLinksPointingTo(el);
    this.refreshSubsensesForSense(el.parentNode as Element);
  }

  _deleteLinksPointingTo(el: Element): void {
    const id = el.getAttribute(util.encodeAttrName("xml:id"));

    // Whereas using querySelectorAll does not **generally** work,
    // using this selector, which selects only on attribute values,
    // works.
    const selector = `*[target='#${id}']`;

    const links = this.editor.data_root.querySelectorAll(selector);
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < links.length; ++i) {
      this.editor.data_updater.removeNode(links[i]);
    }
  }

  excludedExampleHandler(el: Element): void {
    this._deleteLinksPointingTo(el);
  }

  includedSenseTriggerHandler(root: Element): void {
    const senses = root.getElementsByClassName("btw:sense");
    if (senses.length !== 0) {
      const refman = this.refmans.getRefmanForElement(senses[0]);
      if (!(refman instanceof LabelManager)) {
        throw new Error("expected a label manager");
      }
      refman.deallocateAll();
    }
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < senses.length; ++i) {
      const sense = senses[i];
      this.idDecorator(root, sense);
      this.headingDecorator.sectionHeadingDecorator(sense);
      this.headingDecorator.updateHeadingsForSense(sense);
      this.refreshSubsensesForSense(sense);
    }
  }

  refreshSubsensesForSense(sense: Element): void {
    // The indexOf search ensures we don't put duplicates in the list.
    if (this.sensesForRefreshSubsenses.indexOf(sense) === -1) {
      this.sensesForRefreshSubsenses.push(sense);
      this.domlistener.trigger("refresh-subsenses");
    }
  }

  refreshSubsensesTriggerHandler(root: Element): void {
    // Grab the list before we try to do anything.
    const senses = this.sensesForRefreshSubsenses;
    this.sensesForRefreshSubsenses = [];
    senses.forEach((sense) => {
      this._refreshSubsensesForSense(root, sense);
    });
  }

  _refreshSubsensesForSense(root: Element, sense: Element): void {
    const refman = this.refmans.getSubsenseRefman(sense)!;
    refman.deallocateAll();

    // This happens if the sense was removed from the document.
    if (!this.editor.gui_root.contains(sense)) {
      return;
    }

    const subsenses = sense.getElementsByClassName("btw:subsense");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < subsenses.length; ++i) {
      const subsense = subsenses[i];
      this.idDecorator(root, subsense);
      const explanation = domutil.childByClass(subsense, "btw:explanantion");
      if (explanation !== null) {
        this.explanationDecorator(root, explanation);
      }

      this.headingDecorator.updateHeadingsForSubsense(subsense);
    }
  }

  _refChangedInGUI(root: Element, el: Element): void {
    const example =
      closest(el, domutil.toGUISelector("btw:example, btw:example-explained"));

    if (example === null) {
      return;
    }

    const id = example.getAttribute(util.encodeAttrName("xml:id"));
    if (id === null) {
      return;
    }

    // Find the referred element.
    const ptrs = root.querySelectorAll(
      `${util.classFromOriginalName("ptr")}[${util.encodeAttrName("target")}\
='#${id}']`);

    // tslint:disable-next-line:one-variable-per-declaration
    for (let i = 0, limit = ptrs.length; i < limit; ++i) {
      this.refreshElement(root, ptrs[i]);
    }
  }

  languageDecorator(el: Element): void {
    const lang = el.getAttribute(util.encodeAttrName("xml:lang"))!;
    const prefix = lang.slice(0, 2);
    if (prefix !== "en") {
      el.classList.add("_btw_foreign");
      // $el.css("background-color", "#DFCFAF");
      // // Chinese is not commonly italicized.
      if (prefix !== "zh") {
        // $el.css("font-style", "italic");
        el.classList.add("_btw_foreign_italics");
      }

      let label = btwUtil.languageCodeToLabel(lang);
      if (label === undefined) {
        throw new Error(`unknown language: ${lang}`);
      }
      label = label.split("; ")[0];
      tooltip($(el), { title: label, container: "body", trigger: "hover" });
    }
  }

  _refreshNavigationHandler(): void {
    const doc = this.guiRoot.ownerDocument;
    const prevAtDepth: Element[] = [doc.createElement("li")];

    function getParent(depth: number): Element {
      let parent = prevAtDepth[depth];
      if (parent === undefined) {
        parent = doc.createElement("li");
        prevAtDepth[depth] = parent;
        const grandparent = getParent(depth - 1);
        grandparent.appendChild(parent);
      }
      return parent;
    }

    const heads = this.guiRoot.getElementsByClassName("head");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < heads.length; ++i) {
      const el = heads[i];
      // This is the list of DOM parents that do have a head
      // child, i.e. which participate in navigation.
      const parents: Node[] = [];
      let parent = el.parentNode;
      while (parent !== null) {
        if (domutil.childByClass(parent, "head") !== null) {
          parents.push(parent);
        }

        if (parent === this.guiRoot) {
          break; // Don't go beyond this point.
        }

        parent = parent.parentNode;
      }

      // This will never be less than 1 because the current element's parent
      // satisfies the selectors above.
      const myDepth = parents.length;

      parent = el.parentNode;
      let origName = util.getOriginalName(parent as Element);

      const li = doc.createElement("li");
      li.className = "btw-navbar-item";
      // tslint:disable-next-line:no-inner-html
      li.innerHTML =
        `<a class='navbar-link' href='#${el.id}'>${el.textContent}</a>`;

      // getContextualActions needs to operate on the data tree.
      let dataParent = $.data(parent as Element, "wed_mirror_node");

      // btw:explanation is the element that gets the heading that marks the
      // start of a sense. So we need to adjust.
      if (origName === "btw:explanation") {
        const parentSubsense = dataParent.parentNode;
        if (parentSubsense.tagName === "btw:subsense") {
          origName = "btw:subsense";
          dataParent = parentSubsense;
        }
      }

      // Add contextmenu handlers depending on the type of parent we are dealing
      // with.
      const a = li.firstElementChild!;
      li.setAttribute("data-wed-for", origName);

      const $el = $(el);
      if (origName === "btw:sense" ||
          origName === "btw:english-rendition" ||
          origName === "btw:subsense") {
        $(a).on("contextmenu", { node: dataParent },
                this._navigationContextMenuHandler.bind(this));
        a.innerHTML += " <i class='fa fa-cog'></i>";
        const oldIcon = domutil.childByClass(el, "fa");
        if (oldIcon !== null) {
          oldIcon.parentNode!.removeChild(oldIcon);
        }
        el.innerHTML += " <i class='fa fa-cog'></i>";
        // We must remove all previous handlers.
        $el.off("wed-context-menu");
        $el.on("wed-context-menu", { node: dataParent },
               this._navigationContextMenuHandler.bind(this));
      }
      else {
        // We turn off context menus on the link and on the header.
        $(a).on("contextmenu", false);
        $el.on("wed-context-menu", false);
      }
      el.setAttribute("data-wed-custom-context-menu", "true");

      getParent(myDepth - 1).appendChild(li);
      prevAtDepth[myDepth] = li;
    }

    this.editor.setNavigationList(
      Array.prototype.slice.call(prevAtDepth[0].children));
  }

  // tslint:disable-next-line:max-func-body-length
  _navigationContextMenuHandler(wedEv: JQueryEventObject,
                                ev?: JQueryEventObject): boolean {
    const mode = this.mode;
    const editor = this.editor;
    // ev is undefined if called from the context menu. In this case, wedEv
    // contains all that we want.
    if (ev === undefined) {
      ev = wedEv;
    }
    // node is the node in the data tree which corresponds to the navigation
    // item for which a context menu handler was required by the user.
    const node = wedEv.data.node;
    const origName = node.tagName;

    // container, offset: location of the node in its parent.
    const container = node.parentNode;
    const offset = _indexOf.call(container.childNodes, node) as number;

    // List of items to put in the contextual menu.
    const tuples: [Action<{}>, TransformationData, string][] = [];

    //
    // Create "insert" transformations for siblings that could be
    // inserted before this node.
    //
    let actions = mode.getContextualActions("insert", origName, container,
                                            offset);
    // data to pass to transformations
    let data: TransformationData = {
      name: origName,
      moveCaretTo: makeDLoc(editor.data_root, container, offset),
    };

    for (const act of actions) {
      tuples.push([act, data, `${act.getLabelFor(data)} before this one`]);
    }

    //
    // Create "insert" transformations for siblings that could be inserted after
    // this node.
    //
    actions = mode.getContextualActions("insert", origName, container,
                                        offset + 1);

    data = { name: origName,
             moveCaretTo: makeDLoc(editor.data_root, container, offset + 1) };
    for (const act of actions) {
      tuples.push([act, data, `${act.getLabelFor(data)} after this one`]);
    }

    const target = ev.target;
    const doc = ev.target.ownerDocument;
    const navList = closestByClass(target, "nav-list", document.body);
    if (navList !== null) {
      // This context menu was invoked in the navigation list.

      const thisLi = closest(target, "li", navList)!;
      const siblingLinks: Element[] = [];
      const parent = thisLi.parentNode as Element;
      let child = parent.firstElementChild;
      while (child !== null) {
        if (child.getAttribute("data-wed-for") === origName) {
          siblingLinks.push(child);
        }
        child = child.nextElementSibling;
      }

      // If the node has siblings we potentially add swap with previous and swap
      // with next.
      if (siblingLinks.length > 1) {
        data = { name: origName, node: node,
                 moveCaretTo: makeDLoc(editor.data_root, container, offset) };
        // However, don't add swap with prev if we are first.
        if (!siblingLinks[0].contains(ev.currentTarget)) {
          tuples.push([mode.swapWithPrevTr, data,
                       mode.swapWithPrevTr.getLabelFor(data)]);
        }

        // Don't add swap with next if we are last.
        if (!siblingLinks[siblingLinks.length - 1].contains(ev.currentTarget)) {
          tuples.push([mode.swapWithNextTr, data,
                       mode.swapWithNextTr.getLabelFor(data)]);
        }
      }
    }
    else {
      // Set the caret to be inside the head
      editor.caretManager.setCaret(target, 0);
    }

    // Delete the node
    data = { node: node, name: origName,
             moveCaretTo: makeDLoc(editor.data_root, node, 0) };
    actions = mode.getContextualActions("delete-element", origName, node, 0);
    for (const act of actions) {
      tuples.push([act, data, act.getLabelFor(data)]);
    }

    let li;

    // Convert the tuples to actual menu items.
    const items: Element[] = [];

    // Put the documentation link first.
    const docUrl = mode.documentationLinkFor(origName);
    if (docUrl != null) {
      li = doc.createElement("li");
      const a = editor.makeDocumentationLink(docUrl);
      li.appendChild(a);
      items.push(li);
    }

    for (const tup of tuples) {
      li = doc.createElement("li");
      // tslint:disable-next-line:no-inner-html
      li.innerHTML = `<a tabindex='0' href='#'>${tup[2]}</a>`;
      const $a = $(li.firstChild);
      $a.mousedown(false);
      $a.click(tup[1], tup[0].boundHandler);
      items.push(li);
    }

    // tslint:disable-next-line:no-unused-expression
    new contextMenu.ContextMenu(editor.my_window.document,
                                ev.clientX, ev.clientY, items);

    return false;
  }
}

// tslint:disable-next-line:no-any
function implement(mixes: any, mixin: any): void {
  const source = (mixin.prototype !== undefined) ? mixin.prototype : mixin;
  // tslint:disable-next-line:forin
  for (const f in source) {
    // We have to skip those properties already set in the class we mix into
    // because we create the class properties first and then add the mixin.
    if (!(f in mixes.prototype)) {
      mixes.prototype[f] = source[f];
    }
  }
}

implement(BTWDecorator, DispatchMixin);
