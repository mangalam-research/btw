define(function (require, exports, module) {
'use strict';

var $ = require("jquery");
var util = require("wed/util");

function termsForSense($sense) {
    return $sense.find(util.classFromOriginalName("btw:english-rendition") +
                       ">" + util.classFromOriginalName("btw:english-term"));
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

exports.languageCodeToLabel = languageCodeToLabel;
exports.languageToLanguageCode = languageToLanguageCode;

exports.termsForSense = termsForSense;

});
