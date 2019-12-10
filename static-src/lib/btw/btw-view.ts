/**
 * Code for viewing documents edited by btw-mode.
 * @author Louis-Dominique Dubeau
 */
import * as bluejax from "bluejax";
import "bootstrap";
import * as $ from "jquery";
import * as _ from "lodash";
import { DefaultNameResolver } from "salve";

import { convert, DLocRoot, domtypeguards, domutil, transformation,
         treeUpdater } from "wed";
import TreeUpdater = treeUpdater.TreeUpdater;
import isElement = domtypeguards.isElement;
import getMirror = domutil.getMirror;

import { Metadata } from "wed/modes/generic/metadata";
import { MetadataMultiversionReader,
       } from "wed/modes/generic/metadata-multiversion-reader";

import { ajax } from "../ajax";
import { BibliographicalItem, isPrimarySource } from "./bibliography";
import { DispatchEditor, DispatchMixin, DispatchMode } from "./btw-dispatch";
import { HeadingDecorator } from "./btw-heading-decorator";
import { BibliographicalInfo } from "./btw-mode";
import { WholeDocumentManager } from "./btw-refmans";
import * as metadataJSON from "./btw-storage-metadata.json";
import { BTW_NS, getOriginalNameIfPossible, makeCollapsible } from "./btw-util";
import { IDManager } from "./id-manager";
import { MappedUtil } from "./mapped-util";
import { SFFetcher } from "./semantic-field-fetcher";

const closest = domutil.closest;

const FAKE_EDITOR = {
  toDataNode(node: Node): Node {
    return node;
  },
};

const FAKE_MODE = {
  nodesAroundEditableContents(): [null, null] {
    return [null, null];
  },
  async getBibliographicalInfo(): Promise<BibliographicalInfo> {
    // This should never be called when we use a view object. We override
    // the method that *would* call it, with a method that does not.
    throw new Error("called getBibliographicalInfo");
  },
};

function makeExpandHandler(affix: HTMLElement, affixConstrainer: HTMLElement,
                           frame: Element): (ev: JQueryEventObject) => void {
  const $affix = $(affix);
  return (ev: JQueryEventObject) => {
    if (affix.classList.contains("expanding")) {
      return;
    }

    const constrainerRect = affixConstrainer.getBoundingClientRect();

    if (!affix.classList.contains("expanded")) {
      affix.classList.add("expanding");
      affix.style.left = `${constrainerRect.left}px`;
      affix.style.width = `${affixConstrainer.offsetWidth}px`;
      const frameRect = frame.getBoundingClientRect();
      $affix.animate({
        left: frameRect.left,
        width: frameRect.width,
      }, 1000, () => {
        affix.classList.remove("expanding");
        affix.classList.add("expanded");
      });
    }
    else {
      const constrainerStyle = window.getComputedStyle(affixConstrainer);
      const paddingLeft = parseInt(constrainerStyle.paddingLeft!, 10);
      $affix.animate({
        left: constrainerRect.left + paddingLeft,
        width: $(affixConstrainer).innerWidth()! - paddingLeft,
      }, 1000, () => {
        affix.style.left = "";
        affix.style.top = "";
        affix.classList.remove("expanded");
      });
    }
    ev.stopPropagation();
  };
}

function makeResizeHandler(affix: HTMLElement,
                           affixConstrainer: HTMLElement,
                           affixOverflow: HTMLElement,
                           expandableToggle: Element,
                           container: Element,
                           frame: Element,
                           expandHandler: (ev: JQueryEventObject) => void):
() => void {
  const $affix = $(affix);
  const $expandableToggle = $(expandableToggle);

  return () => {
    $expandableToggle.off("click");
    $affix.off("click");
    const containerRect = container.getBoundingClientRect();
    const constrainerRect = affixConstrainer.getBoundingClientRect();
    if (constrainerRect.width < containerRect.width / 4) {
      $expandableToggle.on("click", expandHandler);
      $affix.on("click", "a", expandHandler);
      affix.classList.add("expandable");
    }
    else {
      affix.classList.remove("expanded");
      affix.classList.remove("expanding");
      affix.classList.remove("expandable");
      affix.style.left = "";
    }

    const style = window.getComputedStyle(affix);
    const constrainerStyle = window.getComputedStyle(affixConstrainer);
    if (affix.classList.contains("expanded")) {
      const frameRect = frame.getBoundingClientRect();
      affix.style.width = `${frameRect.width}px`;
      affix.style.left = `${frameRect.left}px`;
    }
    else {
      // This prevents the affix from popping wider when we scroll the
      // window. Because a "detached" affix has "position: fixed", it is taken
      // out of the flow and thus its "width" is no longer constrained by its
      // parent.

      affix.style.width = `${$(affixConstrainer).innerWidth()! -
parseInt(constrainerStyle.paddingLeft!, 10)}px`;
    }
    const rect = affixOverflow.getBoundingClientRect();
    affixOverflow.style.height = `${window.innerHeight - rect.top -
parseInt(style.marginBottom!, 10) - 5}px`;
  };
}

/**
 * @param {Element} root The element of ``wed-document`` class that is meant
 * to hold the viewed document.
 *
 * @param {string} editUrl The url through which the document may be edited.
 *
 * @param {string} fetchUrl The url through which the document may be fetched
 * for displaying. If set, it is a URL from which to get the
 *
 *
 * @param {string} semanticFieldFetchUrl The url through which semantic field
 * information is to be fetched.
 *
 *
 * @param {string} data The document, as XML.
 *
 * @param {string} biblData The bibliographical data. This is a mapping of
 * targets (i.e. the targets given to the ``ref`` tags that point to
 * bibliographical items) to dictionaries that contain the same values those
 * returned as when asking the server to resolve these targets
 * individually. This mapping must be complete. Otherwise, it is an internal
 * error.
 *
 * @param {string} languagePrefix The language prefix currently used in
 * URLs. Django will prefix URLs with something like "/en-us" when the user is
 * using the American English setup. It could be inferable from the URLs
 * passed in other parameter or from the URL of the currrent page but it is
 * preferable to get an actual value than try to guess it.
 */
export class Viewer extends DispatchMixin {
  private readonly doc: Document;
  private readonly win: Window;
  protected readonly metadata: Metadata;
  protected readonly refmans: WholeDocumentManager;
  private readonly loadTimeout: number = 30000;
  private readonly resolver: DefaultNameResolver = new DefaultNameResolver();
  protected readonly sfFetcher: SFFetcher;
  protected readonly editor: DispatchEditor;
  protected readonly mode: DispatchMode;
  protected readonly mapped: MappedUtil;
  protected readonly guiUpdater: TreeUpdater;
  private dataDoc!: Document;
  protected readonly headingDecorator: HeadingDecorator;
  private doneResolve!: (value: Viewer) => void;
  // tslint:disable-next-line:no-any
  private doneReject!: (err: any) => void;

  protected readonly senseSubsenseIdManager: IDManager = new IDManager("S.");
  protected readonly exampleIdManager: IDManager = new IDManager("E.");
  protected readonly senseTooltipSelector: string =
    "btw:english-term-list>btw:english-term";

  private biblData!: Record<string, BibliographicalItem>;

  readonly done: Promise<Viewer>;

  constructor(private readonly root: Element,
              editUrl: string,
              fetchUrl: string,
              private readonly semanticFieldFetchUrl: string,
              data: string, biblData: Record<string, BibliographicalItem>,
              private readonly languagePrefix: string) {
    super();
    this.init();
    this.metadata =
      new MetadataMultiversionReader().read(JSON.parse(metadataJSON));
    this.mapped = new MappedUtil(this.metadata.getNamespaceMappings());
    this.refmans = new WholeDocumentManager(this.mapped);

    const doc = this.doc = root.ownerDocument!;
    this.win = doc.defaultView!;

    const mappings = this.metadata.getNamespaceMappings();
    for (const key of Object.keys(mappings)) {
      this.resolver.definePrefix(key, mappings[key]);
    }

    this.sfFetcher = new SFFetcher(this.semanticFieldFetchUrl,
                                    this.win.location.href,
                                    ["changerecords"]);

    //
    // We provide minimal objects that are used by some of the logic which is
    // shared with btw_decorator.
    //
    this.editor = FAKE_EDITOR;
    this.mode = FAKE_MODE;

    const { heading, group, content } = makeCollapsible(doc, "default",
                                                        "toolbar-heading",
                                                        "toolbar-collapse", {
                                                          group: "horizontal",
                                                        });
    const frame = doc.getElementsByClassName("wed-frame")[0];
    // tslint:disable-next-line:no-inner-html
    heading.innerHTML =
      "<span class='fa fa-bars' style='width: 0.4em; overflow: hidden'></span>";

    let buttons = "<span>";
    if (editUrl != null && editUrl !== "") {
      buttons += _.template(
        "<a class='btw-edit-btn btn btn-outline-dark' title='Edit'\
      href='<%= editUrl %>'><i class='fa fa-fw fa-pencil-square-o'></i>\
  </a>")({ editUrl });
    }
    buttons += "\
<a class='btw-expand-all-btn btn btn-outline-dark' title='Expand All' href='#'>\
 <i class='fa fa-fw fa-caret-down'></i></a>\
<a class='btw-collapse-all-btn btn btn-outline-dark' title='Collapse All' \
 href='#'><i class='fa fa-fw fa-caret-right'></i></a></span>";

    // tslint:disable-next-line:no-inner-html
    content.innerHTML = buttons;

    // Make it so that it floats above everything else.
    group.style.position = "fixed";
    group.style.zIndex = "10";

    // This is necessary so that it collapses horizontally.
    (content.parentNode as Element).classList.add("width");

    frame.insertBefore(group, frame.firstChild);

    const expandAll = content.getElementsByClassName("btw-expand-all-btn")[0];
    $(expandAll).on("click", ev => {
      $(doc.querySelectorAll(".wed-document .collapse:not(.show)"))
        .collapse("show");
      $(content.parentNode!).collapse("hide");
      ev.preventDefault();
    });

    const collapseAll =
      content.getElementsByClassName("btw-collapse-all-btn")[0];
    $(collapseAll).on("click", ev => {
      $(doc.querySelectorAll(".wed-document .collapse.show")).collapse("hide");
      $(content.parentNode!).collapse("hide");
      ev.preventDefault();
    });

    // tslint:disable-next-line:promise-must-complete
    this.done = new Promise((resolve, reject) => {
      this.doneResolve = resolve;
      this.doneReject = reject;
    });

    // tslint:disable-next-line:no-unused-expression
    new DLocRoot(root);
    this.guiUpdater = new TreeUpdater(root);

    // Override the head specs with those required for viewing.
    this.headingDecorator = this.makeHeadingDecorator();

    // If we are passed a fetchUrl, then we have to fetch the data from the
    // site.
    if (fetchUrl != null && fetchUrl !== "") {
      this.fetchAndProcessData(fetchUrl);
    }
    else {
      this.processData(data, biblData);
    }
  }

  private fetchAndProcessData(fetchUrl: string): void {
    // Show the loading alert.
    const loading =
      document.querySelector(".wed-document>.loading") as HTMLElement;
    loading.style.display = "";
    const start = Date.now();
    const fetch = async () => {
      try {
        try {
          const ajaxData = await ajax({
            url: fetchUrl,
            headers: {
              Accept: "application/json",
            },
          });

          this.processData(ajaxData.xml, ajaxData.bibl_data);
        }
        catch (err) {
          if (!(err instanceof bluejax.HttpError)) {
            throw err;
          }

          const jqXHR = err.jqXHR;
          if (jqXHR.status !== 404) {
            throw err;
          }

          if (Date.now() - start > this.loadTimeout) {
            this.failedLoading(loading,
                               "The server has not sent the required " +
                               "data within a reasonable time frame.");
          }
          else {
            window.setTimeout(fetch, 200);
          }
        }
      }
      catch (err) {
        this.doneReject(err);
        throw err;
      }
    };

    fetch();
  }

  private failedLoading(loading: Element, msg: string): void {
    loading.classList.remove("alert-info");
    loading.classList.add("alert-danger");
    loading.textContent = msg;
    this.doneReject(new Error("failed loading"));
  }

  // tslint:disable-next-line:max-func-body-length
  private makeHeadingDecorator(): HeadingDecorator {
    const headingMap = {
      "btw:overview": "• OVERVIEW",
      "btw:sense-discrimination": "• SENSE DISCRIMINATION",
      "btw:historico-semantical-data": "• HISTORICO-SEMANTICAL DATA",
      "btw:credits": "• CREDITS",
    };

    const ret = new HeadingDecorator(this.refmans, this.guiUpdater,
                                     this.mapped, headingMap,
                                     false /* impliedBrackets */);

    ret.addSpec({ selector: "btw:definition", heading: null });
    ret.addSpec({ selector: "btw:english-rendition", heading: null });
    ret.addSpec({ selector: "btw:english-renditions", heading: null });
    ret.addSpec({ selector: "btw:semantic-fields", heading: null });
    ret.addSpec({
      selector: "btw:sense",
      heading: "",
      labelF: this.refmans.getSenseLabelForHead.bind(this.refmans),
      suffix: ".",
    });
    ret.addSpec({ selector: "btw:sense>btw:explanation", heading: null });
    ret.addSpec({ selector: "btw:subsense>btw:explanation", heading: null });
    ret.addSpec({
      selector: "btw:english-renditions>btw:semantic-fields-collection",
      heading: "semantic fields",
      collapse: {
        kind: "default",
        additionalClasses: "sf-collapse",
      },
    });
    ret.addSpec({
      selector: "btw:contrastive-section",
      heading: "contrastive section",
      collapse: "default",
    });
    ret.addSpec({
      selector: "btw:antonyms",
      heading: "antonyms",
      collapse: "default",
    });
    ret.addSpec({
      selector: "btw:cognates",
      heading: "cognates",
      collapse: "default",
    });
    ret.addSpec({
      selector: "btw:conceptual-proximates",
      heading: "conceptual proximates",
      collapse: "default",
    });
    ret.addSpec({
      selector: "btw:cognate-term-list>btw:semantic-fields-collection",
      heading: "semantic fields",
      collapse: {
        kind: "default",
        additionalClasses: "sf-collapse",
      },
    });
    ret.addSpec(
      { selector: "btw:semantic-fields-collection>btw:semantic-fields",
        heading: null });
    ret.addSpec({
      selector: "btw:sense>btw:semantic-fields",
      heading: "all semantic fields in the citations of this sense",
      collapse: {
        kind: "default",
        additionalClasses: "sf-collapse",
      },
    });
    ret.addSpec({
      selector: "btw:overview>btw:semantic-fields",
      heading: "all semantic fields",
      collapse: {
        kind: "default",
        additionalClasses: "sf-collapse",
      },
    });
    ret.addSpec({
      selector: "btw:semantic-fields",
      heading: "semantic fields",
      collapse: {
        kind: "default",
        additionalClasses: "sf-collapse",
      },
    });
    ret.addSpec({ selector: "btw:subsense>btw:citations", heading: null });
    ret.addSpec({ selector: "btw:sense>btw:citations", heading: null });
    ret.addSpec({ selector: "btw:antonym>btw:citations", heading: null });
    ret.addSpec({ selector: "btw:cognate>btw:citations", heading: null });
    ret.addSpec({ selector: "btw:conceptual-proximate>btw:citations",
                  heading: null });
    ret.addSpec({ selector: "btw:citations-collection>btw:citations",
                  heading: null });
    ret.addSpec({
      selector: "btw:sense>btw:other-citations",
      heading: "more citations",
      collapse: "default",
    });
    ret.addSpec({
      selector: "btw:other-citations",
      heading: "more citations",
      collapse: "default",
    });
    return ret;
  }

  // tslint:disable-next-line:max-func-body-length
  private processData(data: string,
                      biblData: Record<string, BibliographicalItem>): void {
    const { doc, win, root } = this;
    this.biblData = biblData;

    // Clear the root.
    // tslint:disable-next-line:no-inner-html
    root.innerHTML = "";

    // tslint:disable-next-line:no-any
    const parser = new (doc.defaultView as any).DOMParser() as DOMParser;
    const dataDoc = this.dataDoc = parser.parseFromString(data, "text/xml");

    //
    // We also need to perform the changes that are purely due to the fact that
    // the editing structure is different from the viewing structure.
    //
    this.transformEnglishRenditions();

    //
    // Transform contrastive items to the proper viewing format.
    //
    this.transformContrastiveItems("antonym");
    this.transformContrastiveItems("cognate");
    this.transformContrastiveItems("conceptual-proximate");

    root.appendChild(convert.toHTMLTree(doc, dataDoc.firstChild!));
    domutil.linkTrees(root, this.dataDoc);

    this.seeIds();

    //
    // Some processing needs to be done before _process is called. In btw_mode,
    // these would be handled by triggers.
    //
    for (const sense of Array.from(root.getElementsByClassName("btw:sense"))) {
      this.idDecorator(root, sense);
      this.headingDecorator.sectionHeadingDecorator(sense);
    }

    for (const sfs of Array.from(
      root.getElementsByClassName("btw:semantic-fields-collection"))) {
      this.headingDecorator.sectionHeadingDecorator(sfs);
    }

    // tslint:disable-next-line:prefer-for-of
    for (const subsense of
         Array.from(root.getElementsByClassName("btw:subsense"))) {
      this.idDecorator(root, subsense);
      const explanation = domutil.childByClass(subsense, "btw:explanantion");
      if (explanation !== null) {
        this.explanationDecorator(root, explanation);
      }
    }

    // In btw_decorator, there are triggers that refresh hyperlinks as elements
    // are added or processed. Such triggers do not exist here so id decorations
    // need to be performed before anything else is done so that when hyperlinks
    // are decorated, everthing is available for them to be decorated.
    for (const withId of Array.from(
      root.querySelectorAll(`[${convert.encodeAttrName("xml:id")}]`))) {
      this.idDecorator(root, withId);
    }

    // We unwrap the contents of all "resp" elements.
    const resps = root.getElementsByClassName("resp");
    // As we process each element, it is removed from the live list returned by
    // getElementsByClassName.
    while (resps.length !== 0) {
      const resp = resps[0];
      resp.replaceWith(...Array.from(resp.childNodes));
    }

    // We want to process all ref elements earlier so that hyperlinks to
    // examples are created properly.
    for (const ref of Array.from(root.getElementsByClassName("ref"))) {
      this.process(root, ref);
    }

    this.process(root, root.firstElementChild!);

    // Work around a bug in Bootstrap. Bootstrap's scrollspy (at least up to
    // 4.4.1) can't handle a period in a URL's hash. It passes the hash to
    // jQuery as a CSS selector and jQuery silently fails to find the object.
    for (const target of Array.from(root.querySelectorAll("[id]"))) {
      target.id = target.id.replace(/\./g, "_");
    }

    for (const link of Array.from(root.getElementsByTagName("a"))) {
      const href = link.getAttribute("href");
      if (href !== null && href.startsWith("#")) {
        link.setAttribute("href", href.replace(/\./g, "_"));
      }
    }

    this.createAffix();
    $(doc.body).on("click", ev => {
      // We are not using $.Event because setting bubbles to `false` does not
      // seem possible with `$.Event`.
      const $for = $(ev.target).closest("[data-toggle='popover']");
      $("[aria-describedby][data-toggle='popover']").not($for).each(
        function destroy(this: Element): void {
          // We have to work around an issue in Bootstrap 3.3.7. If destroy is
          // called more than once on a popover or tooltip, it may cause an
          // error. We work around the issue by making sure we call it only if
          // the tip is .show.
          const popover = $.data(this, "bs.popover");
          if (popover) {
            const tip = popover.getTipElement();
            if (tip && tip.classList.contains("show")) {
              popover.dispose();
            }
          }
        });
    });

    const bound = this._showTarget.bind(this);
    win.addEventListener("popstate", bound);
    // This also catches hitting the Enter key on a link.
    $(root).on("click", "a[href]:not([data-toggle], [href='#'])", () => {
      setTimeout(bound, 0);
    });
    this._showTarget();

    this.doneResolve(this);
  }

  private seeIds(): void {
    const root = this.root;
    const sensesSubsenses = root.querySelectorAll(this.mapped.toGUISelector(
      "btw:sense, btw:subsense"));
    // tslint:disable-next-line:one-variable-per-declaration
    for (let i = 0, limit = sensesSubsenses.length; i < limit; ++i) {
      const s = sensesSubsenses[i];
      const id = s.getAttribute(convert.encodeAttrName("xml:id"));
      if (id !== null) {
        this.senseSubsenseIdManager.seen(id, true);
      }
    }

    const examples = root.querySelectorAll(this.mapped.toGUISelector(
      "btw:example, btw:example-explained"));
    // tslint:disable-next-line:one-variable-per-declaration
    for (let i = 0, limit = examples.length; i < limit; ++i) {
      const ex = examples[i];
      const id = ex.getAttribute(convert.encodeAttrName("xml:id"));
      if (id !== null) {
        this.exampleIdManager.seen(id, true);
      }
    }
  }

  private createAffix(): void {
    // Create the affix
    const { doc, win } = this;

    const affix = doc.getElementById("btw-article-affix")!;
    this.populateAffix(affix);
    // $(affix).affix({
    //   offset: {
    //     top: 1,
    //     bottom: 1,
    //   },
    // });

    $(doc.body).scrollspy({ target: "#btw-article-affix" });

    const expandableToggle = affix.querySelector(".expandable-heading .btn")!;
    const affixConstrainer = domutil.closest(affix, "div") as HTMLElement;
    const affixOverflow =
      affix.getElementsByClassName("overflow")[0] as HTMLElement;

    const frame = doc.getElementsByClassName("wed-frame")[0];
    const expandHandler = makeExpandHandler(affix, affixConstrainer, frame);
    const container = doc.getElementsByClassName("container")[0];
    const resizeHandler =  makeResizeHandler(affix, affixConstrainer,
                                             affixOverflow,
                                             expandableToggle,
                                             container,
                                             frame,
                                             expandHandler);
    win.addEventListener("resize", resizeHandler);
    win.addEventListener("scroll", resizeHandler);
    resizeHandler();

    $(doc.body).on("activate.bs.scrollspy", () => {
      // Scroll the affix if needed.
      const affixRect = affixOverflow.getBoundingClientRect();
      for (const active of Array.from(affix.querySelectorAll(".active>a"))) {
        if (active.getElementsByClassName("active").length !== 0) {
          continue;
        }
        const activeRect = active.getBoundingClientRect();
        affixOverflow.scrollTop = Math.floor(activeRect.top - affixRect.top);
      }
    });
  }

  private populateAffix(affix: Element): void {
    const { doc, root } = this;

    const topUl = affix.getElementsByTagName("ul")[0];
    let ulStack: Element[] = [topUl];
    const containerStack: Element[] = [];
    let prevContainer: Element | null = null;
    // tslint:disable-next-line:prefer-for-of
    for (const anchor of
         Array.from(root.querySelectorAll(
           this.mapped.toGUISelector("btw:subsense, .head")))) {
      if (prevContainer !== null && prevContainer.contains(anchor)) {
        containerStack.unshift(prevContainer);
        const ul = doc.createElement("ul");
        ul.className = "nav";
        ulStack[0].lastElementChild!.append(ul);
        ulStack.unshift(ul);
      }
      else {
        while (containerStack[0] !== undefined &&
               !containerStack[0].contains(anchor)) {
          containerStack.shift();
          ulStack.shift();
        }
        if (ulStack.length === 0) {
          ulStack = [topUl];
        }
      }

      let heading: string | undefined;
      if (anchor.classList.contains("head")) {
        // We're processing a head that was created for the GUI tree.
        const prefix = anchor.textContent!.replace("•", "").trim();
        // Special cases
        const parent = anchor.parentNode as Element;
        switch (getOriginalNameIfPossible(parent)) {
        case "btw:sense":
          const terms = parent.querySelector(
            this.mapped.toGUISelector("btw:english-term-list"));
          heading = `${prefix} ${(terms !== null ? terms.textContent : "")}`;
          break;
        case "btw:antonym-term-list":
        case "btw:cognate-term-list":
        case "btw:conceptual-proximate-term-list":
          break;
        default:
          heading = prefix;
        }
        prevContainer = parent;
      }
      else {
        // We're processing a btw:subsense element.
        heading = anchor.getElementsByClassName("btw:explanation")[0]
          .textContent!;
        prevContainer = anchor;
      }

      if (heading !== undefined && heading !== "") {
        ulStack[0].append(domutil.htmlToElements(
          _.template("<li><a href='#<%= target %>'><%= heading %></a></li>")(
            { target: anchor.id, heading }), doc)[0]);
      }
    }
  }

  _showTarget(): void {
    const hash = this.win.location.hash;
    // tslint:disable-next-line:possible-timing-attack
    if (hash === "") {
      return;
    }

    const target = this.doc.getElementById(hash.slice(1));
    if (target === null) {
      return;
    }

    const parents: Element[] = [];
    let parent = closest(target, ".collapse:not(.show)");
    while (parent !== null) {
      parents.unshift(parent);
      parent = parent.parentNode as Element;
      parent = parent !== null ? closest(parent, ".collapse:not(.show)") : null;
    }

    function next(level: Element): void {
      const $level = $(level);
      $level.one("shown.bs.collapse", () => {
        if (parents.length !== 0) {
          next(parents.shift()!);
          return;
        }
        // We get here only once all sections have been expanded.
        target!.scrollIntoView(true);
      });
      $level.collapse("show");
    }

    if (parents.length !== 0) {
      next(parents.shift()!);
    }
    else {
      target.scrollIntoView(true);
    }
  }

  process(root: Element, el: Element): void {
    this.dispatch(root, el);
    el.classList.remove("_phantom");

    // Process the children...
    const children = el.children;
    // tslint:disable-next-line:one-variable-per-declaration
    for (let i = 0, limit = children.length; i < limit; ++i) {
      this.process(root, children[i]);
    }
  }

  listDecorator(el: Element, sep: string | Node): void {
    // If sep is a string, create an appropriate div.
    const sepNode = (typeof sep === "string") ?
      el.ownerDocument!.createTextNode(sep) :
      sep;

    let first = true;
    let child = el.firstElementChild;
    while (child !== null) {
      if (child.classList.contains("_real")) {
        if (!first) {
          this.guiUpdater.insertBefore(
            el, sepNode.cloneNode(true) as (Element | Text), child);
        }
        else {
          first = false;
        }
      }
      child = child.nextElementSibling;
    }
  }

  // tslint:disable-next-line:no-empty
  languageDecorator(): void {}

  // tslint:disable-next-line:no-empty
  noneDecorator(): void {}

  elementDecorator(root: Element, el: Element): void {
    switch (getOriginalNameIfPossible(el)) {
      case "persName":
        this.persNameDecorator(root, el);
        break;
      case "editor":
        this.editorDecorator(root, el);
        break;
      case "btw:sf":
        this.sfDecorator(root, el);
        break;
        // The following listed elements are only existing in article viewing
        // mode. They do not exist in editing mode.
      case "btw:antonym-term-list":
      case "btw:cognate-term-list":
      case "btw:conceptual-proximate-term-list":
        this.termListDecorator(root, el);
        break;
      default:
    }
  }

  termListDecorator(_root: Element, el: Element): void {
    const head = el.ownerDocument!.createElement("div");
    head.className = "head _phantom";
    head.textContent = "Terms in this section:";
    el.prepend(head);
  }

  editorDecorator(_root: Element, el: Element): void {
    const class_ = "_editor_label";
    let label = domutil.childByClass(el, class_);
    if (label === null) {
      label = el.ownerDocument!.createElement("div");
      label.className = `_text _phantom ${class_}`;
      label.textContent = "Editor: ";
      this.guiUpdater.insertBefore(el, label, el.firstChild);
    }
  }

  persNameDecorator(_root: Element, el: Element): void {
    el.classList.add("_inline");

    const handleSeparator = (class_: string, where: string, text: string) => {
      const separatorClass = `_${class_}_separator`;
      const child = domutil.childByClass(el, class_);
      const exists = child !== null ? (child.childNodes.length !== 0) : false;
      const oldSeparator = domutil.childByClass(el, separatorClass);

      if (exists) {
        if (oldSeparator === null) {
          const separator = el.ownerDocument!.createElement("div");
          separator.className = `_text _phantom ${separatorClass}`;
          separator.textContent = text;
          let before: Node | null;
          switch (where) {
          case "after":
            before = child!.nextSibling;
            break;
          case "before":
            before = child;
            break;
          default:
            throw new Error(`unknown value for where: ${where}`);
          }
          this.guiUpdater.insertBefore(el, separator, before);
        }
      }
      else if (oldSeparator !== null) {
        this.guiUpdater.removeNode(oldSeparator);
      }
    };

    handleSeparator("forename", "after", " ");
    handleSeparator("genName", "before", ", ");

    const nameSeparatorClass = "_persNamename_separator";
    const oldNameSeparator = domutil.childByClass(el, nameSeparatorClass);

    if (oldNameSeparator === null) {
      const separator = el.ownerDocument!.createElement("div");
      separator.className = `_text _phantom ${nameSeparatorClass}`;
      separator.textContent = " ";
      this.guiUpdater.insertBefore(el, separator, el.firstChild);
    }
  }

  private transformEnglishRenditions(): void {
    const { dataDoc } = this;

    // Transform English renditions to the viewing format.
    for (const englishRenditionsEl of
         Array.from(dataDoc.getElementsByTagNameNS(BTW_NS,
                                                   "english-renditions"))) {
      const renditions =
        Array.from(
          englishRenditionsEl.getElementsByTagNameNS(BTW_NS,
                                                     "english-rendition"));
      //
      // Make a list of btw:english-terms that will appear at the start of the
      // btw:english-renditions.
      //
      const terms = Array.from(
        englishRenditionsEl.getElementsByTagNameNS(BTW_NS, "english-term"));
      const lastTerm = terms[terms.length - 1];
      const div = dataDoc.createElementNS(BTW_NS, "btw:english-term-list");
      for (const term of terms) {
        div.appendChild(term.cloneNode(true));
        if (term !== lastTerm) {
          div.appendChild(dataDoc.createTextNode(", "));
        }
      }
      englishRenditionsEl.insertBefore(div, renditions[0]);

      //
      // Combine the contents of all btw:english-rendition into one
      // btw:semantic-fields-collection element.
      //
      const sfs = dataDoc.createElementNS(BTW_NS,
                                          "btw:semantic-fields-collection");
      for (const er of renditions) {
        sfs.append(...Array.from(er.childNodes));
        er.remove();
      }
      englishRenditionsEl.appendChild(sfs);
    }
  }

  private transformContrastiveItems(name: string): void {
    const { dataDoc } = this;
    // A "group" here is an element that combines a bunch of elements of the
    // same kind: btw:antonyms is a group of btw:antonym, btw:cognates is a
    // group of btw:cognates, etc. The elements of the same kind are called
    // "items" later in this code.

    // groups are those elements that act as containers (btw:cognates,
    // btw:antonyms, etc.)
    for (const group of
         Array.from(dataDoc.getElementsByTagNameNS(BTW_NS, `${name}s`))) {
      if (group.getElementsByTagNameNS(BTW_NS, "none").length !== 0) {
        // The group is empty. Remove the group and move on.
        group.remove();
        continue;
      }

      // This div will contain the list of all terms in the group.
      const div = dataDoc.createElementNS(BTW_NS, `btw:${name}-term-list`);

      // A wrapper is the element that wraps around the term. This loop: 1) adds
      // each wrapper to the .btw:...-term-list. and b) replaces each term with
      // a clone of the wrapper.
      const wrappers: Element[] = [];
      let num = 1;
      for (const term of
           Array.from(group.getElementsByTagNameNS(BTW_NS, "term"))) {
        const termWrapper = dataDoc.createElementNS(BTW_NS,
                                                    `btw:${name}-term-item`);
        termWrapper.append(`${name.replace("-", " ")} ${num++}: `,
                           term.cloneNode(true));
        div.append(termWrapper);

        // This replaces the term element in btw:antonym, btw:cognate, etc. with
        // an element that contains the "name i: " prefix.
        term.replaceWith(termWrapper.cloneNode(true));
        wrappers.push(termWrapper);
      }

      const items = Array.from(group.children);

      //
      // Combine the contents of all of the items into one collection.
      //
      const coll = dataDoc.createElementNS(BTW_NS, "btw:citations-collection");
      // What we are doing here is pushing on the btw:antonym, btw:cognate,
      // etc. element. At this point, that's only btw:citations elements plus
      // btw:...-term-item elements.
      coll.append(...items);
      group.append(div, coll);

      //
      // If there are btw:sematic-fields elements, move them to the list of
      // terms.
      //
      if (name === "cognate") {
        for (let ix = 0; ix < items.length; ++ix) {
          wrappers[ix].after(
            // We get only the first one, which is the one that contains the
            // combined semantic fields for the whole cognate.
            items[ix].getElementsByTagNameNS(BTW_NS, "semantic-fields")[0]);
        }
      }
    }
  }

  async fetchAndFillBiblData(targetId: string, el: Element,
                             abbr: Element): Promise<void> {
    const data = this.biblData[targetId];
    if (data === undefined) {
      throw new Error("missing bibliographical data");
    }
    this.fillBiblData(el, abbr, data);
  }

  refDecorator(root: Element, el: Element): void {
    let origTarget = el.getAttribute(convert.encodeAttrName("target"));
    if (origTarget === null) {
      origTarget = "";
    }

    origTarget = origTarget.trim();

    const biblPrefix = "/bibliography/";
    const entryPrefix = `${this.languagePrefix}/lexicography/entry/`;
    if (origTarget.lastIndexOf(biblPrefix, 0) === 0) {
      // We want to remove any possible a element before we give control to the
      // overriden function.
      let a = domutil.childByClass(el, "a") as HTMLAnchorElement;
      if (a !== null) {
        let aChild = a.firstChild;
        while (aChild !== null) {
          el.insertBefore(aChild, a);
          aChild = a.firstChild;
        }
        el.removeChild(a);
      }

      DispatchMixin.prototype.refDecorator.call(this, root, el);

      // Bibliographical reference...
      const targetId = origTarget;

      const data = this.biblData[targetId];
      if (data === undefined) {
        throw new Error("missing bibliographical data");
      }

      // We also want a hyperlink into the Zotero library.
      a = el.ownerDocument!.createElement("a");
      a.className = "a _phantom_wrap";
      // When the item is a secondary source, ``zotero_url`` is at the top
      // level. If it is a secondary source, ``zotero_url`` is inside the
      // ``item`` field.
      a.href = !isPrimarySource(data) ? data.zotero_url : data.item.zotero_url;
      a.setAttribute("target", "_blank");

      let child = el.firstChild;
      el.appendChild(a);
      while (child !== null && child !== a) {
        a.appendChild(child);
        child = el.firstChild;
      }
    }
    else if (origTarget.lastIndexOf(entryPrefix, 0) === 0) {
      let a = domutil.childByClass(el, "a") as HTMLAnchorElement;
      if (a !== null) {
        let aChild = a.firstChild;
        while (aChild !== null) {
          el.insertBefore(aChild, a);
          aChild = a.firstChild;
        }
        el.removeChild(a);
      }

      a = el.ownerDocument!.createElement("a");
      a.className = "a _phantom_wrap";
      a.href = origTarget;
      a.setAttribute("target", "_blank");

      let child = el.firstChild;
      el.appendChild(a);
      while (child !== null && child !== a) {
        a.appendChild(child);
        child = el.firstChild;
      }
    }
    else {
      DispatchMixin.prototype.refDecorator.call(this, root, el);
    }
  }

  makeElement(name: string, attrs?: Record<string, string>): Element {
    const ename = this.resolver.resolveName(name)!;
    const e = transformation.makeElement(this.dataDoc, ename.ns, name, attrs);
    return convert.toHTMLTree(this.doc, e) as Element;
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

    return (this.metadata.isInline(dataNode) ||
            dataNode.tagName === "btw:english-term") ?
      "_inline" : "";
  }
}

//
// This is useful to track down bugs due to nodes lacking a mirror.
//
// function reportMissing(tree: string, node: Node, data: boolean): void {
//   const mirror = domutil.getMirror(node);
//   if (mirror === undefined) {
//     console.log("in", tree,
//                 data ? (node as any).tagName : (node as any).className);
//   }
//   for (let i = 0; i < node.childNodes.length; ++i) {
//     reportMissing(tree, node.childNodes[i], data);
//   }
// }
