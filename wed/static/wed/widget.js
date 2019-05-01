(function startWed() {
  "use strict";

  function init() {
    // eslint-disable-next-line import/no-dynamic-require, global-require
    require(
      ["wed", "last-resort", "js-cookie"],
      function loaded(btwEditor, lr, cookies) {
        var onError = lr.install(window, { force: true });
        onError.register(btwEditor.onerror.handler);

        var widgets = document.getElementsByClassName("wed-widget");

        var csrftoken = cookies.get("csrftoken");
        for (var i = 0; i < widgets.length; i++) {
          var widget = widgets[i];
          var script = widget.nextElementSibling;
          if (script.tagName !== "SCRIPT") {
            throw new Error("script element for data not found!");
          }

          var parentform = widget.closest("form");

          var options = {
            schema: require.toUrl("btw/btw-storage.rng"),
            mode: {
              path: "btw/btw-mode",
              options: {
                bibl_url: "/rest/bibliography/all",
                semanticFieldFetchUrl:
                parentform.querySelector("#id_sf_fetch_url").value,
              },
            },
          };

          options.ajaxlog = {
            url: parentform.querySelector("#id_logurl").value,
            headers: {
              "X-CSRFToken": csrftoken,
            },
          };

          var saverOptions = {
            url: parentform.querySelector("#id_saveurl").value,
            headers: {
              "X-CSRFToken": csrftoken,
              "X-Requested-With": "XMLHttpRequest",
            },
            initial_etag: parentform.querySelector("#id_initial_etag").value,
          };

          btwEditor.load(widget, options, saverOptions, script.textContent)
          // eslint-disable-next-line no-loop-func
            .then(function initialized(wed) {
              // Yep, this means only one wed editor per window.
              window.wed_editor = wed;
              widget.previousElementSibling.remove();
              // Allow CSS to reflow
              window.setTimeout(wed.resize.bind(wed), 0);
            });
        }
      });
  }

  if (window.addEventListener) { // DOM
    window.addEventListener("load", init);
  }
  else if (window.attachEvent) { // IE
    window.attachEvent("onload", init);
  }
}());
