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
    // check whether an article is deemed valid. We've thought about
    // having some sort of validation done in Node.js in the server
    // which could perhaps resuse this code but the problem is that
    // there is no lightweight solution yet.
    //
    // Changes here must be mirrored in the btw-storage-[version].sch
    // file.
    //

    var ret = [];
    var i, sfs, sf;
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
        for (var sfs_ix = 0; !found && (sf = sfs[sfs_ix]); ++sfs_ix) {
            // The contrastive section may not exist yet.
            if (!contrastive || !contrastive.contains(sf))
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

    // Verify that all semantic fields are of the proper format.
    sfs = this._gui_root.getElementsByClassName("btw:sf");
    for (i = 0; (sf = sfs[i]); ++i) {
        var data_sf = $.data(sf, "wed_mirror_node");
        var text = data_sf.textContent;
        var parts = text.split("@");

        for (var partIx = 0; partIx < parts.length; ++partIx) {
            var part = parts[partIx];
            if (!/^\s*\d{2}(?:\.\d{2})*(?:\s*\|\s*\d{2}(?:\.\d{2})*)?(?:aj|av|cj|in|n|p|ph|v|vi|vm|vp|vr|vt)\s*$/.test(part)) {
                ret.push({
                    error: new ValidationError(
                        "semantic field is not in a recognized format"),
                    node: data_sf.parentNode,
                    index: _indexOf.call(data_sf.parentNode.childNodes,
                                         data_sf)
                });
            }
        }
    }

    // Verify that surnames are not empty
    var surnames = this._gui_root.getElementsByClassName("surname");
    var surname;
    for (i = 0; (surname = surnames[i]); ++i) {
        var data_surname = $.data(surname, "wed_mirror_node");
        if (data_surname.textContent.length === 0)
            ret.push({
                error: new ValidationError(
                    "surname cannot be empty"),
                node: data_surname,
                index: 0
            });
    }

    // Verify that there is an editor
    var btw_credits = this._gui_root.getElementsByClassName("btw:credits")[0];
    // btw:credits can be missing on files that should be upgraded to
    // the latest version of the schema.
    if (btw_credits) {
        var data_btw_credits = $.data(btw_credits, "wed_mirror_node");
        if (!btw_credits.getElementsByClassName("editor").length) {
            ret.push({
                error: new ValidationError("there must be at least one editor"),
                node: data_btw_credits,
                index: 0
            });
        }

        // Verify that there is an author
        if (!btw_credits.getElementsByClassName("btw:credit").length) {
            ret.push({
                error: new ValidationError("there must be at least one author"),
                node: data_btw_credits,
                index: 0
            });
        }
    }
    // Else schema validation will have taken care of the missing btw:credits...

    return ret;
};

exports.Validator = Validator;

});
