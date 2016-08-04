export function detailURLFromId(id) {
  return `http://localhost/en-us/semantic-fields/semanticfield/${id}/`;
}

export function queryURLFromDetailURL(url) {
  return `${url}?fields=%40details&depths.parent=-1&depths.related_by_pos=1` +
    "&depths.children=1";
}
