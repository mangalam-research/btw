/**
 * @module lib/btw/semantic_field_editor/models/field
 * @desc Field model.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var Bb = require("backbone");
  require("backbone-relational");

  var Field = Bb.RelationalModel.extend({
    relations: [{
      type: "HasOne",
      key: "parent",
    }, {
      type: "HasMany",
      key: "children",
    }],
  });

  return Field;
});
