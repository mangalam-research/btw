define(["jquery", "last-resort", "bootstrap"], function module($, lastResort) {
  "use strict";

  var $modal = $(
    "\
<div class='modal btw-fatal-modal' style='position: fixed; top: 0; left: 0' \
     tabindex='1'>\
  <div class='modal-dialog'>\
    <div class='modal-content'>\
      <div class='modal-header'>\
        <button type='button' class='close' data-dismiss='modal'\
aria-hidden='true'>&times;</button>\
        <h3>Fatal Error</h3>\
      </div>\
      <div class='modal-body'>\
      </div>\
      <div class='modal-footer'>\
        <a href='#' class='btn btn-primary' data-dismiss='modal'>Reload</a>\
      </div>\
    </div>\
  </div>\
</div>");

  var modal = $modal[0];

  var onerror = lastResort.install(window, { force: true });
  onerror.register(function handler(ev) {
    // eslint-disable-next-line no-console
    console.log("error-handler: caught an unhandled error!");

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

    document.body.appendChild(modal);
    modal.getElementsByClassName("modal-body")[0].innerHTML =
        "<p>A fatal error occurred.</p><pre></pre>";
    var log = modal.getElementsByTagName("pre")[0];
    log.textContent = msg;
    $modal.on("hide.bs.modal.modal", function hidden() {
      modal.parentNode.removeChild(modal);
      window.location.reload();
    });
    $modal.modal();
  });
});
