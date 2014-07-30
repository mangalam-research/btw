/**
 * @module wed/modes/btw/btw_view
 * @desc Code for viewing documents edited by btw-mode.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_view */
    function (require, exports, module) {
'use strict';

var $ = require("jquery");
var btw_meta = require("./btw_meta");

var $document = $(".wed-document");

var meta = new btw_meta.Meta();

function process(el) {
    var classes = meta.getAdditionalClasses(el);
    if (classes.length)
        el.className += " " + classes;



    // Process the children...
    var children = el.children;
    for(var i = 0, limit = children.length; i < limit; ++i)
        process(children[i]);
}

process($document[0]);

});
