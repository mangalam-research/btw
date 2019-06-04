/**
 * Class for fetching semantic fields.
 * @author Louis-Dominique Dubeau
 */
import * as Promise from "bluebird";
import * as _ from "lodash";

import { ajax } from "../ajax";

export interface ChangeRecord {
  lemma: string;

  url: string;

  datetime: string;

  published: boolean;
}

export interface TreeViewNode {
  text: string;

  href: string;

  nodes?: TreeViewNode[];

  selectable: false;
}

export interface SemanticFieldCommon {
  url: string;

  path: string;

  heading: string;

  heading_for_display: string;

  is_subcat: string;

  verbose_pos: string;

}

interface SemanticFieldRaw extends SemanticFieldCommon {
  changerecords: ChangeRecord[];
}

export interface SemanticField extends SemanticFieldCommon {
  tree?: TreeViewNode[];

  changerecords: Record<string, ChangeRecord[]>;
}

export class SFFetcher {
  private readonly fields: string | undefined;
  private readonly depthParams: Record<string, number> = Object.create(null);
  private readonly cache: Record<string, SemanticField> = Object.create(null);

  /**
   * @param fetchUrl The URL to use to perform the ajax query to fetch
   * information about semantic fields.
   *
   * @param excludeUrl: This is the URL of an entry or an entry's change record
   * to exclude from the results returned in the ``changerecord`` field. (We use
   * this to avoid having an article refer to itself.)
   *
   * @param fields A list of extra fields to return or fields to remove from the
   * results.
   *
   * @param depths A map of depths settings.
   */
  constructor(public readonly fetchUrl: string,
              public readonly excludeUrl: string | undefined,
              fields?: string[],
              depths?: Record<string, number>) {

    // We marshal fields into the value we pass to requests.
    this.fields = fields !== undefined ? fields.join(",") : undefined;

    // We also marshal depth into the value we pass to requests.
    if (depths !== undefined) {
      const depthParams = this.depthParams;
      for (const key of Object.keys(depths)) {
        depthParams[`depths.${key}`] = depths[key];
      }
    }
  }

  /**
   * Fetch some semantic fields.
   *
   * @param refs The semantic field references (semantic field paths).
   *
   * @returns A map of paths to semantic field.
   */
  fetch(refs: string[]): Promise<Record<string, SemanticField>> {
    // Figure out what is already resolved from previous calls, and what needs
    // resolving.
    const resolved: Record<string, SemanticField> = Object.create(null);
    const unresolved: string[] = [];
    for (const ref of refs) {
      const links = this.cache[ref];
      if (links !== undefined) {
        resolved[ref] = links;
      }
      else {
        unresolved.push(ref);
      }
    }

    // Nothing needs resolving so we can return right away.
    if (unresolved.length === 0) {
      return Promise.resolve(resolved);
    }

    // We fetch what is missing, and merge it into the resolved map.
    return ajax({
      url: this.fetchUrl,
      data: _.extend({
        paths: unresolved.join(";"),
        fields: this.fields,
      }, this.depthParams),
      headers: {
        Accept: "application/json",
      },
    }).then((response: SemanticFieldRaw[]) => {
      const exclude = this.excludeUrl;
      for (const field of response) {

        const key = field.path;
        //
        // We transform the responses to make them fit for this page:
        //
        let chained = _.chain(field.changerecords);

        // href may be undefined if we do not filter anything.
        if (exclude !== undefined) {
          // 1. Remove changerecords that link back here. This is going to
          // happen all the time because this article necessarily contains the
          // semantic field we are searching for. The REST interface does not
          // know or care that we do not want to link back to this article, so
          // we have to do this ourselves.

          chained = chained.filter(entry => entry.url !== exclude);
        }

        // 2. Order changerecords by ascending lemma, and descending datetime
        // (if datetime is present). Doing the ordering here allows the next
        // groupBy to have each lemma key have its values already ordered by
        // datetime.
        const newChangerecords: Record<string, ChangeRecord[]> = chained
          .orderBy(["lemma", "datetime"], ["asc", "desc"])
        // 3. Group by lemma so that we can hide long lists.
          .groupBy("lemma")
          .value();

        // 4. We create a tree that can be readily used for displaying with
        // $.treeview(...)
        const tree: TreeViewNode[] = [];
        for (const lemma of Object.keys(newChangerecords).sort()) {
          const changerecords = newChangerecords[lemma];
          const nodes = changerecords
            .map((entry): TreeViewNode => ({
              text: entry.datetime + (entry.published ? " published" : ""),
              href: entry.url,
              selectable: false,
            }));
          tree.push({
            text: lemma,
            href: changerecords[0].url,
            nodes,
            selectable: false,
          });
        }

        this.cache[key] = resolved[key] = {
          ...field,
          changerecords: newChangerecords,
          tree,
        };
      }

      return resolved;
    });
  }
}
