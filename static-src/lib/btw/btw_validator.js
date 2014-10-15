/**
 * @module wed/modes/btw/btw_validator
 * @desc Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_validator */
    function (require, exports, module) {

var oop = require("wed/oop");
var ModeValidator = require("wed/mode_validator").ModeValidator;
var ValidationError = require("salve/validate").ValidationError;
var domutil = require("wed/domutil");
var $ = require("jquery");

var _indexOf = Array.prototype.indexOf;

function Validator(gui_root, data_root) {
    ModeValidator.call(this, gui_root, data_root);
}

oop.inherit(Validator, ModeValidator);

Validator.prototype.validateDocument = function () {
    //
    // ATTENTION: The logic here must be duplicated server-side to
    // check whether an article is deemed valid. We've thought about having some sort of validation done in Node.js in the server which could perhaps resuse this code but the problem is that
    //

    var ret = [];
    var i, sfs;
    // Verify that all senses have some semantic fields associated
    // with them.
    var senses = this._gui_root.getElementsByClassName("btw:sense");
    var sense;
    for (i = 0; (sense = senses[i]); ++i) {
        var contrastive =
                sense.getElementsByClassName("btw:contrastive-section")[0];
        sfs = sense.querySelectorAll(
            domutil.toGUISelector("btw:example btw:sf"));
        var found = false;
        for (var sfs_ix = 0, sf; !found && (sf = sfs[sfs_ix]); ++sfs_ix) {
            // The contrastive section may not exist yet.
            if (!contrastive || !contrastive.contains(sfs))
                found = true;
        }

        if (!found) {
            var data_sense = $.data(sense, "wed_mirror_node");
            ret.push({
                error: new ValidationError("sense without semantic fields"),
                node: data_sense.parentNode,
                index: _indexOf.call(data_sense.parentNode.childNodes,
                                     data_sense)
            });
        }
    }

    // Verify that all cognates have some semantic fields associated
    // with them.
    var cognates = this._gui_root.getElementsByClassName("btw:cognate");
    var cognate;
    for (i = 0; (cognate = cognates[i]); ++i) {
        sfs = cognate.querySelectorAll(
            domutil.toGUISelector("btw:example btw:sf"));
        if (sfs.length === 0) {
            var data_cognate = $.data(cognate, "wed_mirror_node");
            ret.push({
                error: new ValidationError("cognate without semantic fields"),
                node: data_cognate.parentNode,
                index: _indexOf.call(data_cognate.parentNode.childNodes,
                                     data_cognate)
            });
        }
    }

    return ret;
};

exports.Validator = Validator;

});
