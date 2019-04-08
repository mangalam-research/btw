// eslint-disable-next-line import/no-dynamic-require
require(["jquery", "js-cookie", "jquery.growl"], function factory($, cookies) {
  "use strict";

  //
  // This library uses jquery.growl instead of bootstrap-notify (which is our
  // go-to notification library elsewhere). The reason for this is that
  // Bootstrap is not loaded in the administration views.
  //
  // It may be advantageous to load Bootstrap in admin views but it requires
  // careful consideration.
  //

  $(function ready() {
    var csrftoken = cookies.get("csrftoken");
    $(".lexicography-revert").click(function onClick() {
      $.ajax({
        type: "POST",
        url: $(this).attr("href"),
        headers: {
          "X-CSRFToken": csrftoken,
        },
      }).done(function done() {
        $.growl.notice({
          message: "The entry was reverted.",
          location: "tc",
        });
      }).fail(function fail() {
        $.growl.error({
          message: "Could not revert the entry, probably because it is locked.",
          location: "tc",
        });
      });
      return false;
    });

    $(".lexicography-delete, .lexicography-undelete")
      .click(function onClick(ev) {
        var delete_ = ev.target.classList.contains("lexicography-delete");
        $.ajax({
          type: "POST",
          url: $(this).attr("href"),
          headers: {
            "X-CSRFToken": csrftoken,
          },
        }).done(function done() {
          $.growl.notice({
            message: "The entry was " + delete_ ? "deleted" : "undeleted",
            location: "tc",
          });
        }).fail(function fail() {
          $.growl.error({
            message: "Could not act on the entry, " +
              "probably because it is locked.",
            location: "tc",
          });
        });
        return false;
      });
  });
});
