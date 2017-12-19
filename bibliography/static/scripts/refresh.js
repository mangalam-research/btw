define(["jquery", "jquery.cookie", "jquery.bootstrap-growl"], function r($) {
  "use strict";

  return function refresh(initiateUrl, checkUrl) {
    var span = document.getElementById("btw-prev-refreshed");
    var tableEl = document.getElementById("bibliography-table");
    var button = document.getElementById("btw-refresh");
    var icon = button.getElementsByTagName("i")[0];
    var csrftoken = $.cookie("csrftoken");

    function working() {
      icon.classList.add("fa-spin");
      button.disabled = true;
    }

    function idle() {
      icon.classList.remove("fa-spin");
      button.disabled = false;
    }

    function growl(message, type) {
      $.bootstrapGrowl(message, {
        ele: "body",
        type: type,
        offset: { from: "top", amount: 20 },
        align: "center",
        width: "auto",
        delay: 4000,
        allow_dismiss: true,
        stackup_spacing: 10,
      });
    }

    function failed() {
      idle();
      growl("Refresh failed. Please contact technical support.", "danger");
    }

    $(button).on("click", function click() {
      working();
      $.ajax({
        url: initiateUrl,
        type: "POST",
        headers: {
          "X-CSRFToken": csrftoken,
          Accept: "application/json",
        },
      }).done(function done(data) {
        var last = data;
        function check() {
          $.ajax({
            url: checkUrl,
            type: "GET",
            headers: {
              Accept: "application/json",
            },
          }).done(function doneCheck(checkData) {
            var now = checkData;
            if (now === last) {
              setTimeout(check, 500);
            }
            else {
              idle();
              span.textContent = checkData;
              var table = $.data(tableEl, "title-table");
              if (table) {
                table.fnDraw();
              }
              growl("Refreshed!", "success");
            }
          }).fail(failed);
        }
        check();
      }).fail(failed);
    });
  };
});
