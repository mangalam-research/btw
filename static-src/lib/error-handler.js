define(['jquery', 'last-resort', 'bootstrap'], function ($, last_resort) {

var $modal = $(
        '\
<div class="modal btw-fatal-modal" style="position: absolute" tabindex="1">\
  <div class="modal-dialog">\
    <div class="modal-content">\
      <div class="modal-header">\
        <button type="button" class="close" data-dismiss="modal"\
aria-hidden="true">&times;</button>\
        <h3>Fatal Error</h3>\
      </div>\
      <div class="modal-body">\
      </div>\
      <div class="modal-footer">\
        <a href="#" class="btn btn-primary" data-dismiss="modal">Reload</a>\
      </div>\
    </div>\
  </div>\
</div>');

var modal = $modal[0];

var onerror = last_resort.setOnError(window, { force: true,
                                               noChaining: true });
onerror.register(function (ev) {
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
            if (reason.stack)
                msg += "\n" + reason.stack;
            else
                msg += reason;
        }
        else if (promise) {
            msg += "Promise: " + promise;
        }
    }

    console.log(msg);

    document.body.appendChild(modal);
    modal.getElementsByClassName("modal-body")[0].innerHTML =
        '<p>A fatal error occurred.</p><pre></pre>';
    var log = modal.getElementsByTagName("pre")[0];
    log.textContent = msg;
    $modal.on("hide.bs.modal.modal", function () {
        modal.parentNode.removeChild(modal);
        window.location.reload();
    });
    $modal.modal();
});


});
