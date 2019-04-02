/**
 * @module lib/btw/semantic_field_editor/views/navigators/page
 * @desc A page for a navigator.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, _exports, _module) {
  "use strict";

  var BreadcrumbView = require("../field/breadcrumb");

  var PageView = BreadcrumbView.extend({
    __classname__: "PageView",
    details: "all",
    tagName: "div",
  });

  return PageView;
});
