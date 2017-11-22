import { Meta as TEIMeta } from "wed/modes/generic/metas/tei_meta";
import * as util from "wed/util";

class BTWMeta extends TEIMeta {
  private cachedMapping: Record<string, string>;

  // tslint:disable-next-line:no-any
  constructor(...args: any[]) {
    super(...args);
  }

  isInline(node: Node): boolean {
    // We need to normalize the name to fit the names we have below.
    const originalName = util.getOriginalName(node);
    const parts = originalName.split(":");
    // XXX this is taking a shortcut. We should instead find the namespace of
    // the node and convert it to an appropriate prefix to use below.
    if (parts.length === 1) {
      parts[1] = parts[0];
      parts[0] = "tei";
    }
    const name = parts.join(":");

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
      if (node.parentNode !== null &&
          util.getOriginalName(node.parentNode) === "btw:citations") {
        return false;
      }
      /* falls through */
    default:
      return super.isInline(node);
    }
  }

  getNamespaceMappings(): Record<string, string> {
    // BTW's mapping is identical to TEI's but with the addition of the "btw"
    // prefix.
    if (this.cachedMapping !== undefined) {
      return this.cachedMapping;
    }

    const ret = {
      ...super.getNamespaceMappings(),
      // tslint:disable-next-line:no-http-string
      btw: "http://mangalamresearch.org/ns/btw-storage",
    };
    this.cachedMapping = ret;
    return ret;
  }
}

export { BTWMeta as Meta };
