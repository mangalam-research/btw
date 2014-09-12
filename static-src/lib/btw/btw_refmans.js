define(function (require, exports, module) {
'use strict';

var oop = require("wed/oop");
var ReferenceManager = require("wed/refman").ReferenceManager;
var $ = require("jquery");
var util = require("wed/util");
var domutil = require("wed/domutil");

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

        var term;
        parent= ptr.parentNode;
        while (parent) {
            term = domutil.childByClass(parent, "term");
            if (term)
                break;

            parent = parent.parentNode;
        }

        if (term)
            ret += ", " + term.textContent;
    }

    ret += ".";

    return ret;
};

exports.ExampleReferenceManager = ExampleReferenceManager;

});
