import * as $ from "jquery";

import * as domutil from "wed/domutil";
import { ReferenceManager } from "wed/refman";
import * as util from "wed/util";

const senseLabels = "abcdefghijklmnopqrstuvwxyz";

export class SubsenseReferenceManager extends ReferenceManager {
  private nextLabel: number = 0;

  // From parent
  // tslint:disable-next-line:variable-name
  readonly _id_to_label: Record<string, string>;
  // End from parent

  constructor(private readonly parentRefman: ReferenceManager,
              private readonly parentId: string) {
    super("subsense");
    this.nextLabel = 1;
  }

  allocateLabel(id: string): string {
    let label = this._id_to_label[id];
    if (label === undefined) {
      label = this._id_to_label[id] = String(this.nextLabel++);
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
  idToLabel(id: string): string {
    // tslint:disable-next-line:restrict-plus-operands
    return this.parentRefman.idToLabel(this.parentId) + super.idToLabel(id);
  }

  idToLabelForHead(id: string): string {
    return this.idToLabel(id);
  }

  /**
   * @param id The element id of the element for which to get a label.
   *
   * @returns Only the label that pertains to the subsense, independent of the
   * parent sense's label. Compare with the value returned from [[idToLabel]].
   */
  idToSublabel(id: string): string {
    return super.idToLabel(id);
  }

  _deallocateAllLabels(): void {
    this.nextLabel = 1;
  }
}

export class SenseReferenceManager extends ReferenceManager {
  private readonly subsenseReferenceManagers: Record<string, ReferenceManager> =
    Object.create(null);
  private nextSenseLabelIx: number = 0;

  // From parent
  // tslint:disable-next-line:variable-name
  readonly _id_to_label: Record<string, string>;
  readonly idToLabel: (id: string) => string;
  // End from parent

  constructor() {
    super("sense");
  }

  allocateLabel(id: string): string {
    if (!(id in this.subsenseReferenceManagers)) {
      this.subsenseReferenceManagers[id] =
        new SubsenseReferenceManager(this, id);
    }

    let label = this._id_to_label[id];
    if (label === undefined) {
      // More than 26 senses in a single article seems much.
      if (this.nextSenseLabelIx >= senseLabels.length) {
        throw new Error("hit the hard limit of 26 sense labels in a " +
                        "single article");
      }

      label = this._id_to_label[id] = senseLabels[this.nextSenseLabelIx++];
    }

    return label;
  }

  idToLabelForHead(id: string): string {
    return this.idToLabel(id).toUpperCase();
  }

  idToSubsenseRefman(id: string): ReferenceManager {
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
  private readonly name: string = "example";

  idToLabel(): undefined {
    return undefined;
  }

  getPositionalLabel(ptr: Element, target: Element): string {
    const guiTarget = $.data(target, "wed_mirror_node");
    const ref = guiTarget.querySelector(domutil.toGUISelector("btw:cit ref"))
            .cloneNode(true);
    const toRemove = ref.querySelectorAll("._gui, ._decoration_text");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < toRemove.length; ++i) {
      const it = toRemove[i];
      it.parentNode.removeChild(it);
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

    if (guiTarget) {
      let parent = guiTarget.parentNode;
      let head;
      while (parent) {
        head = domutil.childByClass(parent, "head");
        if (head) {
          break;
        }

        parent = parent.parentNode;
      }

      ret += ` in ${head.textContent}`;

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
      let guiTerm;
      parent = $.data(ptr, "wed_mirror_node").parentNode;
      while (parent) {
        guiTerm = parent.querySelector(".btw\\:term");
        if (guiTerm) {
          break;
        }

        parent = parent.parentNode;
      }

      if (guiTerm) {
        const term = $.data(guiTerm, "wed_mirror_node");

        // Drop the period, since we're adding a comma.
        if (ret[ret.length - 1] === ".") {
          ret = ret.slice(0, -1);
        }
        ret += `, ${term.textContent}`;
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
    new ExampleReferenceManager();

  getSenseLabelForHead(el: Element): string {
    const id = el.id;
    if (id === "") {
      throw new Error(`element does not have an id: ${el}`);
    }
    return this.senseRefman.idToLabelForHead(id);
  }

  getSenseLabel(el: Element): string {
    let what: Element | null = el;
    let sense;
    while (what !== null) {
      if (what.classList.contains("btw:sense")) {
        sense = what;
        break;
      }

      what = what.parentNode as (Element | null);
    }

    const id = sense && sense.id;

    if (!id) {
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
    let subsense;
    while (what !== null) {
      if (what.classList.contains("btw:subsense")) {
        subsense = what;
        break;
      }

      what = what.parentNode as (Element | null);
    }

    const id = subsense && subsense.id;
    if (!id) {
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

  getRefmanForElement(el: Element): ReferenceManager | null {
    const name = util.getOriginalName(el);
    switch (name) {
    case "ptr":
    case "ref":
      // Find the target and return its value
      const targetAttr = el.getAttribute(util.encodeAttrName("target"));
      if (targetAttr === null) {
        return null;
      }

      // Slice to drop the #.
      const target =
        el.ownerDocument.getElementById(`BTW-${targetAttr.slice(1)}`);
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
