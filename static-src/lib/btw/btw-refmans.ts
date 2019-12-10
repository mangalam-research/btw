import { convert, domutil, labelman } from "wed";
import LabelManager = labelman.LabelManager;
import mustGetMirror = domutil.mustGetMirror;

import { MappedUtil } from "./mapped-util";

const senseLabels = "abcdefghijklmnopqrstuvwxyz";

export class SubsenseReferenceManager extends LabelManager {
  private nextLabel: number = 0;

  constructor(private readonly parentRefman: LabelManager,
              private readonly parentId: string) {
    super("subsense");
    this.nextLabel = 1;
  }

  allocateLabel(id: string): string {
    let label = this._idToLabel[id];
    if (label === undefined) {
      label = this._idToLabel[id] = String(this.nextLabel++);
    }
    return label;
  }

  /**
   * @param id The element id of the element for which to get a label.
   *
   * @returns The complete label: this includes the parent sense's label and the
   * child subsense's label, combined. For instance if the parent has label
   * `"a"` and the subsense has label `"1"`, the return value is `"a1"`. Compare
   * with the return value of [[idToSublabel]].
   */
  idToLabel(id: string): string | undefined {
    const parentLabel = this.parentRefman.idToLabel(this.parentId);

    if (parentLabel === undefined) {
      return undefined;
    }

    const thisLabel = super.idToLabel(id);

    if (thisLabel === undefined) {
      return undefined;
    }

    return parentLabel + thisLabel;
  }

  idToLabelForHead(id: string): string | undefined {
    return this.idToLabel(id);
  }

  /**
   * @param id The element id of the element for which to get a label.
   *
   * @returns Only the label that pertains to the subsense, independent of the
   * parent sense's label. Compare with the value returned from [[idToLabel]].
   */
  idToSublabel(id: string): string | undefined {
    return super.idToLabel(id);
  }

  _deallocateAllLabels(): void {
    this.nextLabel = 1;
  }
}

export class SenseReferenceManager extends LabelManager {
  private readonly subsenseReferenceManagers:
  Record<string, SubsenseReferenceManager> = Object.create(null);

  private nextSenseLabelIx: number = 0;

  constructor() {
    super("sense");
  }

  allocateLabel(id: string): string {
    if (!(id in this.subsenseReferenceManagers)) {
      this.subsenseReferenceManagers[id] =
        new SubsenseReferenceManager(this, id);
    }

    let label = this._idToLabel[id];
    if (label === undefined) {
      // More than 26 senses in a single article seems much.
      if (this.nextSenseLabelIx >= senseLabels.length) {
        throw new Error("hit the hard limit of 26 sense labels in a " +
                        "single article");
      }

      label = this._idToLabel[id] = senseLabels[this.nextSenseLabelIx++];
    }

    return label;
  }

  idToLabelForHead(id: string): string | undefined {
    const label = this.idToLabel(id);
    return (label === undefined) ? undefined : label.toUpperCase();
  }

  idToSubsenseRefman(id: string): SubsenseReferenceManager {
    return this.subsenseReferenceManagers[id];
  }

  _deallocateAllLabels(): void {
    this.nextSenseLabelIx = 0;
    // tslint:disable-next-line:forin
    for (const id in this.subsenseReferenceManagers) {
      this.subsenseReferenceManagers[id].deallocateAll();
    }
  }
}

// This one does not inherit from the ReferenceManager class.
export class ExampleReferenceManager {
  readonly name: string = "example";

  constructor(private readonly mapped: MappedUtil) {}

  idToLabel(): undefined {
    return undefined;
  }

  getPositionalLabel(ptr: Element, target: Element): string {
    const guiTarget = mustGetMirror(target) as HTMLElement;
    const ref = guiTarget
      .querySelector(this.mapped.toGUISelector("btw:cit ref"))!
      .cloneNode(true) as HTMLElement;
    const toRemove = ref.querySelectorAll("._gui, ._decoration_text");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < toRemove.length; ++i) {
      const it = toRemove[i];
      it.parentNode!.removeChild(it);
    }
    let ret = `See ${ref.textContent} quoted `;
    const order = ptr.compareDocumentPosition(target);
    // tslint:disable-next-line:no-bitwise
    if ((order & Node.DOCUMENT_POSITION_DISCONNECTED) !== 0) {
      throw new Error("disconnected nodes");
    }

    // tslint:disable-next-line:no-bitwise
    if ((order & Node.DOCUMENT_POSITION_CONTAINS) !== 0) {
      throw new Error("ptr contains example!");
    }

    // order & Node.DOCUMENT_POSITION_IS_CONTAINED
    // This could happen and we don't care...

    // tslint:disable-next-line:no-bitwise
    ret += ((order & Node.DOCUMENT_POSITION_PRECEDING) !== 0) ?
      "above" : "below";

    if (guiTarget != null) {
      let parent = guiTarget.parentNode;
      let head: Element | null;
      while (parent !== null) {
        head = domutil.childByClass(parent, "head");
        if (head !== null) {
          break;
        }

        parent = parent.parentNode;
      }

      ret += ` in ${head!.textContent}`;

      //
      // This seems a bit backwards at first but what we want here is not the
      // term under which the *referred* example (the target of the pointer)
      // appears but the term under which the *pointer* to the example appears.
      //
      // Basically, the text of the link means "See [referred work] quoted
      // [above/below] in [this heading], [and in the quote look for this
      // term]." The term to look for is the term under which the pointer is
      // located, not the term under which the example (the target of the
      // pointer) is located.
      //
      parent = mustGetMirror(ptr).parentNode;
      while (parent !== null) {
        const guiTerm = parent.querySelector(".btw\\:term");
        if (guiTerm !== null) {
          const term = mustGetMirror(guiTerm);

          // Drop the period, since we're adding a comma.
          if (ret[ret.length - 1] === ".") {
            ret = ret.slice(0, -1);
          }
          ret += `, ${term.textContent}`;
          break;
        }

        parent = parent.parentNode;
      }
    }

    // Don't duplicate the period.
    if (ret[ret.length - 1] !== ".") {
      ret += ".";
    }

    return ret;
  }
}

function closestSense(el: Element): Element | null {
  let what: Element | null = el;
  while (what !== null) {
    if (what.classList.contains("btw:sense")) {
      return what;
    }

    what = what.parentNode as (Element | null);
  }

  return null;
}

export class WholeDocumentManager {
  private readonly senseRefman: SenseReferenceManager =
    new SenseReferenceManager();
  private readonly exampleRefman: ExampleReferenceManager =
    new ExampleReferenceManager(this.mapped);

  constructor(private readonly mapped: MappedUtil) {}

  getSenseLabelForHead(el: Element): string | undefined {
    const id = el.id;
    if (id === "") {
      throw new Error(`element does not have an id: ${el}`);
    }

    return this.senseRefman.idToLabelForHead(id);
  }

  getSenseLabel(el: Element): string | undefined {
    let what: Element | null = el;
    let sense: Element | undefined;
    while (what !== null) {
      if (what.classList.contains("btw:sense")) {
        sense = what;
        break;
      }

      what = what.parentNode as (Element | null);
    }

    const id = sense !== undefined ? sense.id : undefined;

    if (id === undefined) {
      throw new Error(`element does not have sense parent with an id: ${el}`);
    }

    return this.senseRefman.idToLabel(id);
  }

  getSubsenseLabel(el: Element): string | undefined {
    const refman = this.getSubsenseRefman(el);
    if (refman === null) {
      return undefined;
    }

    let what: Element | null = el;
    let subsense: Element | undefined;
    while (what !== null) {
      if (what.classList.contains("btw:subsense")) {
        subsense = what;
        break;
      }

      what = what.parentNode as (Element | null);
    }

    const id = subsense !== undefined ? subsense.id : undefined;
    if (id === undefined) {
      // This can happen during the decoration of the tree because there is in
      // general no guarantee about the order in which elements are decorated. A
      // second pass will ensure that the label is not undefined.
      return undefined;
    }

    return refman.idToLabelForHead(id);
  }

  /**
   * @param el The element for which we want the subsense reference
   * manager. This element must be a child of a ``btw:sense`` element or be a
   * ``btw:sense`` element.
   *
   * @returns The subsense reference manager.
   */
  getSubsenseRefman(el: Element): SubsenseReferenceManager | null {
    const sense = closestSense(el);
    if (sense === null) {
      return null;
    }
    return this.senseRefman.idToSubsenseRefman(sense.id);
  }

  getRefmanForElement(el: Element):
  LabelManager | ExampleReferenceManager | null {
    switch ((mustGetMirror(el) as Element).tagName) {
    case "ptr":
    case "ref":
      // Find the target and return its value
      const targetAttr = el.getAttribute(convert.encodeAttrName("target"));
      if (targetAttr === null) {
        return null;
      }

      // Slice to drop the #.
      const target =
        el.ownerDocument!.getElementById(`BTW-${targetAttr.slice(1)}`);
      return target !== null ? this.getRefmanForElement(target) : null;
    case "btw:sense":
      return this.senseRefman;
    case "btw:subsense":
      const sense = closestSense(el);
      if (sense === null) {
        return null;
      }
      return this.senseRefman.idToSubsenseRefman(sense.id);
    case "btw:example":
    case "btw:example-explained":
      return this.exampleRefman;
    default:
      throw new Error(`unexpected element: ${el}`);
    }
  }
}
