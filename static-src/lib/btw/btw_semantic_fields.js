/**
 * @module wed/modes/btw/btw_semantic_fields
 * @desc Code for viewing documents edited by btw-mode.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_semantic_fields */
    function (require, exports, module) {
'use strict';

/**
 * Combines semantic fields so as to avoid duplicates. The result is
 * sorted in lexical order.
 *
 * @param {Array.<string>} sfs The semantic fields ot combine.
 * @param {integer} depth The depth of semantic fields we are
 * interested in. Semantic fields longer than this depth are truncated
 * to the specified depth **before** being compared with other fields.
 * @returns {Array.<string>} The set of semantic fields. It is sorted
 * in lexical order and does not contain duplicates.
 */
function combineSemanticFields (sfs, depth) {
    var sf_set = Object.create(null);
    var sf;

    var sfs_ix;
    if (depth === undefined)
        for (sfs_ix = 0; (sf = sfs[sfs_ix]); ++sfs_ix)
            sf_set[sf] = 1;
    else
        for (sfs_ix = 0; (sf = sfs[sfs_ix]); ++sfs_ix) {
            // Drop the | suffix or the letter suffix if the latter exists.
            var text = sf.replace(/\|.*$|[a-z]+.*$/, '');
            var parts = text.split(".");
            if (parts.length > depth)
                text = parts.slice(0, depth).join(".");
            sf_set[text] = 1;
        }

    return Object.keys(sf_set).sort();
}

exports.combineSemanticFields = combineSemanticFields;

});
