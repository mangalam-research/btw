/**
 * @module wed/modes/btw/btw_dispatch
 * @desc The dispatch logic common to editing and displaying articles.
 * @author Louis-Dominique Dubeau
 */
define(function (require, exports, module) {
'use strict';

var util = require("wed/util");
var $ = require("jquery");
var tooltip = require("wed/gui/tooltip").tooltip;
var jqutil = require("wed/jqutil");


function DispatchMixin() {
}

DispatchMixin.prototype.dispatch = function (root, el) {
    var klass = this._meta.getAdditionalClasses(el);
    if (klass.length)
        el.className += " " + klass;

    var name = util.getOriginalName(el);
    var skip_default = false;
    switch(name) {
    case "btw:overview":
    case "btw:sense-discrimination":
    case "btw:historico-semantical-data":
        this._heading_decorator.unitHeadingDecorator(el);
        break;
    case "btw:definition":
    case "btw:english-renditions":
    case "btw:english-rendition":
    case "btw:etymology":
    case "btw:contrastive-section":
    case "btw:antonyms":
    case "btw:cognates":
    case "btw:conceptual-proximates":
    case "btw:other-citations":
    case "btw:citations":
        this._heading_decorator.sectionHeadingDecorator(el);
        break;
    case "btw:semantic-fields":
        this._heading_decorator.sectionHeadingDecorator(el);
        this.listDecorator(el, "; ");
        break;
    case "ptr":
        this.ptrDecorator(root, el);
        break;
    case "foreign":
        this.languageDecorator(el);
        break;
    case "ref":
        this.refDecorator(root, el);
        break;
    case "btw:example":
        this.idDecorator(root, el);
        break;
    case "btw:cit":
        this.citDecorator(root, el);
        skip_default = true; // citDecorator calls elementDecorator
        break;
    case "btw:explanation":
        this.explanationDecorator(root, el);
        skip_default = true; // explanationDecorator calls elementDecorator
        break;
    case "btw:none":
        this.noneDecorator(root, el);
        // THIS ELEMENT DOES NOT GET THE REGULAR DECORATION.
        skip_default = true;
        break;
    }

    if (!skip_default)
        this.elementDecorator(root, el);
};

DispatchMixin.prototype._getIDManagerForRefman = function (refman) {
    switch(refman.name) {
    case "sense":
    case "subsense":
        return this._sense_subsense_id_manager;
    case "example":
        return this._example_id_manager;
    default:
        throw new Error("unexpected name: " + refman.name);
    }
};

DispatchMixin.prototype.idDecorator = function (root, el) {
    var name = util.getOriginalName(el);

    var refman = this._refmans.getRefmanForElement(el);
    if (refman) {
        var wed_id = el.id;
        if (!wed_id) {
            var id = el.getAttribute(util.encodeAttrName("xml:id"));
            var id_man = this._getIDManagerForRefman(refman);
            wed_id = "BTW-" + (id || id_man.generate());
            el.id = wed_id;
        }

        // We have some reference managers that don't derive from
        // ReferenceManager and thus do not have this method.
        if (refman.allocateLabel)
            refman.allocateLabel(wed_id);
    }
};

var WHEEL = "☸";

DispatchMixin.prototype.explanationDecorator = function (root, el) {
    var child, next, div; // Damn hoisting...
    // Handle explanations that are in btw:example-explained.
    if (el.parentNode.classList.contains("btw:example-explained")) {
        child = el.firstElementChild;
        while(child) {
            next = child.nextElementSibling;
            if (child.classList.contains("_explanation_bullet")) {
                this._gui_updater.removeNode(child);
                break; // There's only one.
            }
            child = next;
        }

        var cit = el.nextElementSibling;
        // If the next btw:cit element contains Pāli text.
        if (cit.classList.contains("btw:cit") &&
            cit.querySelector("*[" + util.encodeAttrName("xml:lang") +
                              "='pi-Latn']")) {
            div = el.ownerDocument.createElement("div");
            div.className = "_phantom _decoration_text _explanation_bullet";
            div.style.position = "absolute";
            div.style.left = "-1em";
            div.textContent = WHEEL;
            this._gui_updater.insertNodeAt(el, 0, div);
            el.style.position = "relative";
        }
        this.elementDecorator(root, el);
        return;
    }

    this.elementDecorator(root, el);
    var label;
    var parent = el.parentNode;
    // Is it in a subsense?
    if (parent.classList.contains("btw:subsense")) {
        var refman = this._refmans.getSubsenseRefman(el);
        label = refman.idToSublabel(parent.id);
        child = el.firstElementChild;
        var start;
        while(child) {
            next = child.nextElementSibling;
            if (child.classList.contains("_explanation_number"))
                this._gui_updater.removeNode(child);
            else if (child.classList.contains("__start_label"))
                start = child;
            child = next;
        }

        // We want to insert it after the start label.
        div = el.ownerDocument.createElement("div");
        div.className = "_phantom _decoration_text _explanation_number " +
            "_start_wrapper'";
        div.textContent = label + ". ";
        this._gui_updater.insertBefore(el, div,
                                       start ? start.nextSibling : el.firstChild);

    }
    this._heading_decorator.sectionHeadingDecorator(el);
};

DispatchMixin.prototype.citDecorator = function (root, el) {
    this.elementDecorator(root, el);

    var ref;
    var child = el.firstElementChild;
    while(child) {
        var next = child.nextElementSibling;
        if (child.classList.contains("_ref_space") ||
            child.classList.contains("_cit_bullet"))
            this._gui_updater.removeNode(child);
        else if (child.classList.contains("ref"))
            ref = child;
        child = next;
    }

    if (ref) {
        var space = el.ownerDocument.createElement("div");
        space.className = "_text _phantom _ref_space";
        space.innerHTML = " ";
        el.insertBefore(space, ref.nextSibling);
    }

    if (el.querySelector("*[" + util.encodeAttrName("xml:lang") +
                 "='pi-Latn']")) {
        var div = el.ownerDocument.createElement("div");
        div.className = "_phantom _text _cit_bullet";
        div.style.position = "absolute";
        div.style.left = "-1em";
        div.textContent = WHEEL;
        this._gui_updater.insertNodeAt(el, 0, div);
        el.style.position = "relative";
    }
};

DispatchMixin.prototype.ptrDecorator = function (root, el) {
    this.linkingDecorator(root, el, true);
};

DispatchMixin.prototype.refDecorator = function (root, el) {
    this.linkingDecorator(root, el, false);
};

function setTitle($el, data) {
    var creators = data.creators;
    var first_creator = "***ITEM HAS NO CREATORS***";
    if (creators)
        first_creator = creators.split(",")[0];

    var title = first_creator + ", " + data.title;
    var date = data.date;
    if (date)
        title += ", " + date;

    tooltip($el, {"title": title, container: "body"});
}

DispatchMixin.prototype.linkingDecorator = function (root, el, is_ptr) {
    var orig_target = el.getAttribute(util.encodeAttrName("target"));
    // XXX This should become an error one day. The only reason we
    // need this now is that some of the early test files had <ref>
    // elements without targets.
    if (!orig_target)
        orig_target = "";

    orig_target = orig_target.trim();

    var doc = root.ownerDocument;
    var target_id, child, next; // Damn hoisting.
    if (orig_target.lastIndexOf("#", 0) === 0) {
        // Internal target
        // Add BTW in front because we want the target used by wed.
        target_id = orig_target.replace(/#(.*)$/,'#BTW-$1');

        var text = doc.createElement("div");
        text.className = "_text _phantom _linking_deco";
        var a = doc.createElement("a");
        a.className = "_phantom";
        a.setAttribute("href", target_id);
        text.appendChild(a);
        if (is_ptr) {
            // _linking_deco is used locally to make this function idempotent

            child = el.firstElementChild;
            while(child) {
                next = child.nextElementSibling;
                if (child.classList.contains("_linking_deco")) {
                    this._gui_updater.removeNode(child);
                    break; // There is only one.
                }
                child = next;
            }

            var refman = this._refmans.getRefmanForElement(el);

            // Find the referred element. Slice to drop the #.
            var target = doc.getElementById(target_id.slice(1));

            // An undefined or null refman can happen when first
            // decorating the document.
            var label;
            if (refman) {
                if (refman.name === "sense" || refman.name === "subsense") {
                    label = refman.idToLabel(target_id.slice(1));
                    label = label && "[" + label + "]";
                }
                else {
                    // An empty target can happen when first
                    // decorating the document.
                    if (target) {
                        var data_el = this._editor.toDataNode(el);
                        var data_target = this._editor.toDataNode(target);
                        label = refman.getPositionalLabel(data_el,
                                                          data_target,
                                                          target_id.slice(1));
                    }
                }
            }

            if (label === undefined)
                label = target_id;

            a.textContent = label;

            // A ptr contains only attributes, no text, so we can just append.
            var pair = this._mode.nodesAroundEditableContents(el);
            this._gui_updater.insertBefore(el, text, pair[1]);

            if (target) {
                var target_name = util.getOriginalName(target);

                // Reduce the target to something sensible for tooltip text.
                if (target_name === "btw:sense")
                    target = target.querySelector(jqutil.toDataSelector(
                        "btw:english-rendition>btw:english-term"));
                else if (target_name === "btw:subsense") {
                    child = target.firstElementChild;
                    while(child) {
                        if (child.classList.contains("btw:explanation")) {
                            target = child;
                            break;
                        }
                        child = child.nextElementSibling;
                    }
                }
                else if (target_name === "btw:example")
                    target = undefined;

                if (target) {
                    target = target.cloneNode(true);
                    var nodes = target.querySelectorAll(
                        ".head, ._gui, ._explanation_number");
                    for (var node_ix = 0, node;
                         (node = nodes[node_ix]) !== undefined; ++node_ix)
                        node.parentNode.removeChild(node);
                    tooltip($(text), {"title":
                                      "<div>" + target.innerHTML + "</div>",
                                      "html": true, "container": "body"});
                }
            }
        }
        else
            throw new Error("internal error: ref with unexpected target");
    }
    else {
        // External target
        var bibl_prefix = "/bibliography/";
        if (orig_target.lastIndexOf(bibl_prefix, 0) === 0) {
            // Bibliographical reference...
            if (is_ptr)
                throw new Error("internal error: bibliographic "+
                                "reference recorded as ptr");

            target_id = orig_target;

            // It is okay to skip the tree updater for these operations.
            child = el.firstElementChild;
            while(child) {
                next = child.nextElementSibling;
                if (child.classList.contains("_ref_abbr") ||
                    child.classList.contains("_ref_paren"))
                    this._gui_updater.removeNode(child);
                child = next;
            }

            var abbr = doc.createElement("div");
            abbr.className = "_text _phantom _ref_abbr";
            this._gui_updater.insertBefore(el, abbr, el.firstChild);
            var open = doc.createElement("div");
            open.className = "_phantom _decoration_text _ref_paren " +
                "_open_ref_paren _start_wrapper";
            open.innerHTML = "(";
            this._gui_updater.insertBefore(el, open, abbr);

            var close = doc.createElement("div");
            close.className = "_phantom _decoration_text " +
                      "_ref_paren _close_ref_paren _end_wrapper";
            close.innerHTML = ")";
            this._gui_updater.insertBefore(el, close);

            var dec = this;
            var $el = $(el);
            $.ajax({
                url: target_id,
                headers: {
                    Accept: "application/json"
                }
            }).done(function (data) {
                var text = "";

                if (data.reference_title) {
                    text = data.reference_title;
                    setTitle($el, data.item);
                }
                else {
                    var creators = data.creators;
                    text = "***ITEM HAS NO CREATORS***";
                    if (creators)
                        text = creators.split(",")[0];

                    if (data.date)
                        text += ", " + data.date;
                    setTitle($el, data);
                }


                dec._gui_updater.insertText(abbr, 0, text);
                $el.trigger("wed-refresh");

            }).fail(function () {
                dec._gui_updater.insertText(abbr, 0, "NON-EXISTENT");
                $el.trigger("wed-refresh");
            });
        }
    }
};

exports.DispatchMixin = DispatchMixin;

});
