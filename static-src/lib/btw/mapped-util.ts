import * as domutil from "wed/domutil";
import { GUISelector } from "wed/gui-selector";
import * as util from "wed/util";

export class MappedUtil {
  constructor(private readonly mapping: Record<string, string>) {}

  toGUISelector(selector: string): string {
    return domutil.toGUISelector(selector, this.mapping);
  }

  classFromOriginalName(name: string): string {
    return util.classFromOriginalName(name, this.mapping);
  }

  dataFindAll(el: Element, selector: string): Element[] {
    return domutil.dataFindAll(el, selector, this.mapping);
  }

  makeGUISelector(selector: string): GUISelector {
    return GUISelector.fromDataSelector(selector, this.mapping);
  }
}
