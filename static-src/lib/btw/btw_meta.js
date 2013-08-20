define(function (require, exports, module) {
'use strict';

var $ = require("jquery");
var oop = require("wed/oop");
var util = require("wed/util");
var jqutil = require("wed/jqutil");
var TEIMeta = require("wed/modes/generic/metas/tei_meta").Meta;

/**
 * @class
 */
function BTWMeta() {
    TEIMeta.call(this);
}

oop.inherit(BTWMeta, TEIMeta);

BTWMeta.prototype.isInline = function (node) {
    var $node = $(node);
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
    case "btw:occurrence":
    case "btw:authority":
    case "btw:sense-emphasis":
    case "btw:todo":
        return true;
    case "tei:term":
        if ($(node.parentNode).is(jqutil.toDataSelector(
            "btw:english-rendition, btw:antonym, btw:cognate, btw:conceptual-proximate")))
            return false;
        /* falls through */
    default:
        return TEIMeta.prototype.isInline.call(this, node);
    }
};

exports.Meta = BTWMeta;

});
