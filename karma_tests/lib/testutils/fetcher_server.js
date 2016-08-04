import Server from "./server";
import _ from "lodash";
import URI from "urijs/URI";

const fetcherUrlRe = /^\/en-us\/semantic-fields\/semanticfield\/(.*)$/;

export default class FetcherServer extends Server {

  constructor(options) {
    super(_.omit(options, ["fetcherUrlRe"]));
    this.fetcherUrlRe = options.fetcherUrlRe || fetcherUrlRe;
  }

  setChangeRecords(changeRecords) {
    this.changeRecords = changeRecords;
  }

  respond(request) {
    super.respond(request);
    // Already responded.
    if (request.status === 200) {
      return;
    }

    // No match.
    if (request.method === "GET" && this.fetcherUrlRe.test(request.url)) {
      const query = new URI(request.url).query(true);
      if (!query.paths) {
        return;
      }
      const paths = query.paths.split(";");
      const response = paths.map(
        path => ({
          path,
          heading: "semantic field foo",
          parent: undefined,
          changerecords: this.changeRecords,
        }));
      request.respond(200, { "Content-Type": "application/json" },
                      JSON.stringify(response));
      return;
    }
  }
}
