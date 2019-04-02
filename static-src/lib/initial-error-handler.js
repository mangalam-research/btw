/* global LastResort */
(function errorHandler() {
  "use strict";

  // This is a minimalistic error handler meant to be loaded ASAP
  // and that depends on nothing, except last-resort having been
  // loaded through a script tag.
  var oe = LastResort.install(window);
  oe.register(function handler(ev) {
    var msg = "";
    if (ev.type === "error") {
      var message = ev.message;
      var filename = ev.filename;
      var lineno = ev.lineno;
      var colno = ev.colno;
      var err = ev.error;
      if (err) {
        msg = err.stack;
      }
      else {
        msg = filename + ":" + lineno;
        if (colno) {
          msg += "." + colno;
        }
        msg += ": " + message;
      }
    }
    else {
      msg += "Unhandled promise rejection!\n";
      var reason;
      var promise;
      var source = ev.promise ? ev : ev.detail;
      if (source) {
        reason = source.reason;
        promise = source.promise;
      }

      if (reason) {
        msg += "Reason: ";
        if (reason.stack) {
          msg += "\n" + reason.stack;
        }
        else {
          msg += reason;
        }
      }
      else if (promise) {
        msg += "Promise: " + promise;
      }
    }

    // eslint-disable-next-line no-console
    console.log(msg);

    // eslint-disable-next-line no-alert
    alert(msg);
    window.location.reload();
  });
}());
