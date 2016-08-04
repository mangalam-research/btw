/**
 * @module lib/btw/semantic_field_editor/models/field
 * @desc Field model.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";
  var Bb = require("backbone");
  require("backbone-relational");

  //
  // Fields do not have id defined. When we query semantic fields from the
  // server, we do not always have the same needs with regards to how much of a
  // semantic field we want to see. The same semantic field can be queried to
  // show very little info, or more. So Backbone ``Field`` objects with the same
  // id could contain different data. The downsides to this:
  //
  // - Field collections that can contain arbitrary lists of fields should guard
  //   against duplicating fields.
  //
  // - Applications may take more memory than they could. Really if the same
  //   semantic field has two Field objects in memory, they *could* be combined
  //   into one object that shows a union of the attributes on both objects.
  //
  // However, getting a system in place that combine field object so that
  // client-site a field with id X exists once and only once, while doable, is
  // not a trivial enterprise.
  //
  // And note that setting an id on Field would require that we have a fetching
  // system in place that maintains one and only one JavaScript object per
  // id. **Otherwise, RelationalModel will raise fatal errors.**
  //
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
