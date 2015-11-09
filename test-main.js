var allTestFiles = [];
var TEST_REGEXP = /_test\.js$/i;

function pathToModule(path) {
    if (/^\/base\/sitestatic\//.test(path))
        return path.replace(/^\/base\/sitestatic\//,
                            '../').replace(/\.js$/, '');
    else if (/^\/base\/karma_test\//.test(path)) {
        return path.replace(/^\/base\//,
                            '../../').replace(/\.js$/, '');
    }

    return path;
}

Object.keys(window.__karma__.files).forEach(function(file) {
  if (TEST_REGEXP.test(file)) {
    // Normalize paths to RequireJS module names.
    allTestFiles.push(pathToModule(file));
  }
});

require.config({
    baseUrl: '/base/sitestatic/lib/',

    // We need this so that the test files can find the files in "js".
    paths: {
        "js": "../js",
        "sinon": "../../node_modules/sinon/lib/sinon"
    },

    // We need these so that they behave nicely in testing.
    config: {
        'js/displayers': {
            test: true
        },
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


chaiAsPromised.transferPromiseness = function (assertion, promise) {
    assertion.then = promise.then.bind(promise);
    assertion.return = promise.return.bind(promise);
    assertion.catch = promise.catch.bind(promise);
};

// This makes things a bit more expensive than we'd like because we
// are loading all of wed. However, this method will work whether we
// are building BTW with optimized or non-optimized code, whereas
// using RequireJS' packages option would have to be used only when
// using optimized code, etc.
require(['bluebird', 'wed/wed'], function (bluebird) {
    bluebird.Promise.config({
        warnings: true,
        longStackTraces: true
    });
    require(allTestFiles, window.__karma__.start);
});
