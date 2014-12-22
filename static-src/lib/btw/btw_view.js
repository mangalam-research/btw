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
var btw_util = require("./btw_util");

var _slice = Array.prototype.slice;
var _indexOf = Array.prototype.indexOf;
var closest = domutil.closest;

/**
 * @param {Element} root The element of ``wed-document`` class that is
 * meant to hold the viewed document.
 * @param {string} data The document, as XML.
 * @param {string} bibl_data The bibliographical data. This is a
 * mapping of targets (i.e. the targets given to the ``ref`` tags that
 * point to bibliographical items) to dictionaries that contain the
 * same values those returned as when asking the server to resolve
 * these targets individually. This mapping must be
 * complete. Otherwise, it is an internal error.
 */
function Viewer(root, data, bibl_data) {
    SimpleEventEmitter.call(this);
    Conditioned.call(this);
    var doc = root.ownerDocument;
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
        "btw:overview": "OVERVIEW",
        "btw:sense-discrimination": "SENSE DISCRIMINATION",
        "btw:historico-semantical-data": "HISTORICO-SEMANTICAL DATA"
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
         heading: "semantic fields",
         collapse: {
             kind: "default",
             additional_classes: "sf-collapse"
         }
        });
    this._heading_decorator.addSpec(
        {selector: "btw:overview>btw:semantic-fields",
         heading: "all semantic fields"});
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
        // We get all semantic-fields elements that are outside the
        // contrastive section.
        /* jshint loopfunc:true */
        var sfss = _slice.call(sense.querySelectorAll(
            domutil.toGUISelector("btw:example btw:semantic-fields")))
                .filter(function (x) {
                return !contrastive.contains(x);
            });
        var sense_sfss = this.makeElement("btw:semantic-fields");
        // sfs is already defined
        for (var sfss_ix = 0; (sfs = sfss[sfss_ix]); ++sfss_ix) {
            clone = sfs.cloneNode(true);
            while (clone.firstElementChild)
                sense_sfss.appendChild(clone.firstElementChild);
        }
        sense.insertBefore(sense_sfss, contrastive);
    }


    // Create the "all semantic fields" section from the semantic
    // fields of each sense.
    var all_sfs = this.makeElement("btw:semantic-fields");
    for(i = 0, sense; (sense = senses[i]) !== undefined; ++i) {
        var sense_ssfs = domutil.childByClass(sense, "btw:semantic-fields");
        clone = sense_ssfs.cloneNode(true);
        while (clone.firstElementChild)
            all_sfs.appendChild(clone.firstElementChild);
    }
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

    // Create part 2, which does not exist as such in the file we store.
    this.createPartTwo(root);
    this._setCondition("done", this);
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
        var coll = doc.createElement("div");
        coll.classList.add("btw:citations-collection");
        coll.classList.add("_real");
        coll.innerHTML = html.join("");
        group.appendChild(coll);

        //
        // If there are btw:sematic-fields elements, combine them. But
        // only for cognates.
        //
        if (name === "cognate") {
            var cits = coll.getElementsByClassName("btw:citations");
            for (var cit_ix = 0, cit; (cit = cits[cit_ix]); ++cit_ix) {
                var secats = cit.getElementsByClassName("btw:semantic-fields");
                if (secats.length) {
                    secats = _slice.call(secats);
                    html = [];
                    for(var sc_ix = 0, secat; (secat = secats[sc_ix]);
                        ++sc_ix) {
                        html.push(secat.outerHTML);
                    }

                    var sfs = doc.createElement("div");
                    sfs.classList.add("btw:semantic-fields-collection");
                    sfs.classList.add("_real");
                    sfs.innerHTML = html.join("");
                    var wrapper = wrappers[cit_ix];
                    wrapper.parentNode.insertBefore(sfs, wrapper.nextSibling);
                    this._heading_decorator.sectionHeadingDecorator(sfs);
                }
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

Viewer.prototype.makeElement = function (name, attrs) {
    var ename = this._resolver.resolveName(name);
    var e = transformation.makeElement(this._data_doc, ename.ns, name, attrs);
    return convert.toHTMLTree(this._doc, e);
};

/**
 * Recursively removes all ids from an element and its children.
 *
 * @private
 * @param {Element} el The element to process.
 * @returns {Element} The value of ``el``.
 */
function cleanIDs(el) {
    el.id = null;
    if (!el.children)
        return el;

    var child = el.firstElementChild;
    while (child) {
        cleanIDs(child);
        child = child.nextElementSibling;
    }

    return el;
}

/**
 * Prepare all citations in an element for inclusion in Part 2 of an
 * article.
 *
 * @private
 *
 * @param {Element} el The element from part 1.
 * @param {Element} p2_el The element that we are currently populating
 * in part 2. This element is modified by this method.
 * @param {string} which Which of "btw:citations" or
 * "btw:other-citations" we are processing.
 */
function prepareCitations(el, p2_el, which) {
    var doc = el.ownerDocument;
    var citations = domutil.childByClass(el, which);
    if (citations) {
        var p2_citations = citations.cloneNode(true);

        // Drop the head, as it is useless here.
        var head = domutil.childByClass(p2_citations, "head");
        if (head)
            p2_citations.removeChild(head);

        // Replace links to examples with the actual example.
        var ptrs = domutil.childrenByClass(p2_citations, "ptr");
        var i, ptr;
        for (i = 0; (ptr = ptrs[i]); ++i) {
            var a = ptr.getElementsByTagName("a")[0];
            var target = doc.getElementById(a.attributes.href.value.slice(1));
            if (!target)
                throw new Error("can't get target for " +
                                a.attributes.href.value);
            var p2_target = cleanIDs(target.cloneNode(true));
            p2_citations.insertBefore(p2_target, ptr);
            p2_citations.removeChild(ptr);
        }

        cleanIDs(p2_citations);
        p2_el.appendChild(p2_citations);
    }
}

function prepareExplanation(explanation, force_real) {
    var p2_explanation;
    if (explanation) {
        p2_explanation = cleanIDs(explanation.cloneNode(true));
        var head = domutil.childByClass(p2_explanation, "head");
        if (head)
            p2_explanation.removeChild(head);
        var number = domutil.childByClass(p2_explanation,
                                          "_explanation_number");
        if (number)
            p2_explanation.removeChild(number);
    }
    else if (!force_real)
        // Fake object so that the followig code does not have
        // to worry about a missing explanation.
        p2_explanation = {innerHTML: ""};

    return p2_explanation;
}


Viewer.prototype.createPartTwo = function (root) {
    var part_two = this.makeElement("part-two");
    var head = this.makeElement("head");
    head.innerHTML = "Part Two<br/>All Citations Ordered by Sense";
    part_two.appendChild(head);

    var senses = root.getElementsByClassName("btw:sense");
    var i, sense;
    for (i = 0; (sense = senses[i]); ++i) {
        var p2_sense = this.makeElement("sense");
        head = domutil.childByClass(sense, "head");
        p2_sense.appendChild(cleanIDs(head.cloneNode(true)));

        var subsenses = sense.getElementsByClassName("btw:subsense");
        var j, subsense, explanation, p2_explanation;
        for (j = 0; (subsense = subsenses[j]); ++j) {
            var p2_subsense = this.makeElement("subsense");
            explanation = domutil.childByClass(subsense, "btw:explanation");
            p2_explanation = prepareExplanation(explanation);

            var refman = this._refmans.getSubsenseRefman(subsense);
            var label = refman.idToLabel(subsense.id);

            head = this.makeElement("head");
            head.innerHTML = label + " " + p2_explanation.innerHTML;
            p2_subsense.appendChild(head);

            prepareCitations(subsense, p2_subsense, "btw:citations");
            prepareCitations(subsense, p2_subsense, "btw:other-citations");

            p2_sense.appendChild(p2_subsense);
        }

        explanation = domutil.childByClass(sense, "btw:explanation");
        p2_explanation = prepareExplanation(explanation, true);
        if (p2_explanation)
            p2_sense.appendChild(p2_explanation);

        prepareCitations(sense, p2_sense, "btw:citations");
        prepareCitations(sense, p2_sense, "btw:other-citations");

        var contrastive =
                domutil.childByClass(sense, "btw:contrastive-section");

        if (contrastive) {
            var p2_contrastive = this.makeElement("contrastive-section");
            head = this.makeElement("head");
            head.textContent = "[contrastive section]";
            p2_contrastive.appendChild(head);

            // btw:citations-collection is an element we have created
            // when generating the view structure for part 1.
            var cols = contrastive.querySelectorAll(
                domutil.toGUISelector("btw:citations-collection"));
            for (var col_ix = 0, col; (col = cols[col_ix]); ++col_ix) {
                var kind = col.parentNode.classList[0].slice(4, -1);
                var p2_term = this.makeElement("term");
                var term = col.querySelector(domutil.toGUISelector(
                    "btw:" + kind + "-term-item btw:term"));
                head = this.makeElement("head");
                head.innerHTML =
                    "[contrast with " + kind + " " + term.outerHTML + "]";
                p2_term.appendChild(head);
                prepareCitations(col, p2_term, "btw:citations");
                p2_contrastive.appendChild(p2_term);
            }

            p2_sense.appendChild(p2_contrastive);
        }

        part_two.appendChild(p2_sense);
    }

    var collapse_heading_id_manager =
        new id_manager.IDManager("part2-collapse-heading-");
    var collapse_id_manager =
        new id_manager.IDManager("part2-collapse-");


    // Update all the collapsible sections to use new IDs.
    var collapsibles = part_two.getElementsByClassName("panel-group");
    var collapsible;
    for (i = 0, collapsible; (collapsible = collapsibles[i]); ++i)
        btw_util.updateCollapsible(
            collapsible, collapse_heading_id_manager.generate(),
            collapse_id_manager.generate());

    this._gui_updater.insertBefore(root.firstElementChild, part_two);

    // Add tooltips to the references. We must do this after part two
    // has been added because linkingDecorator depends on the nodes
    // being in the tree.
    var refs = part_two.getElementsByClassName("ref");
    var ref;
    for (i = 0; (ref = refs[i]); ++i)
        this.process(root, ref);

};


return Viewer;

});
