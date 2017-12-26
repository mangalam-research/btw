/**
 * Validation code for btw-mode.
 * @author Louis-Dominique Dubeau
 */
import * as $ from "jquery";
import { ValidationError } from "salve";
import { ErrorData } from "salve-dom";

import * as domutil from "wed/domutil";
import { ModeValidator } from "wed/validator";

import { MappedUtil } from "./mapped-util";

const _indexOf = Array.prototype.indexOf;

export class Validator implements ModeValidator {
  constructor(private readonly guiRoot: Element,
              private readonly mapped: MappedUtil) {}

  // tslint:disable-next-line:max-func-body-length
  validateDocument(): ErrorData[] {
    //
    // ATTENTION: The logic here must be duplicated server-side to check whether
    // an article is deemed valid. We've thought about having some sort of
    // validation done in Node.js in the server which could perhaps resuse this
    // code but the problem is that there is no lightweight solution yet.
    //
    // Changes here must be mirrored in the btw-storage-[version].sch file.
    //

    const ret: ErrorData[] = [];
    // Verify that all senses have some semantic fields associated with them.
    const senses = this.guiRoot.getElementsByClassName("btw:sense");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < senses.length; ++i) {
      const sense = senses[i];
      const contrastive =
        sense.getElementsByClassName("btw:contrastive-section")[0];
      const sfs = sense.querySelectorAll(
        this.mapped.toGUISelector("btw:example btw:sf"));
      let found = false;
      // tslint:disable-next-line:prefer-for-of
      for (let sfsIx = 0; sfsIx < sfs.length; ++sfsIx) {
        const sf = sfs[sfsIx];
        // The contrastive section may not exist yet.
        if (!contrastive || !contrastive.contains(sf)) {
          found = true;
          break;
        }
      }

      if (!found) {
        const dataSense = $.data(sense, "wed_mirror_node");
        ret.push({
          error: new ValidationError("sense without semantic fields"),
          node: dataSense.parentNode,
          index: _indexOf.call(dataSense.parentNode.childNodes, dataSense),
        });
      }
    }

    // Verify that all cognates have some semantic fields associated with them.
    const cognates = this.guiRoot.getElementsByClassName("btw:cognate");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < cognates.length; ++i) {
      const cognate = cognates[i];
      const sfs = cognate.querySelectorAll(
        this.mapped.toGUISelector("btw:example btw:sf"));
      if (sfs.length === 0) {
        const dataCognate = $.data(cognate, "wed_mirror_node");
        ret.push({
          error: new ValidationError("cognate without semantic fields"),
          node: dataCognate.parentNode,
          index: _indexOf.call(dataCognate.parentNode.childNodes, dataCognate),
        });
      }
    }

    // Verify that all semantic fields are of the proper format.
    const allSfs = this.guiRoot.getElementsByClassName("btw:sf");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < allSfs.length; ++i) {
      const sf = allSfs[i];
      const dataSf = $.data(sf, "wed_mirror_node");
      const text = dataSf.textContent;
      const parts = text.split("@");

      for (const part of parts) {
        // tslint:disable-next-line:max-line-length
        if (!/^\s*\d{2}(?:\.\d{2})*(?:\s*\|\s*\d{2}(?:\.\d{2})*)?(?:aj|av|cj|in|n|p|ph|v|vi|vm|vp|vr|vt)\s*$/.test(part)) {
          ret.push({
            error: new ValidationError(
              "semantic field is not in a recognized format"),
            node: dataSf.parentNode,
            index: _indexOf.call(dataSf.parentNode.childNodes, dataSf),
          });
        }
      }
    }

    // Verify that surnames are not empty
    const surnames = this.guiRoot.getElementsByClassName("surname");
    // tslint:disable-next-line:prefer-for-of
    for (let i = 0; i < surnames.length; ++i) {
      const surname = surnames[i];
      const dataSurname = $.data(surname, "wed_mirror_node");
      if (dataSurname.textContent.length === 0) {
        ret.push({
          error: new ValidationError("surname cannot be empty"),
          node: dataSurname,
          index: 0,
        });
      }
    }

    const btwCredits = this.guiRoot.getElementsByClassName("btw:credits")[0];
    // btw:credits can be missing on files that should be upgraded to the latest
    // version of the schema.
    if (btwCredits !== undefined) {
      const dataBtwCredits = $.data(btwCredits, "wed_mirror_node");
      // Verify that there is an editor
      if (btwCredits.getElementsByClassName("editor").length === 0) {
        ret.push({
          error: new ValidationError("there must be at least one editor"),
          node: dataBtwCredits,
          index: 0,
        });
      }

      // Verify that there is an author
      if (btwCredits.getElementsByClassName("btw:credit").length === 0) {
        ret.push({
          error: new ValidationError("there must be at least one author"),
          node: dataBtwCredits,
          index: 0,
        });
      }
    }
    // Else schema validation will have taken care of the missing btw:credits...

    return ret;
  }
}
