// This top-level function is purposely written so that it does not need jQuery
// or similar libraries.
(function startWed(require) {
  "use strict";

  if (require === undefined) {
    // We assume that wed is ALREADY defined as a global symbol
    // through other means. It is up to whatever caused this code
    // to be used to set the environment so that wed exists and
    // has the appropriate value.
    require = function fakeRequire(dummy, f) {
      return f(wed, $); // eslint-disable-line no-undef
    };
  }

  function init() {
    // eslint-disable-next-line import/no-dynamic-require
    require(
      ["btw/btw-editor", "jquery", "last-resort", "wed/onerror", "btw/btw-wed-config",
       "jquery.cookie"],
      function loaded(btwEditor, $, lr, onerror, btwWedConfig) {
        var onError = lr.install(window, { force: true });
        onError.register(onerror.handler);

        var widgets = document.getElementsByClassName("wed-widget");

        for (var i = 0; i < widgets.length; i++) {
          var widget = widgets[i];
          var script = widget.nextElementSibling;
          if (script.tagName !== "SCRIPT") {
            throw new Error("script element for data not found!");
          }
          var $widget = $(widget);

          var options = btwWedConfig.config || {};

          var csrftoken = $.cookie("csrftoken");
          var $parentform = $widget.parents("form").first();

          options.mode.options.semanticFieldFetchUrl =
            $parentform.find("#id_sf_fetch_url").val();
          options.ajaxlog = {
            url: $parentform.find("#id_logurl").val(),
            headers: {
              "X-CSRFToken": csrftoken,
            },
          };
          options.save = {
            path: "wed/savers/ajax",
            options: {
              url: $parentform.find("#id_saveurl").val(),
              headers: {
                "X-CSRFToken": csrftoken,
              },
              initial_etag: $parentform.find("#id_initial_etag").val(),
            },
          };

          // eslint-disable-next-line camelcase
          var wed_editor = btwEditor.makeEditor(widget, options);
          // Yep, this means only one wed editor per window.
          // eslint-disable-next-line camelcase
          window.wed_editor = wed_editor;
          // eslint-disable-next-line no-loop-func
          wed_editor.init(script.textContent).then(function initialized() {
            $widget.prev().remove();

            // Allow CSS to reflow
            window.setTimeout(wed_editor.resize.bind(wed_editor), 0);
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
}((typeof require === "undefined") ? undefined : require));
