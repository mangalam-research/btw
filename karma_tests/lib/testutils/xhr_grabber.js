import sinon from "sinon";

export default class XHRGrabber {
  constructor() {
    this.requests = [];
    const xhr = this.xhr = sinon.useFakeXMLHttpRequest();
    xhr.onCreate = function onCreate(request) {
      this.requests.push(request);
    }.bind(this);
  }

  hasRequests() {
    return this.requests.length > 0;
  }

  getSingleRequest() {
    const requests = this.requests;
    if (requests.length !== 1) {
      throw new Error(`expected a single request; `
                      `the number of requests is: ${requests.length}`);
    }

    return requests[0];
  }

  clear() {
    this.requests = [];
  }

  restore() {
    this.xhr.restore();
  }
}
