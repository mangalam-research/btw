import sinon from "sinon";
// eslint-disable-next-line import/no-extraneous-dependencies
import _ from "lodash";

export class Server {
  constructor(options) {
    const fixture = this.fixture = options.fixture;
    this.verboseServer = !!options.verboseServer;

    const server = this.server = sinon.fakeServer.create();
    this.responseMap = _.mapValues(fixture, value => JSON.stringify(value));
    server.respondWith(this.verboseWrap.bind(this));
    server.autoRespond = true;
    server.autoRespondAfter = 1;
  }

  verboseWrap(request) {
    const { verboseServer } = this;
    if (verboseServer) {
      // eslint-disable-next-line no-console
      console.log("REQUEST:", request.method, request.url);
    }
    this.respond(request);
    if (request.status !== 200) {
      request.respond(404, { "Content-Type": "text/html" },
                      "");
    }

    if (verboseServer) {
      // eslint-disable-next-line no-console
      console.log("RESPONSE:", request.status, request.response);
    }
  }

  respond(request) {
    if (request.method !== "GET") {
      return;
    }
    const response = this.responseMap[request.url];
    if (response) {
      request.respond(200, { "Content-Type": "application/json" },
                      response);
    }
  }

  restore() {
    this.server.restore();
  }
}
