function pathToModule(path) {
  "use strict";
  var module = path;
  if (/^\/base\/sitestatic\//.test(path)) {
    module = path.replace(/^\/base\/sitestatic\//, "../");
  }
  else if (/^\/base\/karma_tests\/lib\/testutils\//.test(path)) {
    module = path.replace(/^\/base\/karma_tests\/lib\//, "");
  }
  else if (/^\/base\/karma_tests\//.test(path)) {
    module = path.replace(/^\/base\//, "");
  }

  return module.replace(/\.(es5)?\.js$/, "");
}

var paths = {
  js: "../js",
  sinon: "../../node_modules/sinon/lib/sinon",
  Squire: "../../node_modules/squirejs/src/Squire",
};
var allTestModules = [];
var TEST_REGEXP = /_test$/i;
Object.keys(window.__karma__.files).forEach(function filterTests(file) {
  "use strict";
  var moduleName = pathToModule(file);
  if (TEST_REGEXP.test(moduleName)) {
    // Normalize paths to RequireJS module names.
    allTestModules.push(moduleName);
  }

  if (/.es5.js$/.test(file)) {
    paths[moduleName] = file.slice(0, -3);
  }
});

require.config({
  baseUrl: "/base/sitestatic/lib/",

  paths: paths,

  // We need these so that they behave nicely in testing.
  config: {
    "js/displayers": {
      test: true,
    },
  },
});

/* global chaiAsPromised */
chaiAsPromised.transferPromiseness = function transferPromiseness(assertion,
                                                                  promise) {
  "use strict";
  assertion.then = promise.then.bind(promise);
  assertion.return = promise.return.bind(promise);
  assertion.catch = promise.catch.bind(promise);
};

// This makes things a bit more expensive than we'd like because we are loading
// all of wed. However, this method will work whether we are building BTW with
// optimized or non-optimized code, whereas using RequireJS' packages option
// would have to be used only when using optimized code, etc.
require(["bluebird", "wed"], function init(bluebird) {
  "use strict";
  bluebird.Promise.config({
    warnings: true,
    longStackTraces: true,
  });

  // eslint-disable-next-line global-require
  require(allTestModules, window.__karma__.start.bind(window.__karma__,
                                                      window.__karma__.config));
});
