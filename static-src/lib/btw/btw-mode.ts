/**
 * Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */
import * as Promise from "bluebird";
import * as $ from "jquery";
import "jquery.cookie";
import "rangy";

import * as dloc from "wed/dloc";
import * as domutil from "wed/domutil";
import { Mode } from "wed/modes/generic/generic";
import * as transformation from "wed/transformation";
import * as util from "wed/util";

import * as btwActions from "./btw-actions";
import { BTWDecorator } from "./btw-decorator";
import * as btwMeta from "./btw-meta";
import { Toolbar } from "./btw-toolbar";
import * as btwTr from "./btw-tr";
import { Validator } from "./btw-validator";

// TEMPORARY TYPE DEFINITIONS
/* tslint:disable: no-any */
declare var require: any;

type Action = any;
type Transformation = any;
type Modal = any;
type Options = any;
type WedOptions = any;
type Editor = any;
type Decorator = any;
/* tslint:enable: no-any */
// END TEMPORARY TYPE DEFINITIONS

interface Substitution {
  /** The tag name for which to perform the substitution. */
  tag: string;

  /** The type of transformations for which to perform the substitution. */
  type: string;

  /** The actions to substitute for this tag. */
  actions: Action[];
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
  add?: Transformation[];
}

export type BibliographicalInfo = Record<string, string>;

class BTWMode extends Mode {
  /* from parent */
  /* tslint:disable: no-any */
  private _meta: any;
  private _resolver: any;
  private _editor: Editor;
  public documentationLinkFor: any;
  public getAbsoluteResolver: any;
  /* tslint:enable: no-any */
  /* END from parent */

  /**
   * These are meant to be used only by helper classes and not outside the
   * mode.
   */
  hyperlinkModal: Modal;

  semanticFieldFetchUrl: string;
  /** End of fields for helper classes. */

  private getBibliographicalInfoPromise: Promise<BibliographicalInfo> |
    undefined;
  private toolbar: Toolbar;
  private biblUrl: string;
  // tslint:disable-next-line:variable-name
  private _wed_options: WedOptions;
  private transformationFilters: TransformationFilter[];

  replaceSemanticFields: Transformation;
  editSemanticFieldAction: Action;
  replaceBiblPtr: Action;
  insertBiblPtr: Action;
  insertRefText: Transformation;
  replaceNoneWithConceptualProximate: Transformation;
  replaceNoneWithCognate: Transformation;
  replaceNoneWithAntonym: Transformation;
  swapWithNextTr: Transformation;
  swapWithPrevTr: Transformation;
  replaceSelectionWithRefTr: Transformation;
  insertRefTr: Transformation;
  insertPtrTr: Transformation;
  insertExamplePtrAction: Action;
  insertSensePtrAction: Action;

  constructor(options: Options) {
    options.meta = {
      path: btwMeta,
      options: {
        metadata: require.toUrl("./btw-storage-metadata.json"),
      },
    };
    const biblUrl = options.bibl_url;
    delete options.bibl_url;
    const semanticFieldFetchUrl = options.semanticFieldFetchUrl;
    delete options.semanticFieldFetchUrl;
    super(options);
    this.semanticFieldFetchUrl = semanticFieldFetchUrl;
    this.biblUrl = biblUrl;
    // We can initiate this right away.
    this.getBibliographicalInfo();

    this._wed_options.metadata = {
      name: "BTW Mode",
      authors: ["Louis-Dominique Dubeau"],
      description: "This is a mode for use with BTW.",
      license: "MPL 2.0",
      copyright: "2013-2016 Mangalam Research Center for Buddhist Languages",
    };

    this._wed_options.label_levels.max = 2;
    this._wed_options.attributes = "hide";
  }

  init(editor: Editor): void {
    super.init(editor);

    this.hyperlinkModal = editor.makeModal();
    this.hyperlinkModal.setTitle("Insert hyperlink to sense");
    this.hyperlinkModal.addButton("Insert", true);
    this.hyperlinkModal.addButton("Cancel");

    editor.setNavigationList("");

    this.insertSensePtrAction = new btwActions.SensePtrDialogAction(
      editor, "Insert a new hyperlink to a sense",
      undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.insertExamplePtrAction = new btwActions.ExamplePtrDialogAction(
      editor, "Insert a new hyperlink to an example",
      undefined, "<i class='fa fa-plus fa-fw'></i>", true);

    this.insertPtrTr = new transformation.Transformation(
      editor, "add", "Insert a pointer", btwTr.insertPtr);

    this.insertRefTr = new transformation.Transformation(
      editor, "add", "Insert a reference", btwTr.insertRef);

    this.replaceSelectionWithRefTr = new transformation.Transformation(
      editor, "wrap", "Replace the selection with a reference",
      btwTr.replaceSelectionWithRef);

    this.swapWithPrevTr = new transformation.Transformation(
      editor, "swap-with-previous", "Swap with previous sibling", undefined,
      "<i class='fa fa-long-arrow-up fa-fw'></i>",
      (trEditor, data) => transformation.swapWithPreviousHomogeneousSibling(
        trEditor, data.node));

    this.swapWithNextTr = new transformation.Transformation(
      editor, "swap-with-next", "Swap with next sibling", undefined,
      "<i class='fa fa-long-arrow-down fa-fw'></i>",
      (trEditor, data) => transformation.swapWithNextHomogeneousSibling(
        trEditor, data.node));

    this.replaceNoneWithAntonym = btwTr.makeReplaceNone(editor, "btw:antonym");

    this.replaceNoneWithCognate = btwTr.makeReplaceNone(editor, "btw:cognate");

    this.replaceNoneWithConceptualProximate =
      btwTr.makeReplaceNone(editor, "btw:conceptual-proximate");

    this.insertRefText = new transformation.Transformation(
      editor, "add", "Add custom text to reference",
      (trEditor) => {
        const caret = trEditor.getGUICaret();
        const ref = $(caret.node).closest(util.classFromOriginalName("ref"))[0];
        const ph = trEditor.insertTransientPlaceholderAt(caret.make(
          ref, ref.childNodes.length));
        trEditor.decorator.refreshElement(dloc.findRoot(ref).node, ref);
        trEditor.setGUICaret(ph, 0);
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

    this.replaceSemanticFields = new transformation.Transformation(
      editor, undefined, "Replace semantic fields",
      btwTr.replaceSemanticFields);

    this.toolbar = new Toolbar(this, editor);
    const toolbarTop = this.toolbar.top;
    editor.widget.insertBefore(toolbarTop, editor.widget.firstChild);
    editor.excludeFromBlur(toolbarTop);

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
      selector: domutil.toGUISelector("btw:sf, btw:semantic-fields"),
      pass: {
        "btw:sf": true,
      },
      substitute: [
        { tag: "btw:sf", type: "insert",
          actions: [this.editSemanticFieldAction] },
      ],
    }, {
      selector: domutil.toGUISelector(
        ["btw:overview",
         "btw:definition"].join(",")),
      pass: {},
    }, {
      selector: domutil.toGUISelector("btw:sense-discrimination"),
      pass: {
        "btw:sense": true,
      },
    }, { // paragraph in a definition
      selector: domutil.toGUISelector("btw:definition>p"),
      pass: {
        "btw:sense-emphasis": true,
        ptr: true,
      },
      substitute: [{ tag: "ptr",
                     type: "insert",
                     actions: [this.insertSensePtrAction],
                   }],
    }, {
      selector: util.classFromOriginalName("ptr"),
      pass: { ptr: ["delete-parent"] },
    }, {
      selector: util.classFromOriginalName("ref"),
      pass: {
        ref: ["delete-parent", "insert"],
      },
      substitute: [
        { tag: "ref", type: "insert", actions: [this.insertRefText] },
      ],
    }, {
      selector: util.classFromOriginalName("btw:citations"),
      substitute: [
        { tag: "ptr", type: "insert",
          actions: [this.insertExamplePtrAction] },
      ],
    }, {
      selector: domutil.toGUISelector("btw:tr"),
      pass: passInTr,
    }, {
      selector: domutil.toGUISelector("btw:cit"),
      pass: passInCit,
      substitute: [
        { tag: "ref",
          type: "insert",
          actions: [this.insertBiblPtr],
        },
        { tag: "ref",
          type: "wrap",
          actions: [this.replaceBiblPtr],
        },
      ],
    }, {
      selector: domutil.toGUISelector(
        "btw:citations foreign, btw:other-citations foreign"),
      pass: passInForeign,
    }, {
      selector: util.classFromOriginalName("foreign"),
      pass: {
        foreign: ["delete-parent", "unwrap"],
      },
    }, {
      selector: domutil.toGUISelector("btw:antonyms>btw:none"),
      substitute: [
        { tag: "btw:none",
          type: "delete-parent",
          actions: [this.replaceNoneWithAntonym] },
      ],
    }, {
      selector: domutil.toGUISelector("btw:cognates>btw:none"),
      substitute: [
        { tag: "btw:none",
          type: "delete-parent",
          actions: [this.replaceNoneWithCognate] },
      ],
    }, {
      selector: domutil.toGUISelector("btw:conceptual-proximates>btw:none"),
      substitute: [
        { tag: "btw:none",
          type: "delete-parent",
          actions: [this.replaceNoneWithConceptualProximate] },
      ],
    }, {
      selector: util.classFromOriginalName("btw:term"),
      // We don't want to let anything go through because this
      // can contain only text or a foreign element.
      pass: {},
    }, {
      selector: util.classFromOriginalName("lg"),
      pass: {
        l: true,
      },
    }, {
      selector: domutil.toGUISelector("*"),
      substitute: [
        { tag: "ref", type: "insert", actions: [this.insertBiblPtr] },
        { tag: "ref", type: "wrap", actions: [this.replaceBiblPtr] },
      ],
    }];
  }

  /**
   * This is meant to be called by helper classes.
   */
  getBibliographicalInfo(): Promise<BibliographicalInfo> {
    if (this.getBibliographicalInfoPromise !== undefined) {
      return this.getBibliographicalInfoPromise;
    }

    return (this.getBibliographicalInfoPromise =
            Promise.resolve($.ajax({
              url: this.biblUrl,
              headers: {
                Accept: "application/json",
              },
            })).bind(this)
            .catch((_jqXHR) => {
              throw new Error("cannot load bibliographical information");
            }).then((data) => {
              const urlToItem = Object.create(null);
              for (const item of data) {
                urlToItem[item.abstract_url] = item;
              }
              return urlToItem;
            }));
  }

  makeDecorator(): Decorator {
    // Wed calls this with (domlistener, editor, gui_updater).
    const obj = Object.create(BTWDecorator.prototype);
    // Make arg an array and add our extra argument(s).
    let args = Array.prototype.slice.call(arguments);
    args = [this.semanticFieldFetchUrl, this, this._meta].concat(args);
    BTWDecorator.apply(obj, args);

    // This is as good a place as any where to attach listeners to the
    // data updater directly. Note that we attach to the updater
    // rather than the domlistener because otherwise we would trigger
    // a data update from a GUI update, which is likely to result in
    // issues. (Crash, infinite loop, etc.)

    const noneEName = this._resolver.resolveName("btw:none");

    const updater = this._editor.data_updater;
    updater.addEventListener("deleteNode", (ev) => {
      const el = ev.node;
      if (!(el.tagName === "btw:antonym" ||
            el.tagName === "btw:cognate" ||
            el.tagName === "btw:conceptual-proximate")) {
        return;
      }

      if (ev.former_parent.childElementCount === 0) {
        this._editor.data_updater.insertBefore(
          ev.former_parent,
          transformation.makeElement(el.ownerDocument,
                                     noneEName.ns, "btw:none"),
          null);
      }
    });

    updater.addEventListener("insertNodeAt", (ev) => {
      const ed = this._editor;

      function processNode(node: Node): void {
        if (node.childNodes.length === 0) {
          ed.data_updater.insertBefore(
            node,
            transformation.makeElement(node.ownerDocument,
                                       noneEName.ns,
                                       "btw:none"), null);
        }
      }
      function processList(nodes: NodeListOf<Element>): void {
        // tslint:disable-next-line:prefer-for-of
        for (let i = 0; i < nodes.length; ++i) {
          const node = nodes[i];
          processNode(node);
        }
      }

      const node = ev.node;

      if (node.nodeType !== Node.ELEMENT_NODE) {
        return;
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

    return obj;
  }

  getContextualActions(type: string[] | string,
                       tag: string, container: Node, offset: number): Action[] {
    const el = ((container.nodeType === Node.TEXT_NODE) ?
      // tslint:disable-next-line:no-non-null-assertion
      container.parentNode! : container) as Element;
    const guiEl = $.data(el, "wed_mirror_node") as Element;

    if (!(type instanceof Array)) {
      type = [type];
    }

    //
    // Special case:
    //
    // None of the non-inline elements should be able to be unwrapped.
    //
    if (!(this._meta.isInline(guiEl) as boolean)) {
      const unwrap = type.indexOf("unwrap");
      if (unwrap !== -1) {
        type.splice(unwrap, 1);
      }
    }

    let ret: Action[] = [];
    for (const filter of this.transformationFilters) {
      if (guiEl.matches(filter.selector)) {
        typeLoop:
        for (const t of type) {
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
              if (substitute.tag === tag && substitute.type === t) {
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
    return new Validator(this._editor.gui_root, this._editor.data_root);
  }
}

export { BTWMode as Mode };
