define(function (require, exports, module) {
'use strict';

var oop = require("wed/oop");
var ReferenceManager = require("wed/refman").ReferenceManager;
var jqutil = require("wed/jqutil");
var $ = require("jquery");
var util = require("wed/util");

var sense_labels = 'abcdefghijklmnopqrstuvwxyz';
function SenseReferenceManager() {
    ReferenceManager.call(this, "sense");
    this._subsense_reference_managers = {};
    this._next_sense_label_ix = 0;
}

oop.inherit(SenseReferenceManager, ReferenceManager);

SenseReferenceManager.prototype.allocateLabel = function (id) {
    var label = this._id_to_label[id];
    if (label === undefined) {
        // More than 26 senses in a single article seems much.
        if (this._next_sense_label_ix >= sense_labels.length)
            throw new Error("hit the hard limit of 26 sense labels in a " +
                            "single article");

        label = this._id_to_label[id] =
            sense_labels[this._next_sense_label_ix++];

        this._subsense_reference_managers[id] = new SubsenseReferenceManager(label);
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
    this._subsense_reference_managers = {};
};

exports.SenseReferenceManager = SenseReferenceManager;

function SubsenseReferenceManager(parent_label) {
    ReferenceManager.call(this, "subsense");
    this._next_label = 1;
    this._parent_label = parent_label;
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
    return this._parent_label +
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

ExampleReferenceManager.prototype.getPositionalLabel = function ($ptr, $target,
                                                                 id) {
    var ret = "See ";
    var $ref = $target.find(jqutil.toDataSelector("btw:cit>ref")).first();
    ret += $ref.text();
    ret += " quoted ";
    var order = $ptr[0].compareDocumentPosition($target[0]);
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

    var gui_target = $target.data("wed_mirror_node");
    if (gui_target) {
        var $gui_target = $(gui_target);
        ret += " in " + $gui_target.closest(":has(> .head)").children(".head").first().text();

        var term = $ptr.closest(":has(>" +
                                util.classFromOriginalName("term") +
                                ")").children(util.classFromOriginalName("term")).first().text();

        if (term)
            ret += ", " + term;
    }

    ret += ".";

    return ret;
};

exports.ExampleReferenceManager = ExampleReferenceManager;

});
