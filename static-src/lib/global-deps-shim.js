(function shim() {
  "use strict";

  var require = window.require;
  function depRequire(deps, fn) {
    // eslint-disable-next-line import/no-dynamic-require
    require(["error-handler"], function handlerLoaded() {
      // eslint-disable-next-line import/no-dynamic-require
      require(deps, fn);
    });
  }

  // eslint-disable-next-line guard-for-in
  for (var x in require) {
    depRequire[x] = require[x];
  }

  window.require = depRequire;

  // There is no way to override define to allow a define to automatically
  // trigger the loading of a module. RequireJS expect define to execute
  // synchronously, so we cannot wrap it in a require call. We cannot wrap the
  // function in it in a require call either. Adding to the list of dependencies
  // won't do because it does not guarantee an order.
}());
