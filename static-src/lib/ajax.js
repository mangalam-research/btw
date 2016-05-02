define(['jquery', 'bluejax', 'jquery.cookie', 'bootstrap'],
       function ($, bluejax) {
'use strict';

var $modal = $(
        '\
<div class="modal btw-fatal-modal" style="position: absolute" tabindex="1">\
  <div class="modal-dialog">\
    <div class="modal-content">\
      <div class="modal-header">\
        <button type="button" class="close" data-dismiss="modal"\
aria-hidden="true">&times;</button>\
        <h3>Connectivity Problem</h3>\
      </div>\
      <div class="modal-body">\
        <p>We have detected a connectivity problem: \
           <span class="reason"></span>.</p>\
        <p>When you click the Ok button, we will recheck the connectivity. \
           If there is still a problem, this dialog will remain. Otherwise, \
           the window will be reloaded. If you were modifying information \
           on the \
           site when the outage occurred, please verify that what you were \
           trying to do actually happened.</p>\
      </div>\
      <div class="modal-footer">\
        <a href="#" class="btn btn-primary" data-dismiss="modal">Ok</a>\
      </div>\
    </div>\
  </div>\
</div>');

var modal = $modal[0];

var base_opts = {
    tries: 3,
    delay: 100,
    diagnose: {
        on: true,
        serverURL: "/ping",
        knownServers: [
            "http://www.google.com/",
            "http://www.cloudfront.com/"
        ]
    }
};

var ajax = bluejax.make(base_opts);

var diagnose = bluejax.make({
    diagnose: {
        on: true,
        knownServers: base_opts.diagnose.knownServers
    }
});

var csrftoken = $.cookie("csrftoken");

return function (settings) {
    if (arguments.length > 1) {
        throw new Error(
            "we do not support passing the url as a separate argument; " +
            "please use a single settings argument");
    }

    var headers = settings.headers = settings.headers || {};
    headers['X-CSRFToken'] = csrftoken;

    var ret = ajax.call(this, settings)
        .catch(bluejax.ConnectivityError, function (err) {
            document.body.appendChild(modal);
            var reason = modal.querySelector("span.reason");
            reason.textContent = err.message;
            $modal.on("hide.bs.modal.modal", function (ev) {
                ev.stopPropagation();
                ev.preventDefault();
                diagnose(base_opts.diagnose.serverURL).then(function () {
                    window.location.reload();
                }).suppressUnhandledRejections();
            });
            $modal.modal();

            // Cancelling the promise is something that Bluebird
            // provides. It allows us to handle the exception here
            // while at the same time declaring that no future
            // handlers should be run.
            ret.cancel();
        });
    return ret;
};

});
