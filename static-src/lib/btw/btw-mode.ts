/**
 * Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */
import * as $ from "jquery";
import "jquery.cookie";

import { Action, domtypeguards, EditorAPI, gui, transformation } from "wed";
import { GenericModeOptions, Mode } from "wed/modes/generic/generic";

import isElement = domtypeguards.isElement;
import makeElement = transformation.makeElement;
import swapWithNextHomogeneousSibling =
  transformation.swapWithNextHomogeneousSibling;
import swapWithPreviousHomogeneousSibling =
  transformation.swapWithPreviousHomogeneousSibling;
import Transformation = transformation.Transformation;
import TransformationData = transformation.TransformationData;
import Button = gui.button.Button;
import Modal = gui.modal.Modal;

import { BibliographicalItem } from "./bibliography";
import * as btwActions from "./btw-actions";
import { BTWDecorator } from "./btw-decorator";
import * as btwTr from "./btw-tr";
import { Validator } from "./btw-validator";
import { MappedUtil } from "./mapped-util";

// TEMPORARY TYPE DEFINITIONS
// tslint:disable-next-line:no-reserved-keywords no-any
declare var require: any;
// END TEMPORARY TYPE DEFINITIONS

interface Substitution {
  /** The tag name for which to perform the substitution. */
  tag: string;

  /** The type of transformations for which to perform the substitution. */
  trType: string;

  /** The actions to substitute for this tag. */
  actions: Action<{}>[];
}

/**
 * This is an object whose keys are the name of tags. The values can be ``true``
 * if we pass all types of transformations, or a list of transformation types.
 */
type Pass = Record<string, true | string[]>;

/**
 * This is internally used by [[BTWMode]] to determine what to return from
 * [[BTWMode.getContextualActions]].
 *
 * An array of ``TransformationFilter`` is used. For each element of the array,
 * if ``filter.selector`` matches the ``container`` passed to
 * getContextualActions, then for each ``type`` passed to the method:
 *
 * - if ``filter.pass`` is defined and ``filter.pass[tag]`` is:
 *
 *   + ``undefined``, do not continue processing this type. (Note that this will
 *     skip all types, and consequently skips the tag entirely.)
 *
 *   + a list and ``type`` is absent from it, then do not continue processing
 *     this type.
 *
 *   + ``true``, then continue. (Note that this will process all types.)
 *
 * - if ``filter.substitute`` is defined and the ``tag`` and ``type`` parameters
 *   equal the ``tag`` and ``type`` properties of any of the substitutions in
 *   the list, then add the ``actions`` property of the substitution to the
 *   return value.
 *
 * - if ``filter.substitute`` did not apply, then call the method on the parent
 *   class and add the result to the return value.
 *
 * - Once all types have been processed, if ``filter.add`` is defined as a list,
 *   this list of actions is added to the return value.
 */
interface TransformationFilter {
  /** A jQuery selector. */
  selector: string;

  /** The type of transformation to pass, by name of tag. */
  pass?: Pass;

  /** A list of element names. */
  filter?: string[];

  /** A list of substitutions. */
  substitute?: Substitution[];

  /** An array of transformations to add. */
  add?: Transformation<TransformationData>[];
}

export type BibliographicalInfo = Record<string, BibliographicalItem>;

interface BTWModeOptions extends GenericModeOptions {
  bibl_url: string;

  semanticFieldFetchUrl: string;
}

class BTWMode extends Mode<BTWModeOptions> {
  /**
   * These are meant to be used only by helper classes and not outside the
   * mode.
   */
  hyperlinkModal!: Modal;

  semanticFieldFetchUrl: string;
  /** End of fields for helper classes. */

  private getBibliographicalInfoPromise: Promise<BibliographicalInfo> |
    undefined;
  private biblUrl: string;
  private transformationFilters!: TransformationFilter[];
  private mapped!: MappedUtil;

  replaceSemanticFields!: Transformation<btwTr.SemanticFieldTransformationData>;
  editSemanticFieldAction!: btwActions.EditSemanticFieldsAction;
  replaceBiblPtr!: btwActions.InsertBiblPtrAction;
  insertBiblPtr!: btwActions.InsertBiblPtrAction;
  insertRefText!: Transformation<TransformationData>;
  replaceNoneWithConceptualProximate!: Transformation<TransformationData>;
  replaceNoneWithCognate!: Transformation<TransformationData>;
  replaceNoneWithAntonym!: Transformation<TransformationData>;
  swapWithNextTr!: Transformation<TransformationData>;
  swapWithPrevTr!: Transformation<TransformationData>;
  replaceSelectionWithRefTr!: Transformation<btwTr.TargetedTransformationData>;
  insertRefTr!: Transformation<btwTr.TargetedTransformationData>;
  insertPtrTr!: Transformation<btwTr.TargetedTransformationData>;
  insertExamplePtrAction!: btwActions.ExamplePtrDialogAction;
  insertSensePtrAction!: btwActions.SensePtrDialogAction;
  setLanguageToSanskritTr!: btwTr.SetTextLanguageTr;
  setLanguageToPaliTr!: btwTr.SetTextLanguageTr;
  setLanguageToLatinTr!: btwTr.SetTextLanguageTr;

  constructor(editor: EditorAPI, options: BTWModeOptions) {
    options.metadata = require.toUrl("./btw-storage-metadata.json");
    const biblUrl = options.bibl_url;
    delete options.bibl_url;
    const semanticFieldFetchUrl = options.semanticFieldFetchUrl;
    delete options.semanticFieldFetchUrl;
    super(editor, options);
    this.semanticFieldFetchUrl = semanticFieldFetchUrl;
    this.biblUrl = biblUrl;
    // We can initiate this right away. It is fine to ignore the promise. We're
    // just starting the operation.
    // tslint:disable-next-line:no-floating-promises
    this.getBibliographicalInfo();

    this.wedOptions.metadata = {
      name: "BTW Mode",
      authors: ["Louis-Dominique Dubeau"],
      description: "This is a mode for use with BTW.",
      license: "MPL 2.0",
      copyright: "2013-2016 Mangalam Research Center for Buddhist Languages",
    };

    this.wedOptions.label_levels.max = 2;
    this.wedOptions.attributes = "hide";
  }

  // tslint:disable-next-line:max-func-body-length
  async init(): Promise<void> {
    await super.init();

    const mapped = this.mapped =
      new MappedUtil(this.getAbsoluteNamespaceMappings());

    const editor = this.editor;
    this.hyperlinkModal = editor.makeModal();
    this.hyperlinkModal.setTitle("Insert hyperlink to sense");
    this.hyperlinkModal.addButton("Insert", true);
    this.hyperlinkModal.addButton("Cancel");

    this.insertSensePtrAction = new btwActions.SensePtrDialogAction(
      editor, "Insert a new hyperlink to a sense",
      undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.insertExamplePtrAction = new btwActions.ExamplePtrDialogAction(
      editor, "Insert a new hyperlink to an example",
      undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.insertPtrTr = new Transformation(
      editor, "add", "Insert a pointer", btwTr.insertPtr);

    this.insertRefTr = new Transformation(
      editor, "add", "Insert a reference", btwTr.insertRef);

    this.replaceSelectionWithRefTr = new Transformation(
      editor, "wrap", "Replace the selection with a reference",
      btwTr.replaceSelectionWithRef);

    this.swapWithPrevTr = new Transformation(
      editor, "swap-with-previous", "Swap with previous sibling", undefined,
      "<i class='fa fa-long-arrow-up fa-fw'></i>",
      (trEditor, data) => {
        swapWithPreviousHomogeneousSibling(trEditor, data.node as Element);
      });

    this.swapWithNextTr = new Transformation(
      editor, "swap-with-next", "Swap with next sibling", undefined,
      "<i class='fa fa-long-arrow-down fa-fw'></i>",
      (trEditor, data) => {
        swapWithNextHomogeneousSibling(trEditor, data.node as Element);
      });

    this.setLanguageToSanskritTr =
      new btwTr.SetTextLanguageTr(editor, "Sanskrit");
    this.setLanguageToPaliTr = new btwTr.SetTextLanguageTr(editor, "Pāli");
    this.setLanguageToLatinTr = new btwTr.SetTextLanguageTr(editor, "Latin");

    this.replaceNoneWithAntonym = btwTr.makeReplaceNone(editor, "btw:antonym");

    this.replaceNoneWithCognate = btwTr.makeReplaceNone(editor, "btw:cognate");

    this.replaceNoneWithConceptualProximate =
      btwTr.makeReplaceNone(editor, "btw:conceptual-proximate");

    this.insertRefText = new Transformation(
      editor, "add", "Add custom text to reference",
      (trEditor) => {
        const caret = trEditor.caretManager.caret;
        if (caret === undefined) {
          throw new Error("no caret");
        }
        const ref = $(caret.node).closest(
          mapped.classFromOriginalName("ref"))[0];
        const ph = trEditor.insertTransientPlaceholderAt(caret.make(
          ref, ref.childNodes.length));

        const decorator = trEditor.modeTree.getDecorator(caret.node);
        if (!(decorator instanceof BTWDecorator)) {
          throw new Error("the decorator must be a BTWDecorator");
        }

        decorator.refreshElement(caret.root as Element, ref);
        trEditor.caretManager.setCaret(ph, 0);
      });

    this.insertBiblPtr = new btwActions.InsertBiblPtrAction(
      editor,
      "Insert a new bibliographical reference",
      "",
      "<i class='fa fa-book fa-fw'></i>",
      true);

    // Yes, we inherit from InsertBiblPtrAction even though we are
    // replacing.
    this.replaceBiblPtr = new btwActions.InsertBiblPtrAction(
      editor,
      "Replace the selection with a bibliographical reference",
      "",
      "<i class='fa fa-book fa-fw'></i>",
      true);

    this.editSemanticFieldAction = new btwActions.EditSemanticFieldsAction(
      editor, "Edit semantic fields",
      undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.replaceSemanticFields = new Transformation(
      editor, "transform", "Replace semantic fields",
      btwTr.replaceSemanticFields);

    const passInCit: Pass = {
      "btw:lemma-instance": true,
      "btw:antonym-instance": true,
      "btw:cognate-instance": true,
      "btw:conceptual-proximate-instance": true,
      p: true,
      lg: true,
      ref: ["insert", "wrap"],
    };

    const passInTr = $.extend({}, passInCit);
    delete passInTr.ref;

    const passInForeign = $.extend({}, passInTr);
    delete passInForeign.p;
    delete passInForeign.lg;
    passInForeign.foreign = ["delete-parent", "unwrap"];

    this.transformationFilters = [{
      selector: mapped.toGUISelector("btw:sf, btw:semantic-fields"),
      pass: {
        "btw:sf": true,
      },
      substitute: [
        { tag: "btw:sf", trType: "insert",
          actions: [this.editSemanticFieldAction] },
      ],
    }, {
      selector: mapped.toGUISelector("btw:overview, btw:definition"),
      pass: {},
    }, {
      selector: mapped.toGUISelector("btw:sense-discrimination"),
      pass: {
        "btw:sense": true,
      },
    }, { // paragraph in a definition
      selector: mapped.toGUISelector("btw:definition>p"),
      pass: {
        "btw:sense-emphasis": true,
        ptr: true,
      },
      substitute: [{ tag: "ptr",
                     trType: "insert",
                     actions: [this.insertSensePtrAction],
                   }],
    }, {
      selector: mapped.classFromOriginalName("ptr"),
      pass: { ptr: ["delete-parent"] },
    }, {
      selector: mapped.classFromOriginalName("ref"),
      pass: {
        ref: ["delete-parent", "insert"],
      },
      substitute: [
        { tag: "ref", trType: "insert", actions: [this.insertRefText] },
      ],
    }, {
      selector: mapped.classFromOriginalName("btw:citations"),
      substitute: [
        { tag: "ptr", trType: "insert",
          actions: [this.insertExamplePtrAction] },
      ],
    }, {
      selector: mapped.toGUISelector("btw:tr"),
      pass: passInTr,
    }, {
      selector: mapped.toGUISelector("btw:cit"),
      pass: passInCit,
      substitute: [
        { tag: "ref",
          trType: "insert",
          actions: [this.insertBiblPtr],
        },
        { tag: "ref",
          trType: "wrap",
          actions: [this.replaceBiblPtr],
        },
      ],
    }, {
      selector: mapped.toGUISelector(
        "btw:citations foreign, btw:other-citations foreign"),
      pass: passInForeign,
    }, {
      selector: mapped.classFromOriginalName("foreign"),
      pass: {
        foreign: ["delete-parent", "unwrap"],
      },
    }, {
      selector: mapped.toGUISelector("btw:antonyms>btw:none"),
      substitute: [
        { tag: "btw:none",
          trType: "delete-parent",
          actions: [this.replaceNoneWithAntonym] },
      ],
    }, {
      selector: mapped.toGUISelector("btw:cognates>btw:none"),
      substitute: [
        { tag: "btw:none",
          trType: "delete-parent",
          actions: [this.replaceNoneWithCognate] },
      ],
    }, {
      selector: mapped.toGUISelector("btw:conceptual-proximates>btw:none"),
      substitute: [
        { tag: "btw:none",
          trType: "delete-parent",
          actions: [this.replaceNoneWithConceptualProximate] },
      ],
    }, {
      selector: mapped.classFromOriginalName("btw:term"),
      // We don't want to let anything go through because this
      // can contain only text or a foreign element.
      pass: {},
    }, {
      selector: mapped.classFromOriginalName("lg"),
      pass: {
        l: true,
      },
    }, {
      selector: mapped.toGUISelector("*"),
      substitute: [
        { tag: "ref", trType: "insert", actions: [this.insertBiblPtr] },
        { tag: "ref", trType: "wrap", actions: [this.replaceBiblPtr] },
      ],
    }];
  }

  /**
   * This is meant to be called by helper classes.
   */
  async getBibliographicalInfo(): Promise<BibliographicalInfo> {
    if (this.getBibliographicalInfoPromise === undefined) {
      this.getBibliographicalInfoPromise =
        this.makeGetBibliographicalInfoPromise();
    }

    return this.getBibliographicalInfoPromise;
  }

  private async makeGetBibliographicalInfoPromise():
  Promise<BibliographicalInfo> {
    // tslint:disable-next-line:no-any
    let data: any;
    try {
      data = await Promise.resolve($.ajax({
        url: this.biblUrl,
        headers: {
          Accept: "application/json",
        },
      }));
    }
    catch {
      throw new Error("cannot load bibliographical information");
    }

    const urlToItem = Object.create(null);
    for (const item of data) {
      urlToItem[item.abstract_url] = item;
    }
    return urlToItem;
  }

  makeDecorator(): BTWDecorator {
    const ret = new BTWDecorator(this.semanticFieldFetchUrl, this,
                                 this.metadata, this.options, this.mapped,
                                 this.editor);

    // This is as good a place as any where to attach listeners to the data
    // updater directly. Note that we attach to the updater rather than the
    // domlistener because otherwise we would trigger a data update from a GUI
    // update, which is likely to result in issues. (Crash, infinite loop, etc.)

    const noneEName = this.resolver.resolveName("btw:none");
    if (noneEName === undefined) {
      throw new Error("cannot resolve btw:none!");
    }

    const updater = this.editor.dataUpdater;
    updater.events.subscribe((ev) => {
      if (ev.name !== "DeleteNode") {
        return;
      }

      const el = ev.node;

      if (!isElement(el) ||
          !(el.tagName === "btw:antonym" ||
            el.tagName === "btw:cognate" ||
            el.tagName === "btw:conceptual-proximate")) {
        return;
      }

      if ((ev.formerParent as Element).childElementCount === 0) {
        this.editor.dataUpdater.insertBefore(
          ev.formerParent as Element,
          makeElement(el.ownerDocument!, noneEName.ns, "btw:none"),
          null);
      }
    });

    updater.events.subscribe((ev) => {
      if (ev.name !== "InsertNodeAt") {
        return;
      }

      const node = ev.node;

      if (!isElement(node)) {
        return;
      }

      const ed = this.editor;

      function processNode(toProcess: Element): void {
        if (toProcess.childNodes.length !== 0) {
          return;
        }

        ed.dataUpdater.insertBefore(
          toProcess,
          makeElement(toProcess.ownerDocument!, noneEName!.ns, "btw:none"),
          null);
      }

      function processList(nodes: HTMLCollectionOf<Element>): void {
        // tslint:disable-next-line:prefer-for-of
        for (let i = 0; i < nodes.length; ++i) {
          processNode(nodes[i]);
        }
      }

      const antonyms = node.getElementsByTagName("btw:antonyms");
      const cognates = node.getElementsByTagName("btw:cognates");
      const cps = node.getElementsByTagName("btw:conceptual-proximates");
      processList(antonyms);
      processList(cognates);
      processList(cps);

      if (node.tagName === "btw:antonyms" ||
          node.tagName === "btw:cognates" ||
          node.tagName === "btw:conceptual-proximates") {
        processNode(node);
      }
    });

    return ret;
  }

  getToolbarButtons(): Button[] {
    return [
      this.setLanguageToSanskritTr.makeButton(),
      this.setLanguageToPaliTr.makeButton(),
      this.setLanguageToLatinTr.makeButton(),
      this.insertBiblPtr.makeButton(),
    ];
  }

  getContextualActions(transformationType: string[] | string,
                       tag: string,
                       container: Node,
                       offset: number): Action<{}>[] {
    const el = ((container.nodeType === Node.TEXT_NODE) ?
      // tslint:disable-next-line:no-non-null-assertion
      container.parentNode! : container) as Element;
    const guiEl = $.data(el, "wed_mirror_node") as Element;

    if (!(transformationType instanceof Array)) {
      // tslint:disable-next-line:no-parameter-reassignment
      transformationType = [transformationType];
    }

    //
    // Special case:
    //
    // None of the non-inline elements should be able to be unwrapped.
    //
    if (!this.metadata.isInline(guiEl)) {
      const unwrap = transformationType.indexOf("unwrap");
      if (unwrap !== -1) {
        transformationType.splice(unwrap, 1);
      }
    }

    let ret: Action<{}>[] = [];
    for (const filter of this.transformationFilters) {
      if (guiEl.matches(filter.selector)) {
        typeLoop:
        for (const t of transformationType) {
          if (filter.pass !== undefined) {
            const trTypes = filter.pass[tag];
            if (trTypes === undefined || // not among those to pass
                (trTypes !== true && // true means pass
                 trTypes.indexOf(t) === -1)) {
              // Skip this type...
              continue;
            }
          }

          if (filter.substitute !== undefined) {
            for (const substitute of filter.substitute) {
              if (substitute.tag === tag && substitute.trType === t) {
                ret = ret.concat(substitute.actions);
                break typeLoop;
              }
            }
          }

          ret =
            ret.concat(super.getContextualActions(t, tag, container, offset));
        }

        if (filter.add !== undefined) {
          ret = ret.concat(filter.add);
        }

        // First match of a selector ends the process.
        break;
      }
    }

    // Here we transform the returned array in ways that cannot be captured by
    // transformationFilters.
    return ret.filter((x) => {
      // We want insertRefText to be included only if the current container does
      // not have children.
      if (x !== this.insertRefText) {
        return true;
      }

      return el.childNodes.length === 0;
    });
  }

  getStylesheets(): string[] {
    return [require.toUrl("./btw-mode.css")];
  }

  getValidator(): Validator {
    return new Validator(this.editor.guiRoot, this.mapped);
  }
}

export { BTWMode as Mode };
