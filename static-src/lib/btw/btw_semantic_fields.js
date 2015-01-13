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
 * sorted.
 *
 * @param {Array.<string>} sfs The semantic fields ot combine. These
 * must be valid semantic field numbers. **This code does not validate
 * them!**
 * @param {integer} depth The depth of semantic fields we are
 * interested in. Semantic fields longer than this depth are truncated
 * to the specified depth **before** being compared with other fields.
 * @returns {Array.<string>} The set of semantic fields. It is sorted
 * and does not contain duplicates.
 */
function combineSemanticFields (sfs, depth) {
    var sf_set = Object.create(null);
    var sf;

    // The replacement of "." with "~" is done to allow us to use
    // JavaScript's stock sort function. The problem is that "." comes
    // before [a-z] in lexical order. So "01.01.02" would come
    // **before** "01.01aj", even if it is a child of the
    // latter. Mapping "." to "~", sorting, and remapping to "." takes
    // care of this sorting issue.

    var sfs_ix;
    if (depth === undefined)
        for (sfs_ix = 0; (sf = sfs[sfs_ix]); ++sfs_ix)
            sf_set[sf.replace(/\./g, "~")] = 1;
    else
        for (sfs_ix = 0; (sf = sfs[sfs_ix]); ++sfs_ix) {
            // Drop the | suffix or the letter suffix if the latter exists.
            var text = sf.replace(/\|.*$|[a-z]+.*$/, '');
            var parts = text.split(".");
            text = (parts.length > depth ? parts.slice(0, depth) :
                    parts).join("~");
            sf_set[text] = 1;
        }

    var result = Object.keys(sf_set).sort();
    for (sfs_ix = 0; (sf = result[sfs_ix]); ++sfs_ix)
        result[sfs_ix] = sf.replace(/~/g, ".");
    return result;
}

exports.combineSemanticFields = combineSemanticFields;

});
