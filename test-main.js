var allTestFiles = [];
var TEST_REGEXP = /_test\.js$/i;

function pathToModule(path) {
  return path.replace(/^\/base\/build\/static-build\//, '../').replace(/\.js$/, '');
}

Object.keys(window.__karma__.files).forEach(function(file) {
  if (TEST_REGEXP.test(file)) {
    // Normalize paths to RequireJS module names.
    allTestFiles.push(pathToModule(file));
  }
});

require.config({
    baseUrl: '/base/build/static-build/lib/',
    // We need these so that they behave nicely in testing.
    config: {
        'wed/log': {
            focus_popup: true // For testing only.
        },
        'wed/onerror': {
            suppress_old_onerror: true, // For testing only.
            test: true // For testing only.
        },
        'wed/onbeforeunload': {
            test: true // For testing only
        }
    }
});

// This makes things a bit more expensive than we'd like because we
// are loading all of wed. However, this method will work whether we
// are building BTW with optimized or non-optimized code, whereas
// using RequireJS' packages option would have to be used only when
// using optimized code, etc.
require(['wed/wed'], function () {
  require(allTestFiles, window.__karma__.start);
});
