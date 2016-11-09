/**
 * @module lib/btw/semantic_field_editor/collections/chosen_field_collection
 * @desc Collection of chosen fields.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, _exports, _module) {
  "use strict";
  var Bb = require("backbone");
  var Field = require("../models/field");

  var ChosenFieldCollection = Bb.Collection.extend({
    __classname__: "ChosenFieldCollection",
    model: Field,

    // We override the modelId method so that models are identified by URL.
    // See the comments on the ``Field`` model to learn why we do not have a
    // id set on them.
    modelId: function modelId(attrs) {
      return attrs.url;
    },
  });

  return ChosenFieldCollection;
});
