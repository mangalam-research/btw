// eslint-disable-next-line import/no-extraneous-dependencies
import _ from "lodash";
import { Server } from "./server";

const fetcherUrlRe = /^\/en-us\/semantic-fields\/semanticfield\/(.*)$/;

export class FetcherServer extends Server {
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
      const pathsString = new URL(request.url, "http://fake")
            .searchParams.get("paths");
      if (!pathsString) {
        return;
      }
      const paths = pathsString.split(";");
      const response = paths.map(
        path => ({
          path,
          heading: "semantic field foo",
          parent: undefined,
          changerecords: this.changeRecords,
        }));
      request.respond(200, { "Content-Type": "application/json" },
                      JSON.stringify(response));
    }
  }
}
