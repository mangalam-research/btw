define(function (require, exports, module) {
'use strict';

var oop = require("wed/oop");
var ReferenceManager = require("wed/refman").ReferenceManager;
var $ = require("jquery");
var util = require("wed/util");
var domutil = require("wed/domutil");
var id_manager = require("./id_manager");

var sense_labels = 'abcdefghijklmnopqrstuvwxyz';
function SenseReferenceManager() {
    ReferenceManager.call(this, "sense");
    this._subsense_reference_managers = {};
    this._next_sense_label_ix = 0;
}

oop.inherit(SenseReferenceManager, ReferenceManager);

SenseReferenceManager.prototype.allocateLabel = function (id) {
    if (!(id in this._subsense_reference_managers))
        this._subsense_reference_managers[id] =
        new SubsenseReferenceManager(this, id);

    var label = this._id_to_label[id];
    if (label === undefined) {
        // More than 26 senses in a single article seems much.
        if (this._next_sense_label_ix >= sense_labels.length)
            throw new Error("hit the hard limit of 26 sense labels in a " +
                            "single article");

        label = this._id_to_label[id] =
            sense_labels[this._next_sense_label_ix++];
    }

    return label;
};

SenseReferenceManager.prototype.idToLabelForHead = function (id) {
    return this.idToLabel(id).toUpperCase();
};

SenseReferenceManager.prototype.idToSubsenseRefman = function (id) {
    return this._subsense_reference_managers[id];
};

SenseReferenceManager.prototype._deallocateAllLabels = function () {
    this._next_sense_label_ix = 0;
    for(var id in this._subsense_reference_managers) {
        this._subsense_reference_managers[id].deallocateAll();
    }
};

exports.SenseReferenceManager = SenseReferenceManager;

function SubsenseReferenceManager(parent_refman, parent_id) {
    ReferenceManager.call(this, "subsense");
    this._next_label = 1;
    this._parent_refman = parent_refman;
    this._parent_id = parent_id;
}

oop.inherit(SubsenseReferenceManager, ReferenceManager);

SubsenseReferenceManager.prototype.allocateLabel = function (id) {
    var label = this._id_to_label[id];
    if (label === undefined)
        label = this._id_to_label[id] = this._next_label++;
    return label;
};

// This is organized so that idToLabel returns a complete label using
// the sense's label + subsense's label. idToSublabel returns only the
// child's label.
SubsenseReferenceManager.prototype.idToLabel = function (id) {
    var parent_label = this._parent_refman.idToLabel(this._parent_id);
    return parent_label +
        ReferenceManager.prototype.idToLabel.call(this, id);
};

SubsenseReferenceManager.prototype.idToLabelForHead =
        SubsenseReferenceManager.prototype.idToLabel;

SubsenseReferenceManager.prototype.idToSublabel =
        ReferenceManager.prototype.idToLabel;

SubsenseReferenceManager.prototype._deallocateAllLabels = function () {
    this._next_label = 1;
};

// This one does not inherit from the ReferenceManager class.
function ExampleReferenceManager() {
    this.name = "example";
}

ExampleReferenceManager.prototype.idToLabel = function () {
    return undefined;
};

ExampleReferenceManager.prototype.getPositionalLabel = function (ptr, target,
                                                                 id) {
    var gui_target = $.data(target, "wed_mirror_node");
    var ret = "See ";
    var ref = gui_target.querySelector(domutil.toGUISelector("btw:cit>ref"))
            .cloneNode(true);
    var to_remove = ref.querySelectorAll("._gui, ._decoration_text");
    for(var i = 0, it; (it = to_remove[i]) !== undefined; ++i)
        it.parentNode.removeChild(it);
    ret += ref.textContent;
    ret += " quoted ";
    var order = ptr.compareDocumentPosition(target);
    if (order & Node.DOCUMENT_POSITION_DISCONNECTED)
        throw new Error("disconnected nodes");

    if (order & Node.DOCUMENT_POSITION_CONTAINS)
        throw new Error("ptr contains example!");

    // order & Node.DOCUMENT_POSITION_IS_CONTAINED
    // This could happen and we don't care...

    if (order & Node.DOCUMENT_POSITION_PRECEDING)
        ret += "above";
    else
        ret += "below";

    if (gui_target) {
        var parent = gui_target.parentNode;
        var head;
        while (parent) {
            head = domutil.childByClass(parent, "head");
            if (head)
                break;

            parent = parent.parentNode;
        }

        ret += " in " + head.textContent;

        //
        // This seems a bit backwards at first but what we want here
        // is not the term under which the *referred* example (the
        // target of the pointer) appears but the term under which the
        // *pointer* to the example appears.
        //
        // Basically, the text of the link means "See [referred work]
        // quoted [above/below] in [this heading], [and in the quote
        // look for this term]." The term to look for is the term
        // under which the pointer is located, not the term under
        // which the example (the target of the pointer) is located.
        //
        var gui_term;
        parent= $.data(ptr, "wed_mirror_node").parentNode;
        while (parent) {
            gui_term = parent.querySelector(".btw\\:term");
            if (gui_term)
                break;

            parent = parent.parentNode;
        }

        if (gui_term) {
            var term = $.data(gui_term, "wed_mirror_node");
            ret += ", " + term.textContent;
        }
    }

    ret += ".";

    return ret;
};

exports.ExampleReferenceManager = ExampleReferenceManager;

function WholeDocumentManager() {
    this._sense_refman = new SenseReferenceManager();
    this._example_refman = new ExampleReferenceManager();
}

WholeDocumentManager.prototype.getSenseLabelForHead = function (el) {
    var id = el.id;
    if (!id)
        throw new Error("element does not have an id: " + el);
    return this._sense_refman.idToLabelForHead(id);
};

WholeDocumentManager.prototype.getSenseLabel = function (el) {
    var what = el;
    var sense;
    while(what) {
        if (what.classList.contains("btw:sense")) {
            sense = what;
            break;
        }
        what = what.parentNode;
    }

    var id = sense && sense.id;

    if (!id)
        throw new Error("element does not have sense parent with an id: " + el);
    return this._sense_refman.idToLabel(id);
};

WholeDocumentManager.prototype.getSubsenseLabel = function (el) {
    var refman = this.getSubsenseRefman(el);

    var what = el;
    var subsense;
    while(what) {
        if (what.classList.contains("btw:subsense")) {
            subsense = what;
            break;
        }
        what = what.parentNode;
    }

    var id = subsense && subsense.id;
    if (!id)
        // This can happen during the decoration of the tree because
        // there is in general no guarantee about the order in which
        // elements are decorated. A second pass will ensure that the
        // label is not undefined.
        return undefined;
    var label = refman.idToLabelForHead(id);
    return label;
};

function closestSense(el) {
    var what = el;
    var sense;
    while(what) {
        if (what.classList.contains("btw:sense")) {
            sense = what;
            break;
        }
        what = what.parentNode;
    }

    return sense;
}

/**
 * @param {Node} el The element for which we want the subsense
 * reference manager. This element must be a child of a btw:sense
 * element or a btw:sense element.
 * @returns {module:btw_refmans~SubsenseReferenceManager} The subsense
 * reference manager.
 */
WholeDocumentManager.prototype.getSubsenseRefman = function (el) {
    var sense = closestSense(el);
    var id = sense && sense.id;
    return this._sense_refman.idToSubsenseRefman(id);
};

WholeDocumentManager.prototype.getRefmanForElement = function (el) {
    var name = util.getOriginalName(el);
    switch(name) {
    case "ptr":
    case "ref":
        // Find the target and return its value

        var target_attr = el.getAttribute(util.encodeAttrName("target"));
        if (!target_attr)
            return null;

        // Slice to drop the #.
        var target_id = target_attr.slice(1);

        var target = el.ownerDocument.getElementById("BTW-" + target_id);
        return target ? this.getRefmanForElement(target) : null;
    case "btw:sense":
        return this._sense_refman;
    case "btw:subsense":
        var sense = closestSense(el);
        return this._sense_refman.idToSubsenseRefman(sense.id);
    case "btw:example":
    case "btw:example-explained":
        return this._example_refman;
    default:
        throw new Error("unexpected element: " + el);
    }
};

exports.WholeDocumentManager = WholeDocumentManager;

});
