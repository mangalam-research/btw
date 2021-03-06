/**
 * @module lib/semantic-fields/util
 * @desc Utilities for semantic fields.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:lib/semantic-fields/util */ function factory(require, exports, _module) {
  "use strict";

  var _ = require("lodash");

  function normalize(path) {
    return path.replace(/\./g, "~");
  }

  /**
   * Sort semantic fields.
   *
   * @param {Array.<Object>} sfs The semantic fields to sort. This array should
   * contain the objects returned by the REST call to the BTW backend.
   *
   * @returns {Array.<string>} The sorted fields.
   */
  function sortSemanticFields(sfs) {
    return _.sortBy(sfs, function key(sf) {
      return normalize(sf.path);
    });
  }

  exports.sortSemanticFields = sortSemanticFields;
});
