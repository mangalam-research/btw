/**
 * @module wed/modes/btw/btw_view
 * @desc Code for viewing documents edited by btw-mode.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends module:wed/modes/btw/btw_view */ function btwView(require,
                                                                    exports,
                                                                    _module) {
  "use strict";

  var convert = require("wed/convert");
  var TreeUpdater = require("wed/tree_updater").TreeUpdater;
  var util = require("wed/util");
  var domutil = require("wed/domutil");
  var oop = require("wed/oop");
  var dloc = require("wed/dloc");
  var SimpleEventEmitter =
        require("wed/lib/simple_event_emitter").SimpleEventEmitter;
  var Conditioned = require("wed/lib/conditioned").Conditioned;
  var transformation = require("wed/transformation");
  var btwMeta = require("./btw_meta");
  var HeadingDecorator = require("./btw_heading_decorator").HeadingDecorator;
  var btwRefmans = require("./btw_refmans");
  var DispatchMixin = require("./btw_dispatch").DispatchMixin;
  var idManager = require("./id_manager");
  var nameResolver = require("salve/name_resolver");
  var $ = require("jquery");
  var _ = require("lodash");
  require("bootstrap");
  require("bootstrap-treeview");
  var btwUtil = require("./btw_util");
  var ajax = require("ajax").ajax;
  var bluejax = require("bluejax");
  var sfTemplate = require("text!./btw_view_sf_template.html");
  var SFFetcher = require("./semantic_field_fetcher");

  var _slice = Array.prototype.slice;
  var closest = domutil.closest;

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
  function Viewer(root, editUrl, fetchUrl, semanticFieldFetchUrl,
                  data, biblData, languagePrefix) {
    SimpleEventEmitter.call(this);
    Conditioned.call(this);
    var doc = root.ownerDocument;
    var win = doc.defaultView;

    this._root = root;
    this._doc = doc;
    this._win = win;
    this._refmans = new btwRefmans.WholeDocumentManager();
    this._meta = new btwMeta.Meta();
    this._load_timeout = 30000;
    this._language_prefix = languagePrefix;
    this._semanticFieldFetchUrl = semanticFieldFetchUrl;

    this._resolver = new nameResolver.NameResolver();
    var mappings = this._meta.getNamespaceMappings();
    Object.keys(mappings).forEach(function definePrefix(key) {
      this._resolver.definePrefix(key, mappings[key]);
    }.bind(this));

    this._sfFetcher = new SFFetcher(this._semanticFieldFetchUrl,
                                    this._win.location.href);

    //
    // We provide minimal objects that are used by some of the logic
    // which is shared with btw_decorator.
    //
    this._editor = {
      toDataNode: function toDataNode(node) {
        return node;
      },
    };

    this._mode = {
      nodesAroundEditableContents: function nodesAroundEditableContents(_el) {
        return [null, null];
      },
    };

    this._sense_subsense_id_manager = new idManager.IDManager("S.");
    this._example_id_manager = new idManager.IDManager("E.");

    this._sense_tooltip_selector = "btw:english-term-list>btw:english-term";

    var collapse = btwUtil.makeCollapsible(doc, "default",
                                            "toolbar-heading",
                                            "toolbar-collapse", {
                                              group: "horizontal",
                                            });
    var frame = doc.getElementsByClassName("wed-frame")[0];
    collapse.heading.innerHTML =
      "<span class='fa fa-bars' style='width: 0.4em; overflow: hidden'></span>";

    var buttons = "<span>";
    if (editUrl) {
      buttons += _.template(
        "<a class='btw-edit-btn btn btn-default' title='Edit'\
      href='<%= editUrl %>'><i class='fa fa-fw fa-pencil-square-o'></i>\
  </a>")({ editUrl: editUrl });
    }
    buttons +=
      "<a class='btw-expand-all-btn btn btn-default' title='Expand All' href='#'>\
        <i class='fa fa-fw fa-caret-down'></i></a>\
<a class='btw-collapse-all-btn btn btn-default' title='Collapse All' \
    href='#'>\
        <i class='fa fa-fw fa-caret-right'></i></a></span>";

    collapse.content.innerHTML = buttons;

    // Make it so that it floats above everything else.
    collapse.group.style.position = "fixed";
    collapse.group.style.zIndex = "10";

    // This is necessary so that it collapses horizontally.
    collapse.content.parentNode.classList.add("width");

    frame.insertBefore(collapse.group, frame.firstChild);

    var expandAll = collapse.content
          .getElementsByClassName("btw-expand-all-btn")[0];
    $(expandAll).on("click", function clickHandler(ev) {
      var toOpen = doc.querySelectorAll(".wed-document .collapse:not(.in)");
      $(toOpen).collapse("show");
      $(collapse.content.parentNode).collapse("hide");
      ev.preventDefault();
    });

    var collapseAll = collapse.content
          .getElementsByClassName("btw-collapse-all-btn")[0];
    $(collapseAll).on("click", function clickHandler(ev) {
      var toClose = doc.querySelectorAll(".wed-document .collapse.in");
      $(toClose).collapse("hide");
      $(collapse.content.parentNode).collapse("hide");
      ev.preventDefault();
    });

    // If we are passed a fetchUrl, then we have to fetch the
    // data from the site.
    if (fetchUrl) {
      // Show the loading alert.
      var loading = document.querySelector(".wed-document>.loading");
      loading.style.display = "";
      var start = Date.now();
      var fetch = function _fetch() {
        ajax({
          url: fetchUrl,
          headers: {
            Accept: "application/json",
          },
        }).then(function then(ajaxData) {
          this.processData(ajaxData.xml, ajaxData.bibl_data);
        }.bind(this))
          .catch(bluejax.HttpError, function error(err) {
            var jqXHR = err.jqXHR;
            if (jqXHR.status === 404) {
              if (Date.now() - start > this._load_timeout) {
                this.failedLoading(
                  loading,
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
          }.bind(this))
          .catch(function done(err) {
            this._setCondition("done", this);
            throw err;
          }.bind(this));
      }.bind(this);
      fetch();
    }
    else {
      this.processData(data, biblData);
    }
  }

  Viewer.prototype.failedLoading = function failedLoading(loading, msg) {
    loading.classList.remove("alert-info");
    loading.classList.add("alert-danger");
    loading.innerHTML = msg || "Cannot load the document.";
    this._setCondition("done", this);
  };

  Viewer.prototype.processData = function processData(data, biblData) {
    this._bibl_data = biblData;

    var doc = this._doc;
    var win = this._win;
    var root = this._root;

    // Clear the root.
    root.innerHTML = "";


    var parser = new doc.defaultView.DOMParser();
    var dataDoc = parser.parseFromString(data, "text/xml");

    root.appendChild(convert.toHTMLTree(doc, dataDoc.firstChild));

    new dloc.DLocRoot(root); // eslint-disable-line no-new
    var guiUpdater = new TreeUpdater(root);

    this._data_doc = dataDoc;
    this._gui_updater = guiUpdater;

    var headingMap = {
      "btw:overview": "• OVERVIEW",
      "btw:sense-discrimination": "• SENSE DISCRIMINATION",
      "btw:historico-semantical-data": "• HISTORICO-SEMANTICAL DATA",
      "btw:credits": "• CREDITS",
    };

    // Override the head specs with those required for
    // viewing.
    this._heading_decorator = new HeadingDecorator(
      this._refmans, guiUpdater,
      headingMap, false /* implied_brackets */);

    this._heading_decorator.addSpec({ selector: "btw:definition",
                                     heading: null });
    this._heading_decorator.addSpec({ selector: "btw:english-rendition",
                                     heading: null });
    this._heading_decorator.addSpec({ selector: "btw:english-renditions",
                                     heading: null });
    this._heading_decorator.addSpec({ selector: "btw:semantic-fields",
                                     heading: null });
    this._heading_decorator.addSpec({
      selector: "btw:sense",
      heading: "",
      label_f: this._refmans.getSenseLabelForHead.bind(this._refmans),
      suffix: ".",
    });
    this._heading_decorator.addSpec({ selector: "btw:sense>btw:explanation",
                                      heading: null });
    this._heading_decorator.addSpec({ selector: "btw:subsense>btw:explanation",
                                      heading: null });
    this._heading_decorator.addSpec({
      selector: "btw:english-renditions>btw:semantic-fields-collection",
      heading: "semantic fields",
      collapse: {
        kind: "default",
        additional_classes: "sf-collapse",
      },
    });

    this._heading_decorator.addSpec({
      selector: "btw:contrastive-section",
      heading: "contrastive section",
      collapse: "default",
    });
    this._heading_decorator.addSpec({
      selector: "btw:antonyms",
      heading: "antonyms",
      collapse: "default",
    });
    this._heading_decorator.addSpec({
      selector: "btw:cognates",
      heading: "cognates",
      collapse: "default",
    });
    this._heading_decorator.addSpec({
      selector: "btw:conceptual-proximates",
      heading: "conceptual proximates",
      collapse: "default",
    });

    this._heading_decorator.addSpec({
      selector: "btw:cognate-term-list>btw:semantic-fields-collection",
      heading: "semantic fields",
      collapse: {
        kind: "default",
        additional_classes: "sf-collapse",
      },
    });
    this._heading_decorator.addSpec(
      { selector: "btw:semantic-fields-collection>btw:semantic-fields",
        heading: null });
    this._heading_decorator.addSpec({
      selector: "btw:sense>btw:semantic-fields",
      heading: "all semantic fields in the citations of this sense",
      collapse: {
        kind: "default",
        additional_classes: "sf-collapse",
      },
    });
    this._heading_decorator.addSpec({
      selector: "btw:overview>btw:semantic-fields",
      heading: "all semantic fields",
      collapse: {
        kind: "default",
        additional_classes: "sf-collapse",
      },
    });
    this._heading_decorator.addSpec({
      selector: "btw:semantic-fields",
      heading: "semantic fields",
      collapse: {
        kind: "default",
        additional_classes: "sf-collapse",
      },
    });
    this._heading_decorator.addSpec({
      selector: "btw:subsense>btw:citations",
      heading: null,
    });
    this._heading_decorator.addSpec({
      selector: "btw:sense>btw:citations",
      heading: null,
    });
    this._heading_decorator.addSpec({
      selector: "btw:antonym>btw:citations",
      heading: null,
    });
    this._heading_decorator.addSpec({
      selector: "btw:cognate>btw:citations",
      heading: null,
    });
    this._heading_decorator.addSpec({
      selector: "btw:conceptual-proximate>btw:citations",
      heading: null,
    });
    this._heading_decorator.addSpec({
      selector: "btw:citations-collection>btw:citations",
      heading: null,
    });
    this._heading_decorator.addSpec({
      selector: "btw:sense>btw:other-citations",
      heading: "more citations",
      collapse: "default",
    });
    this._heading_decorator.addSpec({
      selector: "btw:other-citations",
      heading: "more citations",
      collapse: "default",
    });

    var i;
    var limit;
    var id;
    var sensesSubsenses = root.querySelectorAll(domutil.toGUISelector(
      "btw:sense, btw:subsense"));
    for (i = 0, limit = sensesSubsenses.length; i < limit; ++i) {
      var s = sensesSubsenses[i];
      id = s.getAttribute(util.encodeAttrName("xml:id"));
      if (id) {
        this._sense_subsense_id_manager.seen(id, true);
      }
    }

    var examples = root.querySelectorAll(domutil.toGUISelector(
      "btw:example, btw:example-explained"));
    for (i = 0, limit = examples.length; i < limit; ++i) {
      var ex = examples[i];
      id = ex.getAttribute(util.encodeAttrName("xml:id"));
      if (id) {
        this._example_id_manager.seen(id, true);
      }
    }

    //
    // Some processing needs to be done before _process is called. In
    // btw_mode, these would be handled by triggers.
    //
    var senses = root.getElementsByClassName("btw:sense");
    for (i = 0; i < senses.length; ++i) {
      var sense = senses[i];
      this.idDecorator(root, sense);
      this._heading_decorator.sectionHeadingDecorator(sense);
    }

    var subsenses = root.getElementsByClassName("btw:subsense");
    for (i = 0; i < subsenses.length; ++i) {
      var subsense = subsenses[i];
      this.idDecorator(root, subsense);
      var explanation = domutil.childByClass(subsense, "btw:explanantion");
      if (explanation) {
        this.explanationDecorator(root, explanation);
      }
    }

    var terms;
    var term;
    var div;
    var tIx;
    var clone;
    var html;
    var sfs;

    //
    // We also need to perform the changes that are purely due to the
    // fact that the editing structure is different from the viewing
    // structure.
    //

    // Transform English renditions to the viewing format.
    var englishRenditions =
          root.getElementsByClassName("btw:english-renditions");
    for (i = 0; i < englishRenditions.length; ++i) {
      // English renditions element
      var englishRenditionsEl = englishRenditions[i];
      var firstEnglishRendition = domutil.childByClass(englishRenditionsEl,
                                                       "btw:english-rendition");
      //
      // Make a list of btw:english-terms that will appear at the
      // start of the btw:english-renditions.
      //

      // Slicing it prevents this list from growing as we add the clones.
      terms = _slice.call(
        englishRenditionsEl.getElementsByClassName("btw:english-term"));
      div = doc.createElement("div");
      div.classList.add("btw:english-term-list");
      div.classList.add("_real");
      for (tIx = 0; tIx < terms.length; ++tIx) {
        term = terms[tIx];
        clone = term.cloneNode(true);
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
      var ers = _slice.call(
        englishRenditionsEl.getElementsByClassName("btw:english-rendition"));
      html = [];
      for (var eIx = 0; eIx < ers.length; ++eIx) {
        var er = ers[eIx];
        html.push(er.innerHTML);
        er.parentNode.removeChild(er);
      }
      sfs = doc.createElement("div");
      sfs.classList.add("btw:semantic-fields-collection");
      sfs.classList.add("_real");
      sfs.innerHTML = html.join("");
      englishRenditionsEl.appendChild(sfs);
      this._heading_decorator.sectionHeadingDecorator(sfs);
    }

    //
    // Transform btw:antonyms to the proper viewing format.
    //
    this._transformContrastiveItems(root, "antonym");
    this._transformContrastiveItems(root, "cognate");
    this._transformContrastiveItems(root, "conceptual-proximate");

    //
    // We need to link the trees because some logic shared with
    // btw_decorator depends on it. We just link our single tree with
    // itself.
    //
    domutil.linkTrees(root, root);
    guiUpdater.addEventListener("insertNodeAt", function insertNodeAt(ev) {
      domutil.linkTrees(ev.node, ev.node);
    });

    //
    // In btw_decorator, there are triggers that refresh hyperlinks as
    // elements are added or processed. Such triggers do not exist
    // here so id decorations need to be performed before anything
    // else is done so that when hyperlinks are decorated, everthing
    // is available for them to be decorated.
    var withIds = root.querySelectorAll("[" + util.encodeAttrName("xml:id") +
                                         "]");
    for (i = 0; i < withIds.length; ++i) {
      var withId = withIds[i];
      this.idDecorator(root, withId);
    }

    // We unwrap the contents of all "resp" elements.
    var resps = root.getElementsByClassName("resp");
    // As we process each element, it is removed from the live list
    // returned by getElementsByClassName.
    while (resps.length) {
      var resp = resps[0];
      var respParent = resp.parentNode;
      var child = resp.firstChild;
      while (child) {
        respParent.insertBefore(child, resp);
        child = resp.firstChild;
      }
      respParent.removeChild(resp);
    }

    // We want to process all ref elements earlier so that hyperlinks
    // to examples are created properly.
    var refs = root.getElementsByClassName("ref");
    for (i = 0; i < refs.length; ++i) {
      var ref = refs[i];
      this.process(root, ref);
    }

    this.process(root, root.firstElementChild);

    // Work around a bug in Bootstrap. Bootstrap's scrollspy (at least
    // up to 3.3.1) can't handle a period in a URL's hash. It passes
    // the has to jQuery as a CSS selector and jQuery silently fails
    // to find the object.
    var targets = root.querySelectorAll("[id]");
    for (var targetIx = 0; targetIx < targets.length; ++targetIx) {
      var target = targets[targetIx];
      target.id = target.id.replace(/\./g, "_");
    }

    var links = root.getElementsByTagName("a");
    for (var linkIx = 0; linkIx < links.length; ++linkIx) {
      var href = links[linkIx].attributes.href;
      if (!href || href.value.lastIndexOf("#", 0) !== 0) {
        continue;
      }
      href.value = href.value.replace(/\./g, "_");
    }

    // Create the affix
    var affix = doc.getElementById("btw-article-affix");
    var topUl = affix.getElementsByTagName("ul")[0];
    var anchors = root.querySelectorAll(
      domutil.toGUISelector("btw:subsense, .head"));
    var ulStack = [topUl];
    var containerStack = [];
    var prevContainer;
    var ul;
    for (var anchorIx = 0; anchorIx < anchors.length; ++anchorIx) {
      var anchor = anchors[anchorIx];
      if (prevContainer && prevContainer.contains(anchor)) {
        containerStack.unshift(prevContainer);
        ul = doc.createElement("ul");
        ul.className = "nav";
        ulStack[0].lastElementChild.appendChild(ul);
        ulStack.unshift(ul);
      }
      else {
        while (containerStack[0] && !containerStack[0].contains(anchor)) {
          containerStack.shift();
          ulStack.shift();
        }
        if (ulStack.length === 0) {
          ulStack = [topUl];
        }
      }


      var orig = util.getOriginalName(anchor);

      var heading;
      switch (orig) {
      case "head":
        heading = anchor.textContent.replace("•", "").trim();
        // Special cases
        var parent = anchor.parentNode;
        switch (util.getOriginalName(parent)) {
        case "btw:sense":
          terms = parent.querySelector(
            domutil.toGUISelector("btw:english-term-list"));
          heading += " " + (terms ? terms.textContent : "");
          break;
        case "btw:antonym-term-list":
        case "btw:cognate-term-list":
        case "btw:conceptual-proximate-term-list":
          // We suppress these.
          heading = "";
          break;
        default:
          break;
        }
        prevContainer = anchor.parentNode;
        break;
      case "btw:subsense":
        heading = anchor.getElementsByClassName("btw:explanation")[0]
          .textContent;
        prevContainer = anchor;
        break;
      default:
        throw new Error("unknown element type: " + orig);
      }

      if (heading) {
        var li = domutil.htmlToElements(
          _.template("<li><a href='#<%= target %>'><%= heading %></a></li>")(
            { target: anchor.id, heading: heading }), doc)[0];
        ulStack[0].appendChild(li);
      }
    }

    $(affix).affix({
      offset: {
        top: 1,
        bottom: 1,
      },
    });

    $(doc.body).scrollspy({ target: "#btw-article-affix" });

    var expandableToggle = affix.querySelector(".expandable-heading .btn");
    var $expandableToggle = $(expandableToggle);
    var affixConstrainer = domutil.closest(affix, "div");
    var affixOverflow = affix.getElementsByClassName("overflow")[0];
    var $affix = $(affix);

    var frame = doc.getElementsByClassName("wed-frame")[0];
    function expandHandler(ev) {
      if (affix.classList.contains("expanding")) {
        return;
      }

      var frameRect = frame.getBoundingClientRect();
      var constrainerRect = affixConstrainer.getBoundingClientRect();

      if (!affix.classList.contains("expanded")) {
        affix.classList.add("expanding");
        affix.style.left = constrainerRect.left + "px";
        affix.style.width = affixConstrainer.offsetWidth + "px";
        $affix.animate({
          left: frameRect.left,
          width: frameRect.width,
        }, 1000, function done() {
          affix.classList.remove("expanding");
          affix.classList.add("expanded");
        });
      }
      else {
        var constrainerStyle = window.getComputedStyle(affixConstrainer);
        $affix.animate({
          left: constrainerRect.left +
            parseInt(constrainerStyle.paddingLeft, 10),
          width: $(affixConstrainer).innerWidth() -
            parseInt(constrainerStyle.paddingLeft, 10),
        }, 1000, function done() {
          affix.style.left = "";
          affix.style.top = "";
          affix.classList.remove("expanded");
        });
      }
      ev.stopPropagation();
    }

    var container = doc.getElementsByClassName("container")[0];
    function resizeHandler() {
      $expandableToggle.off("click");
      $affix.off("click");
      var containerRect = container.getBoundingClientRect();
      var constrainerRect = affixConstrainer.getBoundingClientRect();
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

      var style = window.getComputedStyle(affix);
      var constrainerStyle = window.getComputedStyle(affixConstrainer);
      if (affix.classList.contains("expanded")) {
        var frameRect = frame.getBoundingClientRect();
        affix.style.width = frameRect.width + "px";
        affix.style.left = frameRect.left + "px";
      }
      else {
        // This prevents the affix from popping wider when we scroll
        // the window. Because a "detached" affix has "position:
        // fixed", it is taken out of the flow and thus its "width" is
        // no longer constrained by its parent.

        affix.style.width = $(affixConstrainer).innerWidth() -
          parseInt(constrainerStyle.paddingLeft, 10) + "px";
      }
      var rect = affixOverflow.getBoundingClientRect();
      affixOverflow.style.height =
        (window.innerHeight - rect.top -
         parseInt(style.marginBottom, 10) - 5) + "px";
    }
    win.addEventListener("resize", resizeHandler);
    win.addEventListener("scroll", resizeHandler);
    resizeHandler();

    $(doc.body).on("activate.bs.scrollspy", function activateScrollSpy(_ev) {
      // Scroll the affix if needed.
      var actives = affix.querySelectorAll(".active>a");
      var affixRect = affixOverflow.getBoundingClientRect();
      for (i = 0; i < actives.length; ++i) {
        var active = actives[i];
        if (active.getElementsByClassName("active").length) {
          continue;
        }
        var activeRect = active.getBoundingClientRect();
        affixOverflow.scrollTop = Math.floor(activeRect.top - affixRect.top);
      }
    });


    $(doc.body).on("click", function bodyClick(ev) {
      var $target = $(ev.target);
      // We are not using $.Event because setting bubbles to `false` does not
      // seem possible with `$.Event`.
      var $for = $target.closest("[data-toggle='popover']");
      $("[aria-describedby][data-toggle='popover']").not($for).each(
        function destroy() {
          // We have to work around an issue in Bootstrap 3.3.7. If destroy is
          // called more than once on a popover or tooltip, it may cause an
          // error. We work around the issue by making sure we call it only if
          // the tip is .in.
          var popover = $.data(this, "bs.popover");
          if (popover) {
            var $tip = popover.tip();
            if ($tip && $tip[0].classList.contains("in")) {
              popover.destroy();
            }
          }
        });
    });

    var bound = this._showTarget.bind(this);
    win.addEventListener("popstate", bound);
    // This also catches hitting the Enter key on a link.
    $(root).on("click", "a[href]:not([data-toggle], [href='#'])",
               function click() {
                 setTimeout(bound, 0);
               });
    this._showTarget();

    this._setCondition("done", this);
  };

  oop.implement(Viewer, DispatchMixin);
  oop.implement(Viewer, SimpleEventEmitter);
  oop.implement(Viewer, Conditioned);

  Viewer.prototype._showTarget = function _showTarget() {
    var hash = this._win.location.hash;
    if (!hash) {
      return;
    }

    var target = this._doc.getElementById(hash.slice(1));
    if (!target) {
      return;
    }

    var parents = [];
    var parent = closest(target, ".collapse:not(.in)");
    while (parent) {
      parents.unshift(parent);
      parent = parent.parentNode;
      parent = parent && closest(parent, ".collapse:not(.in)");
    }

    function next(level) {
      var $level = $(level);
      $level.one("shown.bs.collapse", function shown() {
        if (parents.length) {
          next(parents.shift());
          return;
        }
        // We get here only once all sections have been expanded.
        target.scrollIntoView(true);
      });
      $level.collapse("show");
    }

    if (parents.length) {
      next(parents.shift());
    }
    else {
      target.scrollIntoView(true);
    }
  };

  Viewer.prototype.process = function process(root, el) {
    this.dispatch(root, el);
    el.classList.remove("_phantom");

    // Process the children...
    var children = el.children;
    for (var i = 0, limit = children.length; i < limit; ++i) {
      this.process(root, children[i]);
    }
  };

  Viewer.prototype.listDecorator = function listDecorator(el, sep) {
    // If sep is a string, create an appropriate div.
    var sepNode;
    if (typeof sep === "string") {
      sepNode = el.ownerDocument.createTextNode(sep);
    }
    else {
      sepNode = sep;
    }

    var first = true;
    var child = el.firstElementChild;
    while (child) {
      if (child.classList.contains("_real")) {
        if (!first) {
          this._gui_updater.insertBefore(el, sepNode.cloneNode(true), child);
        }
        else {
          first = false;
        }
      }
      child = child.nextElementSibling;
    }
  };

  Viewer.prototype.languageDecorator = function languageDecorator() {
  };

  Viewer.prototype.noneDecorator = function noneDecorator() {
  };

  Viewer.prototype.elementDecorator = function elementDecorator(root, el) {
    var name = util.getOriginalName(el);

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
  };

  function prependLabel(name, text, el, dec) {
    var class_ = "_" + name + "_label";
    var label = domutil.childByClass(el, class_);
    if (!label) {
      label = el.ownerDocument.createElement("div");
      label.className = "_text _phantom " + class_;
      label.textContent = text;
      dec._gui_updater.insertBefore(el, label, el.firstChild);
    }
  }

  Viewer.prototype.editorDecorator = function editorDecorator(root, el) {
    prependLabel("editor", "Editor: ", el, this);
  };

  Viewer.prototype.persNameDecorator = function persNameDecorator(root, el) {
    var dec = this;
    el.classList.add("_inline");

    function handleSeparator(class_, where, text) {
      var separatorClass = "_" + class_ + "_separator";
      var child = domutil.childByClass(el, class_);
      var exists = child && child.childNodes.length;
      var oldSeparator = domutil.childByClass(el, separatorClass);

      if (exists) {
        if (!oldSeparator) {
          var separator = el.ownerDocument.createElement("div");
          separator.className = "_text _phantom " + separatorClass;
          separator.textContent = text;
          var before;
          switch (where) {
          case "after":
            before = child.nextSibling;
            break;
          case "before":
            before = child;
            break;
          default:
            throw new Error("unknown value for where: " + where);
          }
          dec._gui_updater.insertBefore(el, separator, before);
        }
      }
      else if (oldSeparator) {
        dec._gui_updater.removeNode(oldSeparator);
      }
    }

    handleSeparator("forename", "after", " ");
    handleSeparator("genName", "before", ", ");

    var nameSeparatorClass = "_persNamename_separator";
    var oldNameSeparator = domutil.childByClass(el, nameSeparatorClass);

    if (!oldNameSeparator) {
      var separator = el.ownerDocument.createElement("div");
      separator.className = "_text _phantom " + nameSeparatorClass;
      separator.textContent = " ";
      dec._gui_updater.insertBefore(el, separator, el.firstChild);
    }
  };


  Viewer.prototype.sfDecorator = function sfDecorator(root, el) {
    var initialContent = "<i class='fa fa-spinner fa-2x fa-spin'></i>";
    var a = el.ownerDocument.createElement("a");
    a.className = "btn btn-default sf-popover-button";
    a.setAttribute("role", "button");
    a.setAttribute("tabindex", "0");
    a.setAttribute("data-toggle", "popover");

    var parent = el.parentNode;
    parent.insertBefore(a, el);
    a.appendChild(el);
    var $a = $(a);
    var dataWedRef = el.attributes["data-wed-ref"];
    var ref;
    if (dataWedRef) {
      ref = el.attributes["data-wed-ref"].value;
    }

    // We do not decorate if we have no references.
    if (ref === undefined) {
      return;
    }

    var alreadyResolved;
    var makeContent = function makeContent() {
      if (!alreadyResolved) {
        this._sfFetcher.fetch([ref]).then(function then(resolved) {
          alreadyResolved = resolved;
          // This causes rerendering of the popover and makeContent to be
          // called again.
          $a.popover("show");
        });

        return initialContent;
      }

      var popover = $a.data("bs.popover");
      var $tip = popover.tip();
      var tip = $tip[0];

      var content = tip.getElementsByClassName("popover-content")[0];
      var keys = Object.keys(alreadyResolved).sort();
      var keyIx = 0;

      content.innerHTML = _.template(sfTemplate)({ keys: keys,
                                                   resolved: alreadyResolved });

      var treeDivs = tip.getElementsByClassName("tree");
      for (var treeDivIx = 0; treeDivIx < treeDivs.length; ++treeDivIx) {
        var treeDiv = treeDivs[treeDivIx];
        var key = keys[keyIx++];
        var field = alreadyResolved[key];

        if (field.tree.length === 0) {
          continue; // Nothing to show!
        }

        // If there is only one element at the top of the tree, and this element
        // has only one child, then what we have is a single entry which would
        // have only one version available. There's no need to have a proper
        // tree for this.
        if (field.tree.length === 1 && field.tree[0].nodes.length <= 1) {
          var node = field.tree[0];
          var link = treeDiv.ownerDocument.createElement("a");
          link.textContent = node.text;
          link.href = node.href;
          treeDiv.appendChild(link);
          continue;
        }

        // Otherwise: build a tree.
        $(treeDiv).treeview({
          data: field.tree,
          enableLinks: true,
          levels: 0,
        });
      }

      // Inform that the popover has been fully rendered. This is used mainly in
      // testing.
      $a.trigger("fully-rendered.btw-view.sf-popover");

      return Array.prototype.slice.call(content.childNodes);
    }.bind(this);

    $a.on("click", function click() {
      // If there is already a popover existing for this element, this call
      // won't create a new one.
      $a.popover({
        html: true,
        trigger: "manual",
        content: makeContent,
      });

      var popover = $a.data("bs.popover");

      // The stock hasContent is very expensive.
      popover.hasContent = function hasContent() {
        return true;
      };

      var $tip = popover.tip();
      var tip = $tip[0];

      // Note that we destroy the popover when we "close" it. This is also why
      // we add the event handlers below for every click that shows the
      // popup. If the popover is recreated, then ``tip`` will be new, and
      // destroying the popup removes the event handlers that were created.
      var method = tip.classList.contains("in") ? "destroy" : "show";
      popover[method]();

      // If we're not showing the popup, then we are done.
      if (method !== "show") {
        return;
      }

      // Otherwise, we need to set handlers.
      tip.classList.add("sf-popover");

      $tip.on("click", function tipClick(ev) {
        ev.stopPropagation();
      });
    });
  };


  Viewer.prototype._transformContrastiveItems =
    function _transformContrastiveItems(root, name) {
      // A "group" here is an element that combines a bunch of elements
      // of the same kind: btw:antonyms is a group of btw:antonym,
      // btw:cognates is a group of btw:cognates, etc. The elements of
      // the same kind are called "items" later in this code.

      var groupClass = "btw:" + name + "s";
      var doc = root.ownerDocument;
      // groups are those elements that act as containers (btw:cognates,
      // btw:antonyms, etc.)
      var groups = _slice.call(root.getElementsByClassName(groupClass));
      for (var i = 0; i < groups.length; ++i) {
        var group = groups[i];
        if (group.getElementsByClassName("btw:none").length) {
          // The group is empty. Remove the group and move on.
          group.parentNode.removeChild(group);
          continue;
        }

        // This div will contain the list of all terms in the group.
        var div = doc.createElement("div");
        div.className = "btw:" + name + "-term-list _real";

        var head = doc.createElement("div");
        head.className = "head _phantom";
        head.textContent = "Terms in this section:";
        div.appendChild(head);

        // Slicing it prevents this list from growing as we add the clones.
        var terms = _slice.call(group.getElementsByClassName("btw:term"));

        // A wrapper is the element that wraps around the term. This
        // loop: 1) adds each wrapper to the .btw:...-term-list. and
        // b) replaces each term with a clone of the wrapper.
        var wrappers = [];
        for (var tIx = 0; tIx < terms.length; ++tIx) {
          var term = terms[tIx];
          var clone = term.cloneNode(true);
          clone.classList.add("_inline");
          var termWrapper = doc.createElement("div");
          termWrapper.classList.add("btw:" + name + "-term-item");
          termWrapper.classList.add("_real");
          termWrapper.textContent = name.replace("-", " ") + " " +
            (tIx + 1) + ": ";
          termWrapper.appendChild(clone);
          div.appendChild(termWrapper);

          var parent = term.parentNode;

          // This effectively replaces the term element in
          // btw:antonym, btw:cognate, etc. with an element that
          // contains the "name i: " prefix.
          parent.insertBefore(termWrapper.cloneNode(true), term);
          parent.removeChild(term);
          wrappers.push(termWrapper);
        }

        var firstTerm = group.querySelector(".btw\\:" + name);
        group.insertBefore(div, firstTerm);
        var hr = document.createElement("hr");
        hr.className = "hr _phantom";
        group.insertBefore(hr, firstTerm);

        //
        // Combine the contents of all of the items into one
        // btw:citations element
        //
        // Slicing to prevent changes to the list as we remove elements.
        var items = _slice.call(group.getElementsByClassName("btw:" + name));
        var html = [];
        for (var aIx = 0; aIx < items.length; ++aIx) {
          var item = items[aIx];
          // What we are doing here is pushing on html the contents
          // of a btw:antonym, btw:cognate, etc. element. At this
          // point, that's only btw:citations elements plus
          // btw:...-term-item elements.
          html.push(item.outerHTML);
          item.parentNode.removeChild(item);
        }
        var coll = this.makeElement("btw:citations-collection");
        coll.innerHTML = html.join("");
        group.appendChild(coll);

        //
        // If there are btw:sematic-fields elements, move them to
        // the list of terms.
        //
        if (name === "cognate") {
          var cognates = coll.getElementsByClassName("btw:cognate");
          for (var cognateIx = 0; cognateIx < cognates.length; ++cognateIx) {
            var cognate = cognates[cognateIx];
            // We get only the first one, which is the one that
            // contains the combined semantic fields for the whole
            // cognate.
            var sfss = cognate.getElementsByClassName(
              "btw:semantic-fields")[0];
            var wrapper = wrappers[cognateIx];
            wrapper.parentNode.insertBefore(sfss, wrapper.nextSibling);
          }
        }
      }
    };

  Viewer.prototype.fetchAndFillBiblData =
    function fetchAndFillBiblData(targetId, el, abbr) {
      var data = this._bibl_data[targetId];
      if (!data) {
        throw new Error("missing bibliographical data");
      }
      this.fillBiblData(el, abbr, data);
    };

  Viewer.prototype.refDecorator = function refDecorator(root, el) {
    var origTarget = el.getAttribute(util.encodeAttrName("target"));
    if (!origTarget) {
      origTarget = "";
    }

    origTarget = origTarget.trim();

    var biblPrefix = "/bibliography/";
    var entryPrefix = this._language_prefix + "/lexicography/entry/";
    var a;
    var child;
    if (origTarget.lastIndexOf(biblPrefix, 0) === 0) {
      // We want to remove any possible a element before we give
      // control to the overriden function.
      a = domutil.childByClass(el, "a");
      if (a) {
        child = a.firstChild;
        while (child) {
          el.insertBefore(child, a);
          child = a.firstChild;
        }
        el.removeChild(a);
      }

      DispatchMixin.prototype.refDecorator.call(this, root, el);

      // Bibliographical reference...
      var targetId = origTarget;

      var data = this._bibl_data[targetId];
      if (!data) {
        throw new Error("missing bibliographical data");
      }

      // We also want a hyperlink into the Zotero library.
      a = el.ownerDocument.createElement("a");
      a.className = "a _phantom_wrap";
      // When the item is a secondary source, ``zotero_url`` is at the
      // top level. If it is a secondary source, ``zotero_url`` is
      // inside the ``item`` field.
      a.href = (data.zotero_url ?
                data.zotero_url : data.item.zotero_url);
      a.setAttribute("target", "_blank");

      child = el.firstChild;
      el.appendChild(a);
      while (child && child !== a) {
        a.appendChild(child);
        child = el.firstChild;
      }
    }
    else if (origTarget.lastIndexOf(entryPrefix, 0) === 0) {
      a = domutil.childByClass(el, "a");
      if (a) {
        child = a.firstChild;
        while (child) {
          el.insertBefore(child, a);
          child = a.firstChild;
        }
        el.removeChild(a);
      }

      a = el.ownerDocument.createElement("a");
      a.className = "a _phantom_wrap";
      a.href = origTarget;
      a.setAttribute("target", "_blank");

      child = el.firstChild;
      el.appendChild(a);
      while (child && child !== a) {
        a.appendChild(child);
        child = el.firstChild;
      }
    }
    else {
      DispatchMixin.prototype.refDecorator.call(this, root, el);
    }
  };

  Viewer.prototype.makeElement = function makeElement(name, attrs) {
    var ename = this._resolver.resolveName(name);
    var e = transformation.makeElement(this._data_doc, ename.ns, name, attrs);
    return convert.toHTMLTree(this._doc, e);
  };

  return Viewer;
});
