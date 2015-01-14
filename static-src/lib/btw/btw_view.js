/**
 * @module wed/modes/btw/btw_view
 * @desc Code for viewing documents edited by btw-mode.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_view */
    function (require, exports, module) {
'use strict';

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
var btw_meta = require("./btw_meta");
var HeadingDecorator = require("./btw_heading_decorator").HeadingDecorator;
var btw_refmans = require("./btw_refmans");
var DispatchMixin = require("./btw_dispatch").DispatchMixin;
var id_manager = require("./id_manager");
var name_resolver = require("salve/name_resolver");
var $ = require("jquery");
var _ = require("lodash");
var btw_util = require("./btw_util");
var btw_semantic_fields = require("./btw_semantic_fields");

var _slice = Array.prototype.slice;
var _indexOf = Array.prototype.indexOf;
var closest = domutil.closest;

/**
 * @param {Element} root The element of ``wed-document`` class that is
 * meant to hold the viewed document.
 * @param {string} edit_url The url through which the document may be
 * edited.
 * @param {string} data The document, as XML.
 * @param {string} bibl_data The bibliographical data. This is a
 * mapping of targets (i.e. the targets given to the ``ref`` tags that
 * point to bibliographical items) to dictionaries that contain the
 * same values those returned as when asking the server to resolve
 * these targets individually. This mapping must be
 * complete. Otherwise, it is an internal error.
 */
function Viewer(root, edit_url, data, bibl_data) {
    SimpleEventEmitter.call(this);
    Conditioned.call(this);
    var doc = root.ownerDocument;
    var win = doc.defaultView;

    var collapse = btw_util.makeCollapsible(doc, "default",
                                            "toolbar-heading",
                                            "toolbar-collapse", {
                                                group: "horizontal"
                                            });
    var frame = doc.getElementsByClassName("wed-frame")[0];
    collapse.heading.innerHTML = "<span class='fa fa-bars' style='width: 0.4em; overflow: hidden'></span>";

    var buttons = '<span>';
    if (edit_url) {
        buttons += _.template(
'<a class="btw-edit-btn btn btn-default" title="Edit"\
      href="<%= edit_url %>"><i class="fa fa-fw fa-pencil-square-o"></i>\
  </a>', { edit_url: edit_url });
    }
    buttons +=
'<a class="btw-expand-all-btn btn btn-default" title="Expand All" href="#">\
        <i class="fa fa-fw fa-caret-down"></i></a>\
<a class="btw-collapse-all-btn btn btn-default" title="Collapse All" \
    href="#">\
        <i class="fa fa-fw fa-caret-right"></i></a></span>';

    collapse.content.innerHTML = buttons;

    // Make it so that it floats above everything else.
    collapse.group.style.position = 'fixed';
    collapse.group.style.zIndex = "10";

    // This is necessary so that it collapses horizontally.
    collapse.content.parentNode.classList.add("width");

    frame.insertBefore(collapse.group, frame.firstChild);

    var expand_all = collapse.content
            .getElementsByClassName("btw-expand-all-btn")[0];
    $(expand_all).on('click', function (ev) {
        var to_open = doc.querySelectorAll(
            ".wed-document .collapse:not(.in)");
        $(to_open).collapse('show');
        $(collapse.content.parentNode).collapse('hide');
        ev.preventDefault();
    });

    var collapse_all = collapse.content
            .getElementsByClassName("btw-collapse-all-btn")[0];
    $(collapse_all).on('click', function (ev) {
        var to_close = doc.querySelectorAll(".wed-document .collapse.in");
        $(to_close).collapse('hide');
        $(collapse.content.parentNode).collapse('hide');
        ev.preventDefault();
    });

    var parser = new doc.defaultView.DOMParser();
    var data_doc = parser.parseFromString(data, "text/xml");
    root.appendChild(convert.toHTMLTree(doc, data_doc.firstChild));

    new dloc.DLocRoot(root);
    var gui_updater = new TreeUpdater(root);

    this._doc = doc;
    this._data_doc = data_doc;
    this._gui_updater = gui_updater;
    this._refmans = new btw_refmans.WholeDocumentManager();
    this._meta = new btw_meta.Meta();
    this._bibl_data = bibl_data;

    this._resolver = new name_resolver.NameResolver();
    var mappings = this._meta.getNamespaceMappings();
    Object.keys(mappings).forEach(function (key) {
        this._resolver.definePrefix(key, mappings[key]);
    }.bind(this));

    //
    // We provide minimal objects that are used by some of the logic
    // which is shared with btw_decorator.
    //
    this._editor = {
        toDataNode: function (node) { return node; }
    };

    this._mode = {
        nodesAroundEditableContents: function (el) {
            return [null, null];
        }
    };

    var heading_map = {
        "btw:overview": "• OVERVIEW",
        "btw:sense-discrimination": "• SENSE DISCRIMINATION",
        "btw:historico-semantical-data": "• HISTORICO-SEMANTICAL DATA"
    };

    // Override the head specs with those required for
    // viewing.
    this._heading_decorator = new HeadingDecorator(
        this._refmans, gui_updater,
        heading_map, false /* implied_brackets */);

    this._heading_decorator.addSpec({selector: "btw:definition",
                                     heading: null});
    this._heading_decorator.addSpec({selector: "btw:english-rendition",
                                     heading: null});
    this._heading_decorator.addSpec({selector: "btw:english-renditions",
                                     heading: null});
    this._heading_decorator.addSpec({selector: "btw:semantic-fields",
                                     heading: null});
    this._heading_decorator.addSpec(
    {
        selector: "btw:sense",
        heading: "",
        label_f: this._refmans.getSenseLabelForHead.bind(this._refmans),
        suffix: "."
    });
    this._heading_decorator.addSpec(
        {selector: "btw:sense>btw:explanation",
         heading: null});
    this._heading_decorator.addSpec(
        {selector: "btw:subsense>btw:explanation",
         heading: null});
    this._heading_decorator.addSpec(
        {selector: "btw:english-renditions>btw:semantic-fields-collection",
         heading: "semantic fields",
         collapse: {
             kind: "default",
             additional_classes: "sf-collapse"
         }
        });

    this._heading_decorator.addSpec({
        selector: "btw:contrastive-section",
        heading: "contrastive section",
        collapse: "default"
    });
    this._heading_decorator.addSpec({
        selector: "btw:antonyms",
        heading: "antonyms",
        collapse: "default"
    });
    this._heading_decorator.addSpec({
        selector: "btw:cognates",
        heading: "cognates",
        collapse: "default"
    });
    this._heading_decorator.addSpec({
        selector: "btw:conceptual-proximates",
        heading: "conceptual proximates",
        collapse: "default"
    });

    this._heading_decorator.addSpec(
        {selector: "btw:cognate-term-list>btw:semantic-fields-collection",
         heading: "semantic fields",
         collapse: {
             kind: "default",
             additional_classes: "sf-collapse"
         }
        });
    this._heading_decorator.addSpec(
        {selector: "btw:semantic-fields-collection>btw:semantic-fields",
         heading: null});
    this._heading_decorator.addSpec(
        {selector: "btw:sense>btw:semantic-fields",
         heading: "all semantic fields in the citations of this sense",
         collapse: {
             kind: "default",
             additional_classes: "sf-collapse"
         }
        });
    this._heading_decorator.addSpec(
        {selector: "btw:overview>btw:semantic-fields",
         heading: "all semantic fields",
         collapse: {
             kind: "default",
             additional_classes: "sf-collapse"
         }
        });
    this._heading_decorator.addSpec(
        {selector: "btw:semantic-fields",
         heading: "semantic fields",
         collapse: {
             kind: "default",
             additional_classes: "sf-collapse"
         }
        });
    this._heading_decorator.addSpec({
        selector: "btw:subsense>btw:citations",
        heading: null
    });
    this._heading_decorator.addSpec({
        selector: "btw:sense>btw:citations",
        heading: null
    });
    this._heading_decorator.addSpec({
        selector: "btw:antonym>btw:citations",
        heading: null
    });
    this._heading_decorator.addSpec({
        selector: "btw:cognate>btw:citations",
        heading: null
    });
    this._heading_decorator.addSpec({
        selector: "btw:conceptual-proximate>btw:citations",
        heading: null
    });
    this._heading_decorator.addSpec({
        selector: "btw:citations-collection>btw:citations",
        heading: null
    });
    this._heading_decorator.addSpec({
        selector: "btw:sense>btw:other-citations",
        heading: "more citations",
        collapse: "default"
    });
    this._heading_decorator.addSpec({
        selector: "btw:other-citations",
        heading: "more citations",
        collapse: "default"
    });

    this._sense_subsense_id_manager = new id_manager.IDManager("S.");
    this._example_id_manager = new id_manager.IDManager("E.");

    this._sense_tooltip_selector = "btw:english-term-list>btw:english-term";

    var i, limit, id;
    var senses_subsenses = root.querySelectorAll(domutil.toGUISelector(
        "btw:sense, btw:subsense"));
    for(i = 0, limit = senses_subsenses.length; i < limit; ++i) {
        var s = senses_subsenses[i];
        id = s.getAttribute(util.encodeAttrName("xml:id"));
        if (id)
            this._sense_subsense_id_manager.seen(id, true);
    }

    var examples = root.querySelectorAll(domutil.toGUISelector(
        "btw:example, btw:example-explained"));
    for(i = 0, limit = examples.length; i < limit; ++i) {
        var ex = examples[i];
        id = ex.getAttribute(util.encodeAttrName("xml:id"));
        if (id)
            this._example_id_manager.seen(id, true);
    }

    //
    // Some processing needs to be done before _process is called. In
    // btw_mode, these would be handled by triggers.
    //
    var senses = root.getElementsByClassName("btw:sense");
    var sense;
    for(i = 0, sense; (sense = senses[i]) !== undefined; ++i) {
        this.idDecorator(root, sense);
        this._heading_decorator.sectionHeadingDecorator(sense);
    }

    var subsenses = root.getElementsByClassName("btw:subsense");
    var subsense;
    for(i = 0, subsense; (subsense = subsenses[i]) !== undefined; ++i) {
        this.idDecorator(root, subsense);
        var explanation = domutil.childByClass(subsense, "btw:explanantion");
        if (explanation)
            this.explanationDecorator(root, explanation);
    }

    var terms, term, div, t_ix, clone, html, sfs;

    //
    // We also need to perform the changes that are purely due to the
    // fact that the editing structure is different from the viewing
    // structure.
    //

    // Combine the semantic fields of each sense from those semantic
    // fields assigned to the citations of the sense (but not those in
    // the contrastive section).
    for(i = 0, sense; (sense = senses[i]) !== undefined; ++i) {
        // There can be only one contrastive section.
        var contrastive =
                sense.getElementsByClassName("btw:contrastive-section")[0];
        // We get all btw:sf elements that are outside the
        // contrastive section.
        /* jshint loopfunc:true */
        sfs = _slice.call(sense.querySelectorAll(
            domutil.toGUISelector("btw:citations btw:sf, "+
                                  "btw:other-citations btw:sf")))
                .filter(function (x) {
                return !contrastive.contains(x);
            });

        var sense_sfss = this.makeElement("btw:semantic-fields");
        this.combineSemanticFieldsInto(sfs, sense_sfss);
        sense.insertBefore(sense_sfss, contrastive || null);
    }


    // Create the "all semantic fields" section from the semantic
    // fields of each sense.
    var all_sfs = this.makeElement("btw:semantic-fields");
    sfs = root.querySelectorAll(domutil.toGUISelector(
        "btw:sense>btw:semantic-fields>btw:sf"));
    this.combineSemanticFieldsInto(sfs, all_sfs, 3);
    var overview = root.getElementsByClassName("btw:overview")[0];
    overview.appendChild(all_sfs);


    // Transform English renditions to the viewing format.
    var english_renditions =
            root.getElementsByClassName("btw:english-renditions");
    var ers_el; // English renditions element
    for (i = 0; (ers_el = english_renditions[i]) !== undefined; ++i) {
        var first_er = domutil.childByClass(ers_el, "btw:english-rendition");
        //
        // Make a list of btw:english-terms that will appear at the
        // start of the btw:english-renditions.
        //

        // Slicing it prevents this list from growing as we add the clones.
        terms = _slice.call(ers_el.getElementsByClassName("btw:english-term"));
        div = doc.createElement("div");
        div.classList.add("btw:english-term-list");
        div.classList.add("_real");
        for (t_ix = 0, term; (term = terms[t_ix]) !== undefined; ++t_ix) {
            clone = term.cloneNode(true);
            clone.classList.add("_inline");
            div.appendChild(clone);
            if (t_ix < terms.length - 1)
                div.appendChild(doc.createTextNode(", "));
        }
        ers_el.insertBefore(div, first_er);

        //
        // Combine the contents of all btw:english-rendition into one
        // btw:semantic-fields element
        //
        // Slicing to prevent changes to the list as we remove elements.
        var ers = _slice.call(
            ers_el.getElementsByClassName("btw:english-rendition"));
        html = [];
        for (var e_ix = 0, er; (er = ers[e_ix]) !== undefined; ++e_ix) {
            html.push(er.innerHTML);
            er.parentNode.removeChild(er);
        }
        sfs = doc.createElement("div");
        sfs.classList.add("btw:semantic-fields-collection");
        sfs.classList.add("_real");
        sfs.innerHTML = html.join("");
        ers_el.appendChild(sfs);
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
    gui_updater.addEventListener("insertNodeAt", function (ev) {
        domutil.linkTrees(ev.node, ev.node);
    });

    //
    // In btw_decorator, there are triggers that refresh hyperlinks as
    // elements are added or processed. Such triggers do not exist
    // here so id decorations need to be performed before anything
    // else is done so that when hyperlinks are decorated, everthing
    // is available for them to be decorated.
    var with_ids = root.querySelectorAll("[" + util.encodeAttrName("xml:id") +
                                         "]");
    var with_id;
    for(i = 0; (with_id = with_ids[i]) !== undefined; ++i)
        this.idDecorator(root, with_id);

    // We want to process all ref elements earlier so that hyperlinks
    // to examples are created properly.
    var refs = root.getElementsByClassName("ref");
    var ref;
    for (i = 0; (ref = refs[i]); ++i)
        this.process(root, ref);

    this.process(root, root.firstElementChild);

    this._setCondition("done", this);

    function showTarget() {
        var hash = win.location.hash;
        if (!hash)
            return;

        var target = doc.getElementById(hash.slice(1));
        if (!target)
            return;

        var parents = [];
        var parent = closest(target, ".collapse:not(.in)");
        while (parent) {
            parents.unshift(parent);
            parent = parent.parentNode;
            parent = parent && closest(parent, ".collapse:not(.in)");
        }

        function next(parent) {
            var $parent = $(parent);
            $parent.one('shown.bs.collapse', function () {
                if (parents.length) {
                    next(parents.shift());
                    return;
                }
                // We get here only once all sections have been expanded.
                target.scrollIntoView(true);
            });
            $parent.collapse('show');
        }
        next(parents.shift());
    }
    win.addEventListener('popstate', showTarget);
    // This also catches hitting the Enter key on a link.
    $(root).on('click', 'a[href]:not([data-toggle], [href="#"])',
               function (ev) {
        setTimeout(showTarget, 0);
    });
    showTarget();
}

oop.implement(Viewer, DispatchMixin);
oop.implement(Viewer, SimpleEventEmitter);
oop.implement(Viewer, Conditioned);

Viewer.prototype.process = function (root, el) {
    this.dispatch(root, el);
    el.classList.remove("_phantom");

    // Process the children...
    var children = el.children;
    for(var i = 0, limit = children.length; i < limit; ++i)
        this.process(root, children[i]);
};

Viewer.prototype.listDecorator = function (el, sep) {
    // If sep is a string, create an appropriate div.
    var sep_node;
    if (typeof sep === "string") {
        sep_node = el.ownerDocument.createTextNode(sep);
    }
    else
        sep_node = sep;

    var first = true;
    var child = el.firstElementChild;
    while(child) {
        if (child.classList.contains("_real")) {
            if (!first)
                this._gui_updater.insertBefore(el, sep_node.cloneNode(true),
                                               child);
            else
                first = false;
        }
        child = child.nextElementSibling;
    }
};

Viewer.prototype.languageDecorator = function () {
};

Viewer.prototype.noneDecorator = function () {
};

Viewer.prototype.elementDecorator = function () {
};

Viewer.prototype._transformContrastiveItems = function(root, name) {
    // A "group" here is an element that combines a bunch of elements
    // of the same kind: btw:antonyms is a group of btw:antonym,
    // btw:cognates is a group of btw:cognates, etc. The elements of
    // the same kind are called "items" later in this code.

    var group_class = "btw:" + name + "s";
    var doc = root.ownerDocument;
    // groups are those elements that act as containers (btw:cognates,
    // btw:antonyms, etc.)
    var groups = _slice.call(root.getElementsByClassName(group_class));
    for(var i = 0, group; (group = groups[i]) !== undefined; ++i) {
        if (group.getElementsByClassName("btw:none").length) {
            // The group is empty. Remove the group and move on.
            group.parentNode.removeChild(group);
            continue;
        }

        // This div will contain the list of all terms in the group.
        var div = doc.createElement("div");
        div.classList.add("btw:" + name + "-term-list");
        div.classList.add("_real");

        // Slicing it prevents this list from growing as we add the clones.
        var terms = _slice.call(group.getElementsByClassName("btw:term"));

        // A wrapper is the element that wraps around the term. This
        // loop: 1) adds each wrapper to the .btw:...-term-list. and
        // b) replaces each term with a clone of the wrapper.
        var wrappers = [];
        for (var t_ix = 0, term; (term = terms[t_ix]) !== undefined; ++t_ix) {
            var clone = term.cloneNode(true);
            clone.classList.add("_inline");
            var wrapper = doc.createElement("div");
            wrapper.classList.add("btw:" + name + "-term-item");
            wrapper.classList.add("_real");
            wrapper.textContent = name.replace("-", " ") + " " +
                (t_ix + 1) + ": ";
            wrapper.appendChild(clone);
            div.appendChild(wrapper);

            var parent = term.parentNode;

            // This effectively replaces the term element in
            // btw:antonym, btw:cognate, etc. with an element that
            // contains the "name i: " prefix.
            parent.insertBefore(wrapper.cloneNode(true), term);
            parent.removeChild(term);
            wrappers.push(wrapper);
        }
        group.insertBefore(div, group.querySelector(".btw\\:" + name));

        //
        // Combine the contents of all of the items into one
        // btw:citations element
        //
        // Slicing to prevent changes to the list as we remove elements.
        var items = _slice.call(group.getElementsByClassName("btw:" + name));
        var html = [];
        for (var a_ix = 0, item; (item = items[a_ix]) !== undefined; ++a_ix) {
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
        // If there are btw:sematic-fields elements, combine them. But
        // only for cognates.
        //
        if (name === "cognate") {
            var cits = coll.getElementsByClassName("btw:citations");
            for (var cit_ix = 0, cit; (cit = cits[cit_ix]); ++cit_ix) {
                var sfs = cit.getElementsByClassName("btw:sf");
                var sfss = this.makeElement("btw:semantic-fields");
                var wrapper = wrappers[cit_ix];
                wrapper.parentNode.insertBefore(sfss, wrapper.nextSibling);
                this.combineSemanticFieldsInto(sfs, sfss);
            }
        }
    }
};

Viewer.prototype.fetchAndFillBiblData = function (target_id, el, abbr) {
    var data = this._bibl_data[target_id];
    if (!data)
        throw new Error("missing bibliographical data");
    this.fillBiblData(el, abbr, data);
};

Viewer.prototype.refDecorator = function (root, el) {
    var orig_target = el.getAttribute(util.encodeAttrName("target"));
    if (!orig_target)
        orig_target = "";

    orig_target = orig_target.trim();

    var bibl_prefix = "/bibliography/";
    if (orig_target.lastIndexOf(bibl_prefix, 0) === 0) {
        // We want to remove any possible a element before we give control
        // to the overriden function.
        var a = domutil.childByClass(el, 'a');
        var child;
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
        var target_id = orig_target;

        var data = this._bibl_data[target_id];
        if (!data)
            throw new Error("missing bibliographical data");

        // We also want a hyperlink into the Zotero library.
        a = el.ownerDocument.createElement("a");
        a.className = "a _phantom_wrap";
        a.href = data.zotero_url;
        a.setAttribute("target", "_blank");
        child = el.firstChild;
        el.appendChild(a);
        while (child && child !== a) {
            a.appendChild(child);
            child = el.firstChild;
        }
    }
    else
        DispatchMixin.prototype.refDecorator.call(this, root, el);
};

Viewer.prototype.makeElement = function (name, attrs) {
    var ename = this._resolver.resolveName(name);
    var e = transformation.makeElement(this._data_doc, ename.ns, name, attrs);
    return convert.toHTMLTree(this._doc, e);
};

Viewer.prototype.combineSemanticFieldsInto = function (sfs, into, depth) {
    var texts = [];
    for (var sfs_ix = 0, sf; (sf = sfs[sfs_ix]); ++sfs_ix)
        texts.push(sf.textContent.trim());

    var combined = btw_semantic_fields.combineSemanticFields(texts, depth);
    for (var ix = 0, text; (text = combined[ix]); ++ix) {
        sf = this.makeElement("btw:sf");
        sf.textContent = text;
        into.appendChild(sf);
    }
};

return Viewer;

});
