/**
 * @module wed/modes/btw/btw_util
 * @desc Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_util */
    function (require, exports, module) {
'use strict';

var util = require("wed/util");
var domutil = require("wed/domutil");
var _ = require("lodash");

function termsForSense(sense) {
    return sense.querySelectorAll(domutil.toGUISelector(
        "btw:english-rendition>btw:english-term"));
}

var lang_to_label = {
    "sa-Latn": "Sanskrit; Skt",
    "pi-Latn": "Pāli; Pāli",
    "bo-Latn": "Tibetan; Tib",
    "zh-Hant": "Chinese; Ch",
    "x-gandhari-Latn": "Gāndhārī; Gāndh",
    "en": "English; Eng",
    "fr": "French; Fr",
    "de": "German; Ger",
    "it": "Italian; It",
    "es": "Spanish; Sp",
    // Additional languages
    "la": "Latin; Lat",
    "zh-Latn-pinyin": "Chinese Pinyin; Ch Pin",
    "x-bhs-Latn": "Buddhist Hybrid Sanskrit; BHSkt"
};

var language_to_code = {};
(function () {
    var keys = Object.keys(lang_to_label);
    for(var i = 0, key; (key = keys[i]) !== undefined; ++i) {
        var languages = lang_to_label[key].split("; ");
        for(var j = 0, language; (language = languages[j]) !== undefined; ++j)
            language_to_code[language] = key;
    }
})();


function languageCodeToLabel(code) {
    return lang_to_label[code];
}

function languageToLanguageCode(language) {
    return language_to_code[language];
}

function htmlToElements(document, html) {
    var frag = document.createDocumentFragment();
    var div = document.createElement("div");
    frag.appendChild(div);
    div.innerHTML = html;
    return Array.prototype.slice.call(div.childNodes);
}

var collapsible_template =
'\
<div class="_phantom_wrap panel-group" role="tablist" aria-multiselectable="true">\
 <div class="_phantom_wrap panel panel-<%= kind %><%= heading_classes %>">\
  <div class="_phantom_wrap panel-heading" role="tab" id="<%= heading_id %>">\
   <h4 class="_phantom_wrap panel-title">\
    <a class="_phantom collapsed" data-toggle="collapse" href="#<%= collapse_id %>" aria-expanded="true" aria-controls="<%= collapse_id %>">\
    </a>\
   </h4>\
  </div>\
  <div id="<%= collapse_id %>" class="_phantom_wrap panel-collapse collapse" role="tabpanel" aria-labelledby="<%= heading_id %>">\
   <div class="_phantom_wrap panel-body"></div>\
  </div>\
 </div>\
</div>';


/**
 * Creates a collapsible structure.
 *
 * @param {Document} document The document for which to create the
 * structure.
 * @param {string} kind The kind of structure. This is one of
 * Bootstrap's usual ``"default"``, ``"info"``, ``"alert"``, etc.
 * @param {string} heading_id The new id to use for the heading. Must
 * be unique.
 * @param {string} collapse_id The new id to use for the collapsible
 * element. Must be unique.
 * @param {string} additional_heading_classes A list of classes to add
 * to the heading.
 * @returns {{group: Element, heading: Element, content: Element}} The
 * ``group`` key contains the top level element of the collapsible
 * structure. The ``heading`` key contains the innermost element
 * in the heading. This is where the calling code should add custom
 * heading text. The ``content`` key contains the innermost element
 * of the collapsible part of the structure. This is where the
 * content that should be hidden or shown should be added by the
 * calling code.
 */
function makeCollapsible(document, kind, heading_id, collapse_id,
                         additional_heading_classes) {
    additional_heading_classes =
        additional_heading_classes ?
        " " + additional_heading_classes : "";

    var el = htmlToElements(
        document,
        _.template(collapsible_template, {
            kind: kind,
            heading_classes: additional_heading_classes,
            heading_id: heading_id,
            collapse_id: collapse_id
        }))[0];

    return {
        group: el,
        heading: el.getElementsByTagName("a")[0],
        content: el.getElementsByClassName("panel-body")[0]
    };
}

/**
 * Updates the ids used by a collapsible structure created with {@link
 * module:wed/modes/btw/btw_util~makeCollapsible
 * makeCollapsible}. This updates the DOM directly.
 *
 * @param {Element} structure The structure to update.
 * @param {string} heading_id The new id to use for the heading. Must
 * be unique.
 * @param {string} collapse_id The new id to use for the collapsible
 * element. Must be unique.
 */
function updateCollapsible(structure, heading_id, collapse_id) {
    var heading =
            structure.getElementsByClassName("panel-heading")[0];
    heading.id = heading_id;
    var a = heading.getElementsByTagName("a")[0];
    a.href = "#" + collapse_id;
    a.attributes["aria-controls"] = collapse_id;

    var collapse =
            structure.getElementsByClassName("panel-collapse")[0];
    collapse.attributes["aria-labelledby"] = heading_id;
    collapse.id = collapse_id;
}

exports.languageCodeToLabel = languageCodeToLabel;
exports.languageToLanguageCode = languageToLanguageCode;

exports.termsForSense = termsForSense;
exports.htmlToElements = htmlToElements;
exports.makeCollapsible = makeCollapsible;
exports.updateCollapsible = updateCollapsible;

});
