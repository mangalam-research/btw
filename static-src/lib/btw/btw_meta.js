define(function factory(require, exports, _module) {
  "use strict";

  var $ = require("jquery");
  var oop = require("wed/oop");
  var util = require("wed/util");
  var TEIMeta = require("wed/modes/generic/metas/tei_meta").Meta;

  /**
   * @classdesc Meta-information for BTW's schema.
   *
   * @extends module:modes/generic/metas/tei_meta~Meta
   *
   * @constructor
   * @param {Object} options The options to pass to the Meta.
   */
  function BTWMeta() {
    TEIMeta.apply(this, arguments);
  }

  oop.inherit(BTWMeta, TEIMeta);

  BTWMeta.prototype.isInline = function isInline(node) {
    // We need to normalize the name to fit the names we have below.
    var originalName = util.getOriginalName(node);
    var parts = originalName.split(":");
    // XXX this is taking a shortcut. We should instead find the
    // namespace of the node and convert it to an appropriate prefix
    // to use below.
    if (parts.length === 1) {
      parts[1] = parts[0];
      parts[0] = "tei";
    }
    var name = parts.join(":");

    switch (name) {
    case "btw:sf":
    case "btw:lemma-instance":
    case "btw:antonym-instance":
    case "btw:cognate-instance":
    case "btw:conceptual-proximate-instance":
    case "btw:lang":
    case "btw:sense-emphasis":
    case "btw:todo":
      return true;
    case "tei:editor":
    case "tei:persName":
    case "tei:resp":
      return false;
    case "btw:none":
    case "btw:english-term":
    case "btw:term":
    case "tei:ptr":
      if (node.parentNode &&
          util.getOriginalName(node.parentNode) === "btw:citations") {
        return false;
      }
      /* falls through */
    default:
      return TEIMeta.prototype.isInline.call(this, node);
    }
  };

  var cachedMapping;

  BTWMeta.prototype.getNamespaceMappings = function getNamespaceMappings() {
    // BTW's mapping is identical to TEI's but with the addition of
    // the "btw" prefix.
    if (cachedMapping) {
      return cachedMapping;
    }

    var ret = TEIMeta.prototype.getNamespaceMappings.call(this);
    ret = $.extend({}, ret, {
      btw: "http://mangalamresearch.org/ns/btw-storage",
    });
    cachedMapping = ret;
    return ret;
  };

  exports.Meta = BTWMeta;
});
