import URI from "urijs/URI";
import _ from "lodash";

export default class SearchEngine {
  constructor(number) {
    this.results = this._makeSearchResults(number);
  }

  _makeSearchResults(number) {
    const ret = [];
    for (let i = 0; i < number; ++i) {
      ret.push({
        path: `01.${i}n`,
        heading: `heading ${i}`,
        parent: null,
        related_by_pos: [],
      });
    }
    return ret;
  }

  _makeSearchResponse(path, from, number) {
    let results = this.results;

    const count = results.length;
    results = results.slice(from, number + from);

    for (const result of results) {
      result.url = `${path}?paths=${result.path}`;
    }

    return {
      count,
      results,
      unfiltered_count: 1000, // Arbitrary.
    };
  }

  getResultByPath(path) {
    return _.find(this.results, (x) => x.path === path);
  }

  respond(request, query) {
    const uri = new URI(request.url);
    if (query === undefined) {
      query = uri.query(true);
    }
    const response = this._makeSearchResponse(uri.path(),
                                             +query.offset, +query.limit);
    request.respond(200, { "Content-Type": "application/json" },
                    JSON.stringify(response));
  }
}
