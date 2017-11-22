/**
 * Bibliographical structures.
 * @author Louis-Dominique Dubeau
 */

export interface Item {
  pk: number;
  date: string;
  title: string;
  creators: string;
  zotero_url: string;
  url: string;
  abstract_url: string;
}

export interface PrimarySource {
  pk: number;
  reference_title: string;
  genre: string;
  item: Item;
}

export type BibliographicalItem = Item | PrimarySource;

export function isPrimarySource(datum: BibliographicalItem):
datum is PrimarySource {
  return (datum as PrimarySource).item !== undefined;
}

export function biblSuggestionSorter(array: BibliographicalItem[]):
BibliographicalItem[] {
  const itemPkToPss: Record<string, PrimarySource[]> = Object.create(null);
  const items: Item[] = [];

  // Separate items (secondary sources) and primary sources.
  for (const it of array) {
    if (!isPrimarySource(it)) {
      items.push(it);
    }
    else {
      let l = itemPkToPss[it.item.pk];
      if (l === undefined) {
        l = itemPkToPss[it.item.pk] = [];
      }
      l.push(it);
    }
  }

  items.sort((a, b) => {
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

  function sortPss(a: PrimarySource, b: PrimarySource): -1 | 1 {
    // We don't bother with 0 since it is not possible to
    // have two identical reference titles.
    return (a.reference_title < b.reference_title) ? -1 : 1;
  }

  let sortedByItem: BibliographicalItem[] = [];
  for (const it of items) {
    const l = itemPkToPss[it.pk];
    if (l !== undefined) {
      l.sort(sortPss);
      sortedByItem = sortedByItem.concat(l);
      delete itemPkToPss[it.pk];
    }
    sortedByItem.push(it);
  }

  // Any remaining primary sources in itemPkToPss get to the front.
  let pss: PrimarySource[] = [];
  for (const key of Object.keys(itemPkToPss)) {
    pss = pss.concat(itemPkToPss[key]);
  }

  pss.sort(sortPss);

  return (pss as BibliographicalItem[]).concat(sortedByItem);
}

export function biblDataToReferenceText(data: BibliographicalItem): string {
  let text = "";
  if (isPrimarySource(data)) {
    text = data.reference_title;
  }
  else {
    const creators = data.creators;
    text = "***ITEM HAS NO CREATORS***";
    if (creators != null && creators !== "") {
      text = creators.split(",")[0];
    }

    if (data.date != null && data.date !== "") {
      text += `, ${data.date}`;
    }
  }
  return text;
}
