/**
 * Mode for BTW editing.
 * @author Louis-Dominique Dubeau
 */
import * as _ from "lodash";

import { domutil } from "wed";

export const BTW_MODE_ORIGIN = "https://github.com/mangalam-research/btw";

export const BTW_NS = "http://mangalamresearch.org/ns/btw-storage";

export function termsForSense(sense: Element,
                              mappings: Record<string, string>):
NodeListOf<Element> {
  return sense.querySelectorAll(
    domutil.toGUISelector("btw:english-rendition>btw:english-term", mappings));
}

const langToLabel: Record<string, string> = {
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
  "x-bhs-Latn": "Buddhist Hybrid Sanskrit; BHSkt",
};

const languageToCode: Record<string, string> = Object.create(null);
// tslint:disable-next-line:no-void-expression
(function compute(): void {
  for (const key of Object.keys(langToLabel)) {
    for (const lang of langToLabel[key].split("; ")) {
      languageToCode[lang] = key;
    }
  }
}());

export function languageCodeToLabel(code: string): string {
  return langToLabel[code];
}

export function languageToLanguageCode(language: string): string {
  return languageToCode[language];
}

const collapsibleTemplate =
  "\
<div class='_phantom_wrap <%= group_classes %>' role='tablist' \
aria-multiselectable='true'>\
<div class='_phantom_wrap card<%= kind %><%= card_classes %>'>\
<h4 class='_phantom_wrap card-header' role='tab' id='<%= heading_id %>'>\
<a class='_phantom collapsed<%= toggle_classes %>' data-toggle='collapse' \
href='#<%= collapse_id %>' aria-expanded='true' \
aria-controls='<%= collapse_id %>'>\
</a>\
</h4>\
<div id='<%= collapse_id %>' class='_phantom_wrap collapse' \
role='tabpanel' aria-labelledby='<%= heading_id %>'>\
<div class='_phantom_wrap card-body'></div>\
</div>\
</div>\
</div>";

export interface AdditionalClasses {
  group?: string;

  card?: string;

  toggle?: string;
}

export interface Collapsible {
  /** The top level element of the collapsible structure. */
  group: HTMLElement;

  /**
   * The innermost element in the heading. This is where the calling code
   * should add custom heading text.
   */
  heading: HTMLElement;

  /**
   * The innermost element of the collapsible part of the structure. This is
   * where the content that should be hidden or shown should be added by the
   * calling code.
   */
  content: HTMLElement;
}

/**
 * Creates a collapsible structure.
 *
 * @param document The document for which to create the structure.
 *
 * @param kind The kind of structure. This is one of Bootstrap's usual
 * ``"default"``, ``"info"``, ``"alert"``, etc.
 *
 * @param headingId The new id to use for the heading. Must be unique.
 *
 * @param collapseId The new id to use for the collapsible element. Must be
 * unique.
 *
 * @param additional Classes to add to the elements.
 *
 * @returns A new collapsible structure.
 */
export function makeCollapsible(document: Document,
                                kind: string,
                                headingId: string,
                                collapseId: string,
                                additional: AdditionalClasses = {}):
Collapsible {
  let additionalGroupClasses = additional.group;
  let additionalCardClasses = additional.card;
  let additionalToggleClasses = additional.toggle;

  additionalCardClasses =
    additionalCardClasses !== undefined ? ` ${additionalCardClasses}` : "";

  additionalGroupClasses =
    additionalGroupClasses !== undefined ? ` ${additionalGroupClasses}` : "";

  additionalToggleClasses =
    additionalToggleClasses !== undefined ? ` ${additionalToggleClasses}` : "";

  const el = domutil.htmlToElements(
    _.template(collapsibleTemplate)({
      kind: kind === "default" ? "" : ` card-${kind}`,
      group_classes: additionalGroupClasses,
      card_classes: additionalCardClasses,
      toggle_classes: additionalToggleClasses,
      heading_id: headingId,
      collapse_id: collapseId,
    }), document)[0] as HTMLElement;

  return {
    group: el,
    heading: el.getElementsByTagName("a")[0],
    content: el.getElementsByClassName("card-body")[0] as HTMLElement,
  };
}

/**
 * Updates the ids used by a collapsible structure created with
 * [[makeCollapsible]]. This updates the DOM directly.
 *
 * @param structure The structure to update.
 *
 * @param headingId The new id to use for the heading. Must be unique.
 *
 * @param collapseId The new id to use for the collapsible element. Must be
 * unique.
 */
export function updateCollapsible(structure: Element, headingId: string,
                                  collapseId: string): void {
  const heading = structure.getElementsByClassName("card-header")[0];
  heading.id = headingId;
  const a = heading.getElementsByTagName("a")[0];
  a.href = `#${collapseId}`;
  a.setAttribute("aria-controls", collapseId);

  const collapse = structure.getElementsByClassName("collapse")[0];
  collapse.setAttribute("aria-labelledby", headingId);
  collapse.id = collapseId;
}

export function getOriginalNameIfPossible(el: Element): string {
  const mirror = domutil.getMirror(el) as Element;
  return mirror === undefined ? "" : mirror.tagName;
}
