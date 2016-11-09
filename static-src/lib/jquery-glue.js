define(function jqueryGlue(require) {
  "use strict";
  var $ = require("jquery");

  $.noConflict();

  var originalAjax = $.ajax;
  var ajax;

  // This rigmarole is needed because we are dealing with a circular
  // dependency. In order to benefit from the services of Bluejax we must: a)
  // load ``ajax``, which depends on ``bluejax``, which depends in ``jquery``,
  // which brings us back here. (``ajax`` calls on ``jquery`` directly too but
  // splitting it into a library that only provides ajax calls (so does not
  // directly load ``jquery``) and a library that provides the GUI would not
  // solve the problem because the loop above would remain.) So we require
  // ``ajax`` like this and save the return value. There is a small window of
  // time at initial loading whereby it would be possible to have to handle a
  // call with bluejaxOptions set, but with `ajax` not loaded yet. This does not
  // seem likely though.
  require(["ajax"], function ajaxLoaded(_ajax) {
    ajax = _ajax;
  });

  // This is pretty simple. If ``$.ajax`` is called without settings or with an
  // settings object that does not contain bluejaxOptions, then just call the
  // old stock ``$.ajax``. Otherwise, we call our own ``ajax.ajax$`` function
  // and return the xhr produced from it.
  $.ajax = function overridenjQueryAjax(url, settings) {
    var origArgs;
    if (settings === undefined) {
      settings = url;
      origArgs = [url];
    }
    else {
      origArgs = [url, settings];
    }

    if ((typeof settings === "object") && settings.useBluejax) {
      delete settings.useBluejax;

      if (ajax && ajax.ajax$) {
        return ajax.ajax$.apply(ajax, origArgs).xhr;
      }

      // eslint-disable-next-line no-console
      console.warn("received a call with useBluejax set but the " +
                   "ajax module is not yet loaded: using stock $.ajax");
    }

    return originalAjax.apply($, origArgs);
  };

  return $;
});
