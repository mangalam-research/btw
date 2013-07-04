define(function (require, exports, module) {
'use strict';

var oop = require("wed/oop");
var ReferenceManager = require("wed/refman").ReferenceManager;

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

});
