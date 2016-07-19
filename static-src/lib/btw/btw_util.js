/**
 * @module wed/modes/btw/btw_util
 * @desc Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */

define(/** @lends module:wed/modes/btw/btw_util */ function btwUtil(
  require, exports, _module) {
  "use strict";

  var domutil = require("wed/domutil");
  var _ = require("lodash");

  function termsForSense(sense) {
    return sense.querySelectorAll(domutil.toGUISelector(
      "btw:english-rendition>btw:english-term"));
  }

  var langToLabel = {
    "sa-Latn": "Sanskrit; Skt",
    "pi-Latn": "Pāli; Pāli",
    "bo-Latn": "Tibetan; Tib",
    "zh-Hant": "Chinese; Ch",
    "x-gandhari-Latn": "Gāndhārī; Gāndh",
    en: "English; Eng",
    fr: "French; Fr",
    de: "German; Ger",
    it: "Italian; It",
    es: "Spanish; Sp",
    // Additional languages
    la: "Latin; Lat",
    "zh-Latn-pinyin": "Chinese Pinyin; Ch Pin",
    "x-bhs-Latn": "Buddhist Hybrid Sanskrit; BHSkt",
  };

  var languageToCode = {};
  (function compute() {
    var keys = Object.keys(langToLabel);
    for (var i = 0; i < keys.length; ++i) {
      var key = keys[i];
      var languages = langToLabel[key].split("; ");
      for (var j = 0; j < languages.length; ++j) {
        languageToCode[languages[j]] = key;
      }
    }
  }());


  function languageCodeToLabel(code) {
    return langToLabel[code];
  }

  function languageToLanguageCode(language) {
    return languageToCode[language];
  }

  var collapsibleTemplate =
        "\
<div class='_phantom_wrap panel-group<%= group_classes %>' role='tablist' \
     aria-multiselectable='true'>\
 <div class='_phantom_wrap panel panel-<%= kind %><%= panel_classes %>'>\
  <div class='_phantom_wrap panel-heading' role='tab' id='<%= heading_id %>'>\
   <h4 class='_phantom_wrap panel-title'>\
    <a class='_phantom collapsed' data-toggle='collapse' \
       href='#<%= collapse_id %>' aria-expanded='true' \
       aria-controls='<%= collapse_id %>'>\
    </a>\
   </h4>\
  </div>\
  <div id='<%= collapse_id %>' class='_phantom_wrap panel-collapse collapse' \
       role='tabpanel' aria-labelledby='<%= heading_id %>'>\
   <div class='_phantom_wrap panel-body'></div>\
  </div>\
 </div>\
</div>";


  /**
   * Creates a collapsible structure.
   *
   * @param {Document} document The document for which to create the
   * structure.
   * @param {string} kind The kind of structure. This is one of
   * Bootstrap's usual ``"default"``, ``"info"``, ``"alert"``, etc.
   * @param {string} headingId The new id to use for the heading. Must
   * be unique.
   * @param {string} collapseId The new id to use for the collapsible
   * element. Must be unique.
   * @param {object} additionalClasses A list of classes to add
   * to the elements.
   * @returns {{group: Element, heading: Element, content: Element}} The
   * ``group`` key contains the top level element of the collapsible
   * structure. The ``heading`` key contains the innermost element
   * in the heading. This is where the calling code should add custom
   * heading text. The ``content`` key contains the innermost element
   * of the collapsible part of the structure. This is where the
   * content that should be hidden or shown should be added by the
   * calling code.
   */
  function makeCollapsible(document, kind, headingId, collapseId,
                           additionalClasses) {
    additionalClasses = additionalClasses || {};
    var additionalGroupClasses = additionalClasses.group;
    var additionalPanelClasses = additionalClasses.panel;

    additionalPanelClasses =
      additionalPanelClasses ? " " + additionalPanelClasses : "";

    additionalGroupClasses =
      additionalGroupClasses ? " " + additionalGroupClasses : "";

    var el = domutil.htmlToElements(
      _.template(collapsibleTemplate)({
        kind: kind,
        group_classes: additionalGroupClasses,
        panel_classes: additionalPanelClasses,
        heading_id: headingId,
        collapse_id: collapseId,
      }), document)[0];

    return {
      group: el,
      heading: el.getElementsByTagName("a")[0],
      content: el.getElementsByClassName("panel-body")[0],
    };
  }

  /**
   * Updates the ids used by a collapsible structure created with {@link
   * module:wed/modes/btw/btw_util~makeCollapsible
   * makeCollapsible}. This updates the DOM directly.
   *
   * @param {Element} structure The structure to update.
   * @param {string} headingId The new id to use for the heading. Must
   * be unique.
   * @param {string} collapseId The new id to use for the collapsible
   * element. Must be unique.
   */
  function updateCollapsible(structure, headingId, collapseId) {
    var heading = structure.getElementsByClassName("panel-heading")[0];
    heading.id = headingId;
    var a = heading.getElementsByTagName("a")[0];
    a.href = "#" + collapseId;
    a.setAttribute("aria-controls", collapseId);

    var collapse = structure.getElementsByClassName("panel-collapse")[0];
    collapse.setAttribute("aria-labelledby", headingId);
    collapse.id = collapseId;
  }

  function biblDataToReferenceText(data) {
    var text = "";
    if (data.reference_title) {
      text = data.reference_title;
    }
    else {
      var creators = data.creators;
      text = "***ITEM HAS NO CREATORS***";
      if (creators) {
        text = creators.split(",")[0];
      }

      if (data.date) {
        text += ", " + data.date;
      }
    }
    return text;
  }

  function biblSuggestionSorter(array) {
    var itemPkToPss = {};
    var items = [];

    var i;
    var it;
    var l;
    // Separate items (secondary sources) and primary sources.
    for (i = 0; i < array.length; ++i) {
      it = array[i];
      if (!it.item) {
        items.push(it);
      }
      else {
        l = itemPkToPss[it.item.pk];
        if (!l) {
          l = itemPkToPss[it.item.pk] = [];
        }
        l.push(it);
      }
    }

    items.sort(function cmp(a, b) {
      // Order by creator...
      if (a.creators < b.creators) {
        return -1;
      }

      if (a.creators > b.creators) {
        return 1;
      }

      // then by title....
      if (a.title < b.title) {
        return -1;
      }

      if (a.title > b.title) {
        return 1;
      }

      // then by date...
      if (a.date < b.date) {
        return -1;
      }

      if (a.date > b.date) {
        return 1;
      }

      // It is unlikely that we'd get here but if we do, then...
      return Number(a.pk) - Number(b.pk);
    });

    function sortPss(a, b) {
      // We don't bother with 0 since it is not possible to
      // have two identical reference titles.
      return (a.reference_title < b.reference_title) ? -1 : 1;
    }

    var sortedByItem = [];
    for (i = 0; i < items.length; ++i) {
      it = items[i];
      l = itemPkToPss[it.pk];
      if (l) {
        l.sort(sortPss);
        sortedByItem = sortedByItem.concat(l);
        delete itemPkToPss[it.pk];
      }
      sortedByItem.push(it);
    }

    // Any remaining primary sources in itemPkToPss get to the front.
    var pss = [];
    Object.keys(itemPkToPss).forEach(function each(key) {
      pss = pss.concat(itemPkToPss[key]);
    });

    pss.sort(sortPss);

    return pss.concat(sortedByItem);
  }


  exports.languageCodeToLabel = languageCodeToLabel;
  exports.languageToLanguageCode = languageToLanguageCode;

  exports.termsForSense = termsForSense;
  exports.makeCollapsible = makeCollapsible;
  exports.updateCollapsible = updateCollapsible;
  exports.biblDataToReferenceText = biblDataToReferenceText;
  exports.biblSuggestionSorter = biblSuggestionSorter;
});
