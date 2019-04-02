/**
 * Module for decorating headings
 * @author Louis-Dominique Dubeau
 */
import { treeUpdater, util } from "wed";
import TreeUpdater = treeUpdater.TreeUpdater;

import { WholeDocumentManager } from "./btw-refmans";
import * as btwUtil from "./btw-util";
import { IDManager } from "./id-manager";
import { MappedUtil } from "./mapped-util";

let nextHead = 0;
function allocateHeadID(): string {
  return `BTW-H-${++nextHead}`;
}

const defaultHeadingMap: Record<string, string> = {
  "btw:overview": "UNIT 1: OVERVIEW",
  "btw:sense-discrimination": "UNIT 2: SENSE DISCRIMINATION",
  "btw:historico-semantical-data": "UNIT 3: HISTORICO-SEMANTICAL DATA",
  "btw:credits": "UNIT 4: CREDITS",
};

type ElementToLabel = (el: Element) => string | undefined;

type Collapse = string | {
  kind: string;

  additionalClasses?: string;
};

interface InitialSpec {
  selector: string;

  heading: string | null;

  labelF?: ElementToLabel;

  suffix?: string;

  collapse?: Collapse;
}

interface Spec extends InitialSpec {
  dataSelector: string;
}

export class HeadingDecorator {
  private readonly collapseHeadingIdManager: IDManager;
  private readonly collapseIdManager: IDManager;

  private readonly boundGetSenseLabel: ElementToLabel;
  private readonly boundGetSubsenseLabel: ElementToLabel;

  private specs: Spec[];

  constructor(private readonly refmans: WholeDocumentManager,
              private readonly guiUpdater: TreeUpdater,
              private readonly mapped: MappedUtil,
              private readonly headingMap: Record<string, string> =
              defaultHeadingMap,
              private readonly impliedBrackets: boolean = true) {
    this.collapseHeadingIdManager = new IDManager("collapse-heading-");
    this.collapseIdManager = new IDManager("collapse-");

    // We bind them here so that we have a unique function to use.
    this.boundGetSenseLabel = this.refmans.getSenseLabel.bind(this.refmans);
    this.boundGetSubsenseLabel =
      this.refmans.getSubsenseLabel.bind(this.refmans);

    this.specs = [{
      selector: "btw:definition",
      heading: "definition",
    }, {
      selector: "btw:sense",
      heading: "SENSE",
      labelF: this.refmans.getSenseLabelForHead.bind(this.refmans),
    }, {
      selector: "btw:english-renditions",
      heading: "English renditions",
    }, {
      selector: "btw:english-rendition",
      heading: "English rendition",
    }, {
      selector: "btw:semantic-fields",
      heading: "semantic categories",
    }, {
      selector: "btw:etymology",
      heading: "etymology",
    }, {
      selector: "btw:sense>btw:explanation",
      heading: "brief explanation of sense",
      labelF: this.boundGetSenseLabel,
    }, {
      selector: "btw:subsense>btw:explanation",
      heading: "brief explanation of sense",
      labelF: this.boundGetSubsenseLabel,
    }, {
      selector: "btw:sense>btw:citations",
      heading: "citations for sense",
      labelF: this.boundGetSenseLabel,
    }, {
      selector: "btw:subsense>btw:citations",
      heading: "citations for sense",
      labelF: this.boundGetSubsenseLabel,
    }, {
      selector: "btw:antonym>btw:citations",
      heading: "citations",
    }, {
      selector: "btw:cognate>btw:citations",
      heading: "citations",
    }, {
      selector: "btw:conceptual-proximate>btw:citations",
      heading: "citations",
    }, {
      selector: "btw:contrastive-section",
      heading: "contrastive section for sense",
      labelF: this.boundGetSenseLabel,
    }, {
      selector: "btw:antonyms",
      heading: "antonyms",
    }, {
      selector: "btw:cognates",
      heading: "cognates",
    }, {
      selector: "btw:conceptual-proximates",
      heading: "conceptual proximates",
    }, {
      selector: "btw:sense>btw:other-citations",
      heading: "other citations for sense",
      labelF: this.boundGetSenseLabel,
    }, {
      selector: "btw:other-citations",
      heading: "other citations",
    }].map((x) => ({
      ...x,
      dataSelector: this.mapped.toGUISelector(x.selector),
    }));
  }

  addSpec(spec: InitialSpec): void {
    this.specs = this.specs.filter((x) => x.selector !== spec.selector);
    const fullSpec = {
      ...spec,
      dataSelector: this.mapped.toGUISelector(spec.selector),
    };
    this.specs.push(fullSpec);
  }

  unitHeadingDecorator(el: Element): void {
    let child = el.firstElementChild;
    while (child !== null) {
      const next = child.nextElementSibling;
      if (child.classList.contains("head")) {
        this.guiUpdater.removeNode(child);
        break; // There's only one.
      }
      child = next;
    }

    const name = util.getOriginalName(el);
    const headStr = this.headingMap[name];
    if (headStr === undefined) {
      throw new Error(
        `found an element with name ${name}, which is not handled`);
    }

    const head = el.ownerDocument!.createElement("div");
    head.className = "head _phantom _start_wrapper";
    // tslint:disable-next-line:no-inner-html
    head.innerHTML = headStr;
    head.id = allocateHeadID();
    this.guiUpdater.insertNodeAt(el, 0, head);
  }

  sectionHeadingDecorator(el: Element, headStr?: string): void {
    let child = el.firstElementChild;
    while (child !== null) {
      const next = child.nextElementSibling;
      if (child.classList.contains("head")) {
        this.guiUpdater.removeNode(child);
        break; // There's only one.
      }
      child = next;
    }

    let collapse: Collapse | undefined;
    if (headStr === undefined) {
      const name = util.getOriginalName(el);
      let found: Spec | undefined;
      for (const spec of this.specs) {
        if (el.matches(spec.dataSelector)) {
          found = spec;
          break;
        }
      }

      if (found === undefined) {
        throw new Error(
          `found an element with name ${name}, which is not handled`);
      }

      if (found.heading !== null) {
        const labelF = found.labelF;
        const labelFResult = labelF !== undefined ? labelF(el) : undefined;
        // tslint:disable-next-line:no-parameter-reassignment
        headStr = labelFResult !== undefined ?
          `${found.heading} ${labelFResult}` : found.heading;
      }

      if (found.suffix !== undefined) {
        // tslint:disable-next-line:no-parameter-reassignment
        headStr += found.suffix;
      }

      collapse = found.collapse;
    }

    if (headStr !== undefined) {
      if (collapse === undefined) {
        const head = el.ownerDocument!.createElement("div");
        head.className = "head _phantom _start_wrapper";
        head.textContent = this.impliedBrackets ? `[${headStr}]` : headStr;
        head.id = allocateHeadID();
        this.guiUpdater.insertNodeAt(el, 0, head);
      }
      else {
        // If collapse is a string, it is shorthand for a collapse object with
        // the field `kind` set to the value of the string.
        if (typeof collapse === "string") {
          collapse = {
            kind: collapse,
          };
        }
        const collapsible = btwUtil.makeCollapsible(
          el.ownerDocument!,
          collapse.kind,
          this.collapseHeadingIdManager.generate(),
          this.collapseIdManager.generate(),
          {
            panel: collapse.additionalClasses,
            toggle: "arrow-toggle",
          });
        const group = collapsible.group;
        const panelBody = collapsible.content;
        collapsible.heading.textContent = headStr;

        const next = el.nextSibling;
        const parent = el.parentNode as Element;
        this.guiUpdater.removeNode(el);
        panelBody.appendChild(el);
        this.guiUpdater.insertBefore(parent, group, next);
      }
    }
  }

  private _updateHeadingsFor(el: Element, func: ElementToLabel): void {
    // Refresh the headings that use the sense label.
    for (const spec of this.specs) {
      if (spec.labelF === func) {
        const subheaders = el.querySelectorAll(spec.dataSelector);
        // tslint:disable-next-line:prefer-for-of
        for (let shIx = 0; shIx < subheaders.length; ++shIx) {
          const sh = subheaders[shIx];
          this.sectionHeadingDecorator(sh);
        }
      }
    }
  }

  updateHeadingsForSubsense(subsense: Element): void {
    // Refresh the headings that use the subsense label.
    this._updateHeadingsFor(subsense, this.boundGetSubsenseLabel);
  }

  updateHeadingsForSense(sense: Element): void {
    // Refresh the headings that use the sense label.
    this._updateHeadingsFor(sense, this.boundGetSenseLabel);
  }
}
