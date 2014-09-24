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
var btw_meta = require("./btw_meta");
var HeadingDecorator = require("./btw_heading_decorator").HeadingDecorator;
var btw_refmans = require("./btw_refmans");
var DispatchMixin = require("./btw_dispatch").DispatchMixin;
var id_manager = require("./id_manager");
var $ = require("jquery");

var _slice = Array.prototype.slice;
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
    var doc = root.ownerDocument;
    var parser = new doc.defaultView.DOMParser();
    var data_doc = parser.parseFromString(data, "text/xml");
    root.appendChild(convert.toHTMLTree(doc, data_doc.firstChild));

    var gui_updater = new TreeUpdater(root);

    this._gui_updater = gui_updater;
    this._refmans = new btw_refmans.WholeDocumentManager();
    this._meta = new btw_meta.Meta();
    this._bibl_data = bibl_data;

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

    // Override the head specs with those required for
    // viewing.
    this._heading_decorator = new HeadingDecorator(this._refmans, gui_updater);
    this._heading_decorator.addSpec({selector: "btw:english-rendition",
                                     heading: null});
    this._heading_decorator.addSpec({selector: "btw:semantic-fields",
                                     heading: null});
    this._heading_decorator.addSpec(
        {selector: "btw:english-renditions>btw:semantic-fields-collection",
         heading: "semantic categories of possible English renditions"});
    this._heading_decorator.addSpec(
        {selector: "btw:cognates>btw:semantic-fields-collection",
         heading: "semantic categories of cognates related to sense",
         label_f: this._heading_decorator._bound_getSenseLabel});
    this._heading_decorator.addSpec(
        {selector: "btw:semantic-fields-collection>btw:semantic-fields",
         heading: null});
    this._heading_decorator.addSpec(
        {selector: "btw:sense>btw:semantic-fields",
         heading: "semantic categories for sense",
         label_f: this._heading_decorator._bound_getSenseLabel});
    this._heading_decorator.addSpec({selector: "btw:semantic-fields",
                                     heading: "semantic categories"});
    this._heading_decorator.addSpec({
        selector: "btw:antonyms>btw:citations-collection",
        heading: "citations for antonyms related to sense",
        label_f: this._heading_decorator._bound_getSenseLabel
    });
    this._heading_decorator.addSpec({
        selector: "btw:cognates>btw:citations-collection",
        heading: "citations for cognates related to sense",
        label_f: this._heading_decorator._bound_getSenseLabel
    });
    this._heading_decorator.addSpec({
        selector: "btw:conceptual-proximates>btw:citations-collection",
        heading: "citations for conceptual-proximates related to sense",
        label_f: this._heading_decorator._bound_getSenseLabel
    });
    this._heading_decorator.addSpec({
        selector: "btw:antonym>btw:citations",
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

    // Transform English renditions to the viewing format.
    var english_renditions = root.getElementsByClassName("btw:english-renditions");
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

    new dloc.DLocRoot(root);

    // We want to process all ref elements earlier so that hyperlinks
    // to examples are created properly.
    var refs = root.getElementsByClassName("ref");
    var ref;
    for (i = 0; (ref = refs[i]); ++i)
        this.process(root, ref);

    this.process(root, root.firstElementChild);

    // Create part 2, which does not exist as such in the file we store.
    this.createPartTwo(root);
}

oop.implement(Viewer, DispatchMixin);

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
        var wrappers = [];
        for (var t_ix = 0, term; (term = terms[t_ix]) !== undefined; ++t_ix) {
            var clone = term.cloneNode(true);
            clone.classList.add("_inline");
            var wrapper = doc.createElement("div");
            wrapper.classList.add("btw:" + name + "-term-item");
            wrapper.classList.add("_real");
            wrapper.textContent = name + " " + (t_ix + 1) + ": ";
            wrapper.appendChild(clone);
            div.appendChild(wrapper);

            var parent = term.parentNode;

            // This effectively replaces the term with an element that
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
            html.push(item.innerHTML);
            item.parentNode.removeChild(item);
        }
        var coll = doc.createElement("div");
        coll.classList.add("btw:citations-collection");
        coll.classList.add("_real");
        coll.innerHTML = html.join("");
        group.appendChild(coll);
        this._heading_decorator.sectionHeadingDecorator(coll);

        //
        // If there are btw:sematic-fields elements, combine them.
        //
        var secats = group.getElementsByClassName("btw:semantic-fields");
        if (secats.length) {
            secats = _slice.call(secats);
            html = [];
            for(var sc_ix = 0, secat; (secat = secats[sc_ix]) !== undefined;
                ++sc_ix) {
                html.push(wrappers[sc_ix].outerHTML);
                html.push(secat.outerHTML);
                secat.parentNode.removeChild(secat);
            }
            var sfs = doc.createElement("div");
            sfs.classList.add("btw:semantic-fields-collection");
            sfs.classList.add("_real");
            sfs.innerHTML = html.join("");
            group.appendChild(sfs);
            this._heading_decorator.sectionHeadingDecorator(sfs);
        }
    }
};

/**
 * This function works exactly like the one in {@link
 * module:btw_dispatch~DispatchMixin DispatchMixin} except that it
 * takes the additional ``final_`` parameter.
 *
 * @param {boolean} final_ Whether there will be any more changes to
 * this ptr or not.
 */
Viewer.prototype.linkingDecorator = function (root, el, is_ptr, final_) {
    DispatchMixin.prototype.linkingDecorator.call(this, root, el, is_ptr);

    // What we are doing here is taking care of updating links to
    // examples when the reference to the bibliographical source they
    // contain is updated. These updates happen asynchronously.
    if (is_ptr && !final_) {
        var doc = el.ownerDocument;
        var orig_target = el.getAttribute(util.encodeAttrName("target"));
        if (!orig_target)
            orig_target = "";

        orig_target = orig_target.trim();

        if (orig_target.lastIndexOf("#", 0) !== 0)
            return;

        // Internal target
        // Add BTW in front because we want the target used by wed.
        var target_id = orig_target.replace(/#(.*)$/,'#BTW-$1');

        // Find the referred element. Slice to drop the #.
        var target = doc.getElementById(target_id.slice(1));

        if (!(target.classList.contains("btw:example") ||
              target.classList.contains("btw:example-explained")))
            return;

        // Get the ref element that olds the reference to the
        // bibliographical item, and set an event handler to make sure
        // we update *this* ptr, when the ref changes.
        var ref =
                target.querySelector(domutil.toGUISelector("btw:cit>ref"));

        $(ref).on("wed-refresh", function () {
            this.linkingDecorator(root, el, is_ptr);
        }.bind(this));
    }
};

DispatchMixin.prototype.fetchAndFillBiblData = function (target_id, el, abbr) {
    var data = this._bibl_data[target_id];
    if (!data)
        throw new Error("missing bibliographical data");
    this.fillBiblData(el, abbr, data);
};


Viewer.prototype.createPartTwo = function (root) {
};


return Viewer;

});
