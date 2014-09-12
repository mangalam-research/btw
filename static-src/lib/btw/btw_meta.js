define(function (require, exports, module) {
'use strict';

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

BTWMeta.prototype.isInline = function (node) {
    // We need to normalize the name to fit the names we have below.
    var original_name = util.getOriginalName(node);
    var parts = original_name.split(":");
    // XXX this is taking a shortcut. We should instead find the
    // namespace of the node and convert it to an appropriate prefix
    // to use below.
    if (parts.length === 1) {
        parts[1] = parts[0];
        parts[0] = "tei";
    }
    var name = parts.join(":");

    switch(name) {
    case "btw:sf":
    case "btw:lemma-instance":
    case "btw:antonym-instance":
    case "btw:cognate-instance":
    case "btw:conceptual-proximate-instance":
    case "btw:lang":
    case "btw:sense-emphasis":
    case "btw:todo":
        return true;
    case "btw:none":
    case "btw:english-term":
    case "btw:term":
        return false;
    default:
        return TEIMeta.prototype.isInline.call(this, node);
    }
};

var cached_mapping;

BTWMeta.prototype.getNamespaceMappings = function () {
    // BTW's mapping is identical to TEI's but with the addition of
    // the "btw" prefix.
    if (cached_mapping)
        return cached_mapping;

    var ret = TEIMeta.prototype.getNamespaceMappings.call(this);
    $.extend({}, ret, {
        "btw": "http://mangalamresearch.org/ns/btw-storage"
    });
    cached_mapping = ret;
    return ret;
};

exports.Meta = BTWMeta;

});
