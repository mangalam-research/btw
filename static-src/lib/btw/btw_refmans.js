define(function (require, exports, module) {
'use strict';

var oop = require("wed/oop");
var ReferenceManager = require("wed/refman").ReferenceManager;

var sense_labels = 'abcdefghijklmnopqrstuvwxyz';
function SenseReferenceManager() {
    ReferenceManager.call(this, "sense");
    this._next_sense_label_ix = 0;
}

oop.inherit(SenseReferenceManager, ReferenceManager);

(function () {
    this.allocateLabel = function (id) {
        // More than 26 senses in a single article seems much.
        if (this._next_sense_label_ix >= sense_labels.length)
            throw new Error("hit the hard limit of 26 sense labels in a single article");

        /* jshint boss:true */
        return this._id_to_label[id] = sense_labels[this._next_sense_label_ix++];
    };

    this._deallocateAllLabels = function () {
        this._next_sense_label_ix = 0;
    };
}).call(SenseReferenceManager.prototype);

exports.sense_refs = new SenseReferenceManager();
});
