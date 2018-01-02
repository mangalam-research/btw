/**
 * Code for viewing documents edited by btw-mode.
 * @author Louis-Dominique Dubeau
 */
import * as bluejax from "bluejax";
import "bootstrap";
import * as $ from "jquery";
import * as _ from "lodash";
import { NameResolver } from "salve";

import { convert, DLocRoot, domtypeguards, domutil, transformation,
         treeUpdater, util } from "wed";
import isElement = domtypeguards.isElement;
import InsertNodeAtEvent = treeUpdater.InsertNodeAtEvent;
import TreeUpdater = treeUpdater.TreeUpdater;

import { Metadata } from "wed/modes/generic/metadata";
import { MetadataMultiversionReader,
       } from "wed/modes/generic/metadata-multiversion-reader";

import { ajax } from "../ajax";
import { BibliographicalItem, isPrimarySource } from "./bibliography";
import { DispatchMixin } from "./btw-dispatch";
import { HeadingDecorator } from "./btw-heading-decorator";
import { WholeDocumentManager } from "./btw-refmans";
import * as metadataJSON from "./btw-storage-metadata.json";
import * as btwUtil from "./btw-util";
import { IDManager } from "./id-manager";
import { MappedUtil } from "./mapped-util";
import { SFFetcher } from "./semantic-field-fetcher";

const _slice = Array.prototype.slice;
const closest = domutil.closest;

// TEMPORARY TYPE DEFINITIONS
// tslint:disable-next-line: no-any
declare var require: any;
// END TEMPORARY TYPE DEFINITIONS

interface FakeEditor {
  toDataNode(node: Node): Node;
}

interface FakeMode {
  nodesAroundEditableContents(): [null, null];
}

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
export class Viewer {
  private readonly doc: Document;
  private readonly win: Window;
  private readonly metadata: Metadata;
  private readonly refmans: WholeDocumentManager;
  private readonly loadTimeout: number = 30000;
  private readonly resolver: NameResolver = new NameResolver();
  private readonly sfFetcher: SFFetcher;
  private readonly editor: FakeEditor;
  private readonly mode: FakeMode;
  private readonly mapped: MappedUtil;
  private guiUpdater: TreeUpdater;
  private dataDoc: Document;
  private headingDecorator: HeadingDecorator;
  private doneResolve: (value: Viewer) => void;
  // tslint:disable-next-line:no-any
  private doneReject: (err: any) => void;

  private readonly senseSubsenseIdManager: IDManager = new IDManager("S.");
  private readonly exampleIdManager: IDManager = new IDManager("E.");
  private readonly senseTooltipSelector: string =
    "btw:english-term-list>btw:english-term";

  private biblData: Record<string, BibliographicalItem>;

  readonly done: Promise<Viewer>;

  // From DispatchMixin
  dispatch: (root: Element, el: Element) => void;
  idDecorator: (root: Element, el: Element) => void;
  explanationDecorator: (root: Element, el: Element) => void;
  sfDecorator: (root: Element, el: Element) => void;
  fillBiblData: (el: Element, abbr: Element, data: BibliographicalItem) => void;

  constructor(private readonly root: Element,
              editUrl: string,
              fetchUrl: string,
              private readonly semanticFieldFetchUrl: string,
              data: string, biblData: Record<string, BibliographicalItem>,
              private readonly languagePrefix: string) {
    this.metadata =
      new MetadataMultiversionReader().read(JSON.parse(metadataJSON));
    this.mapped = new MappedUtil(this.metadata.getNamespaceMappings());
    this.refmans = new WholeDocumentManager(this.mapped);

    DispatchMixin.call(this);
    const doc = this.doc = root.ownerDocument;
    const win = this.win = doc.defaultView;

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
    this.editor = {
      toDataNode(node: Node): Node {
        return node;
      },
    };

    this.mode = {
      nodesAroundEditableContents(): [null, null] {
        return [null, null];
      },
    };

    const { heading, group, content } =
      btwUtil.makeCollapsible(doc, "default", "toolbar-heading",
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
        "<a class='btw-edit-btn btn btn-default' title='Edit'\
      href='<%= editUrl %>'><i class='fa fa-fw fa-pencil-square-o'></i>\
  </a>")({ editUrl });
    }
    buttons += "\
<a class='btw-expand-all-btn btn btn-default' title='Expand All' href='#'>\
 <i class='fa fa-fw fa-caret-down'></i></a>\
<a class='btw-collapse-all-btn btn btn-default' title='Collapse All' \
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
    $(expandAll).on("click", (ev) => {
      $(doc.querySelectorAll(".wed-document .collapse:not(.in)"))
        .collapse("show");
      $(content.parentNode!).collapse("hide");
      ev.preventDefault();
    });

    const collapseAll =
      content.getElementsByClassName("btw-collapse-all-btn")[0];
    $(collapseAll).on("click", (ev) => {
      $(doc.querySelectorAll(".wed-document .collapse.in")).collapse("hide");
      $(content.parentNode!).collapse("hide");
      ev.preventDefault();
    });

    // tslint:disable-next-line:promise-must-complete
    this.done = new Promise((resolve, reject) => {
      this.doneResolve = resolve;
      this.doneReject = reject;
    });

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
    const fetch = () => {
      ajax({
        url: fetchUrl,
        headers: {
          Accept: "application/json",
        },
      })
        .then((ajaxData) => {
          this.processData(ajaxData.xml, ajaxData.bibl_data);
        })
        .catch(bluejax.HttpError, (err) => {
          const jqXHR = err.jqXHR;
          if (jqXHR.status === 404) {
            if (Date.now() - start > this.loadTimeout) {
              this.failedLoading(loading,
                                 "The server has not sent the required " +
                                 "data within a reasonable time frame.");
            }
            else {
              window.setTimeout(fetch, 200);
            }
          }
          else {
            throw err;
          }
        })
          .catch((err) => {
            this.doneReject(err);
            throw err;
          });
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

    root.appendChild(convert.toHTMLTree(doc, dataDoc.firstChild!));

    // tslint:disable-next-line:no-unused-expression
    new DLocRoot(root);
    const guiUpdater = this.guiUpdater = new TreeUpdater(root);

    // Override the head specs with those required for viewing.
    this.headingDecorator = this.makeHeadingDecorator();

    this.seeIds();

    //
    // Some processing needs to be done before _process is called. In btw_mode,
    // these would be handled by triggers.
    //
    const senses = root.getElementsByClassName("btw:sense");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < senses.length; ++i) {
      const sense = senses[i];
      this.idDecorator(root, sense);
      this.headingDecorator.sectionHeadingDecorator(sense);
    }

    const subsenses = root.getElementsByClassName("btw:subsense");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < subsenses.length; ++i) {
      const subsense = subsenses[i];
      this.idDecorator(root, subsense);
      const explanation = domutil.childByClass(subsense, "btw:explanantion");
      if (explanation !== null) {
        this.explanationDecorator(root, explanation);
      }
    }

    //
    // We also need to perform the changes that are purely due to the fact that
    // the editing structure is different from the viewing structure.
    //
    this.transformEnglishRenditions();

    //
    // Transform btw:antonyms to the proper viewing format.
    //
    this.transformContrastiveItems("antonym");
    this.transformContrastiveItems("cognate");
    this.transformContrastiveItems("conceptual-proximate");

    //
    // We need to link the trees because some logic shared with btw_decorator
    // depends on it. We just link our single tree with itself.
    //
    domutil.linkTrees(root, root);
    guiUpdater.events.subscribe((ev) => {
      if (ev.name !== "InsertNodeAt" || !isElement(ev.node)) {
        return;
      }

      domutil.linkTrees(ev.node, ev.node);
    });

    // In btw_decorator, there are triggers that refresh hyperlinks as elements
    // are added or processed. Such triggers do not exist here so id decorations
    // need to be performed before anything else is done so that when hyperlinks
    // are decorated, everthing is available for them to be decorated.
    const withIds = root.querySelectorAll(`[${util.encodeAttrName("xml:id")}]`);
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < withIds.length; ++i) {
      const withId = withIds[i];
      this.idDecorator(root, withId);
    }

    // We unwrap the contents of all "resp" elements.
    const resps = root.getElementsByClassName("resp");
    // As we process each element, it is removed from the live list returned by
    // getElementsByClassName.
    while (resps.length !== 0) {
      const resp = resps[0];
      const respParent = resp.parentNode!;
      let child = resp.firstChild;
      while (child !== null) {
        respParent.insertBefore(child, resp);
        child = resp.firstChild;
      }
      respParent.removeChild(resp);
    }

    // We want to process all ref elements earlier so that hyperlinks to
    // examples are created properly.
    const refs = root.getElementsByClassName("ref");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < refs.length; ++i) {
      this.process(root, refs[i]);
    }

    this.process(root, root.firstElementChild!);

    // Work around a bug in Bootstrap. Bootstrap's scrollspy (at least up to
    // 3.3.1) can't handle a period in a URL's hash. It passes the has to jQuery
    // as a CSS selector and jQuery silently fails to find the object.
    const targets = root.querySelectorAll("[id]");
    // tslint:disable-next-line:prefer-for-of
    for (let targetIx = 0; targetIx < targets.length; ++targetIx) {
      const target = targets[targetIx];
      target.id = target.id.replace(/\./g, "_");
    }

    const links = root.getElementsByTagName("a");
    // tslint:disable-next-line:prefer-for-of
    for (let linkIx = 0; linkIx < links.length; ++linkIx) {
      const href = links[linkIx].getAttribute("href");
      if (href !== null && href.lastIndexOf("#", 0) === 0) {
        links[linkIx].setAttribute("href", href.replace(/\./g, "_"));
      }
    }

    this.createAffix();
    $(doc.body).on("click", (ev) => {
      // We are not using $.Event because setting bubbles to `false` does not
      // seem possible with `$.Event`.
      const $for = $(ev.target).closest("[data-toggle='popover']");
      $("[aria-describedby][data-toggle='popover']").not($for).each(
        function destroy(this: Element) : void {
          // We have to work around an issue in Bootstrap 3.3.7. If destroy is
          // called more than once on a popover or tooltip, it may cause an
          // error. We work around the issue by making sure we call it only if
          // the tip is .in.
          const popover = $.data(this, "bs.popover");
          if (popover) {
            const $tip = popover.tip();
            if ($tip && $tip[0].classList.contains("in")) {
              popover.destroy();
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
      const id = s.getAttribute(util.encodeAttrName("xml:id"));
      if (id !== null) {
        this.senseSubsenseIdManager.seen(id, true);
      }
    }

    const examples = root.querySelectorAll(this.mapped.toGUISelector(
      "btw:example, btw:example-explained"));
    // tslint:disable-next-line:one-variable-per-declaration
    for (let i = 0, limit = examples.length; i < limit; ++i) {
      const ex = examples[i];
      const id = ex.getAttribute(util.encodeAttrName("xml:id"));
      if (id !== null) {
        this.exampleIdManager.seen(id, true);
      }
    }
  }

  private createAffix(): void {
    // Create the affix
    const { doc, win, root } = this;

    const affix = doc.getElementById("btw-article-affix")!;
    this.populateAffix(affix);
    $(affix).affix({
      offset: {
        top: 1,
        bottom: 1,
      },
    });

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

    $(doc.body).on("activate.bs.scrollspy", (_ev) => {
      // Scroll the affix if needed.
      const affixRect = affixOverflow.getBoundingClientRect();
      const actives = affix.querySelectorAll(".active>a");
      // tslint:disable-next-line:prefer-for-of
      for (let i = 0; i < actives.length; ++i) {
        const active = actives[i];
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
    const anchors =
      root.querySelectorAll(this.mapped.toGUISelector("btw:subsense, .head"));
    let ulStack: Element[] = [topUl];
    const containerStack: Element[] = [];
    let prevContainer;
    // tslint:disable-next-line:prefer-for-of
    for (let anchorIx = 0; anchorIx < anchors.length; ++anchorIx) {
      const anchor = anchors[anchorIx];
      if (prevContainer && prevContainer.contains(anchor)) {
        containerStack.unshift(prevContainer);
        const ul = doc.createElement("ul");
        ul.className = "nav";
        ulStack[0].lastElementChild!.appendChild(ul);
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
      const orig = util.getOriginalName(anchor);
      switch (orig) {
      case "head":
        const prefix = anchor.textContent!.replace("•", "").trim();
        // Special cases
        const parent = anchor.parentNode as Element;
        switch (util.getOriginalName(parent)) {
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
          break;
        }
        prevContainer = parent;
        break;
      case "btw:subsense":
        heading = anchor.getElementsByClassName("btw:explanation")[0]
          .textContent!;
        prevContainer = anchor;
        break;
      default:
        throw new Error(`unknown element type: ${orig}`);
      }

      if (heading !== undefined && heading !== "") {
        const li = domutil.htmlToElements(
          _.template("<li><a href='#<%= target %>'><%= heading %></a></li>")(
            { target: anchor.id, heading }), doc)[0];
        ulStack[0].appendChild(li);
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
    let parent = closest(target, ".collapse:not(.in)");
    while (parent !== null) {
      parents.unshift(parent);
      parent = parent.parentNode as Element;
      parent = parent !== null ? closest(parent, ".collapse:not(.in)") : null;
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
      el.ownerDocument.createTextNode(sep) :
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
    const name = util.getOriginalName(el);

    switch (name) {
    case "persName":
      this.persNameDecorator(root, el);
      break;
    case "editor":
      this.editorDecorator(root, el);
      break;
    case "btw:sf":
      this.sfDecorator(root, el);
      break;
    default:
    }
  }

  editorDecorator(root: Element, el: Element): void {
    const class_ = "_editor_label";
    let label = domutil.childByClass(el, class_);
    if (label === null) {
      label = el.ownerDocument.createElement("div");
      label.className = `_text _phantom ${class_}`;
      label.textContent = "Editor: ";
      this.guiUpdater.insertBefore(el, label, el.firstChild);
    }
  }

  persNameDecorator(root: Element, el: Element): void {
    el.classList.add("_inline");

    const handleSeparator = (class_, where, text) => {
      const separatorClass = `_${class_}_separator`;
      const child = domutil.childByClass(el, class_);
      const exists = child !== null ? (child.childNodes.length !== 0) : false;
      const oldSeparator = domutil.childByClass(el, separatorClass);

      if (exists) {
        if (oldSeparator === null) {
          const separator = el.ownerDocument.createElement("div");
          separator.className = `_text _phantom ${separatorClass}`;
          separator.textContent = text;
          let before;
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
      const separator = el.ownerDocument.createElement("div");
      separator.className = `_text _phantom ${nameSeparatorClass}`;
      separator.textContent = " ";
      this.guiUpdater.insertBefore(el, separator, el.firstChild);
    }
  }

  private transformEnglishRenditions(): void {
    const { doc, root } = this;

    // Transform English renditions to the viewing format.
    const englishRenditions =
      root.getElementsByClassName("btw:english-renditions");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < englishRenditions.length; ++i) {
      // English renditions element
      const englishRenditionsEl = englishRenditions[i];
      const firstEnglishRendition =
        domutil.childByClass(englishRenditionsEl, "btw:english-rendition");
      //
      // Make a list of btw:english-terms that will appear at the start of the
      // btw:english-renditions.
      //

      // Slicing it prevents this list from growing as we add the clones.
      const terms: HTMLElement[] = _slice.call(
        englishRenditionsEl.getElementsByClassName("btw:english-term"));
      const div = this.makeElement("btw:english-term-list");
      for (let tIx = 0; tIx < terms.length; ++tIx) {
        const term = terms[tIx];
        const clone = term.cloneNode(true) as HTMLElement;
        clone.classList.add("_inline");
        div.appendChild(clone);
        if (tIx < terms.length - 1) {
          div.appendChild(doc.createTextNode(", "));
        }
      }
      englishRenditionsEl.insertBefore(div, firstEnglishRendition);

      //
      // Combine the contents of all btw:english-rendition into one
      // btw:semantic-fields element
      //
      // Slicing to prevent changes to the list as we remove elements.
      const ers = _slice.call(
        englishRenditionsEl.getElementsByClassName("btw:english-rendition"));
      let html: string = "";
      for (const er of ers) {
        html += er.innerHTML;
        er.parentNode.removeChild(er);
      }
      const sfs = this.makeElement("btw:semantic-fields-collection");
      // tslint:disable-next-line:no-inner-html
      sfs.innerHTML = html;
      englishRenditionsEl.appendChild(sfs);
      this.headingDecorator.sectionHeadingDecorator(sfs);
    }
  }

  private transformContrastiveItems(name: string): void {
    const root = this.root;
    // A "group" here is an element that combines a bunch of elements of the
    // same kind: btw:antonyms is a group of btw:antonym, btw:cognates is a
    // group of btw:cognates, etc. The elements of the same kind are called
    // "items" later in this code.

    const groupClass = `btw:${name}s`;
    const doc = root.ownerDocument;
    // groups are those elements that act as containers (btw:cognates,
    // btw:antonyms, etc.)
    const groups = _slice.call(root.getElementsByClassName(groupClass));
    for (const group of groups) {
      if (group.getElementsByClassName("btw:none").length) {
        // The group is empty. Remove the group and move on.
        group.parentNode.removeChild(group);
        continue;
      }

      // This div will contain the list of all terms in the group.
      const div = this.makeElement(`btw:${name}-term-list`);

      const head = doc.createElement("div");
      head.className = "head _phantom";
      head.textContent = "Terms in this section:";
      div.appendChild(head);

      // Slicing it prevents this list from growing as we add the clones.
      const terms = _slice.call(group.getElementsByClassName("btw:term"));

      // A wrapper is the element that wraps around the term. This loop: 1) adds
      // each wrapper to the .btw:...-term-list. and b) replaces each term with
      // a clone of the wrapper.
      const wrappers: Element[] = [];
      for (let tIx = 0; tIx < terms.length; ++tIx) {
        const term = terms[tIx];
        const clone = term.cloneNode(true);
        clone.classList.add("_inline");
        const termWrapper = this.makeElement(`btw:${name}-term-item`);
        termWrapper.textContent = `${name.replace("-", " ")} ${tIx + 1}: `;
        termWrapper.appendChild(clone);
        div.appendChild(termWrapper);

        const parent = term.parentNode;

        // This effectively replaces the term element in btw:antonym,
        // btw:cognate, etc. with an element that contains the "name i: "
        // prefix.
        parent.insertBefore(termWrapper.cloneNode(true), term);
        parent.removeChild(term);
        wrappers.push(termWrapper);
      }

      const firstTerm = group.querySelector(`.btw\\:${name}`);
      group.insertBefore(div, firstTerm);
      const hr = document.createElement("hr");
      hr.className = "hr _phantom";
      group.insertBefore(hr, firstTerm);

      //
      // Combine the contents of all of the items into one btw:citations
      // element.
      //
      // Slicing to prevent changes to the list as we remove elements.
      const items = _slice.call(group.getElementsByClassName(`btw:${name}`));
      let html: string = "";
      for (const item of items) {
        // What we are doing here is pushing on html the contents of a
        // btw:antonym, btw:cognate, etc. element. At this point, that's only
        // btw:citations elements plus btw:...-term-item elements.
        html += item.outerHTML;
        item.parentNode.removeChild(item);
      }
      const coll = this.makeElement("btw:citations-collection");
      // tslint:disable-next-line:no-inner-html
      coll.innerHTML = html;
      group.appendChild(coll);

      //
      // If there are btw:sematic-fields elements, move them to the list of
      // terms.
      //
      if (name === "cognate") {
        const cognates = coll.getElementsByClassName("btw:cognate");
        for (let cognateIx = 0; cognateIx < cognates.length; ++cognateIx) {
          const cognate = cognates[cognateIx];
          // We get only the first one, which is the one that contains the
          // combined semantic fields for the whole cognate.
          const sfss = cognate.getElementsByClassName("btw:semantic-fields")[0];
          const wrapper = wrappers[cognateIx];
          wrapper.parentNode!.insertBefore(sfss, wrapper.nextSibling);
        }
      }
    }
  }

  fetchAndFillBiblData(targetId: string, el: Element, abbr: Element): void {
    const data = this.biblData[targetId];
    if (data === undefined) {
      throw new Error("missing bibliographical data");
    }
    this.fillBiblData(el, abbr, data);
  }

  refDecorator(root: Element, el: Element): void {
    let origTarget = el.getAttribute(util.encodeAttrName("target"));
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
      a = el.ownerDocument.createElement("a");
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

      a = el.ownerDocument.createElement("a");
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

implement(Viewer, DispatchMixin);
