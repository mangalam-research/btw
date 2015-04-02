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

  // Dynamically load all test files
  deps: allTestFiles,

  // Kickoff the tests.
  callback: window.__karma__.start
});
