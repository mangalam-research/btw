// Karma configuration
// Generated on Thu Apr 02 2015 07:49:34 GMT-0400 (EDT)
/* eslint-env node, commonjs */
/* global module */
"use strict";

module.exports = function configure(config) {
  config.set({
    basePath: "",
    frameworks: ["requirejs", "mocha", "chai-as-promised", "chai", "fixture"],
    client: {
      mocha: {
        asyncOnly: true,
        grep: config.grep,
      },
    },
    files: [
      "sitestatic/config/requirejs-config-dev.js",
      "test-main.js",
      { pattern: "sitestatic/lib/**/*.html", included: false },
      { pattern: "build/test-data/**/*", included: false },
      { pattern: "sitestatic/lib/**/*.js", included: false },
      { pattern: "sitestatic/js/**/*.js", included: false },
      { pattern: "karma_tests/**/*.js", included: false },
      { pattern: "semantic_fields/karma_tests/**/*.js", included: false },
      { pattern: "lexicography/karma_tests/**/*.js", included: false },
      { pattern: "lexicography/templates/lexicography/viewer.html" },
      { pattern: "node_modules/sinon/lib/**/*.js", included: false },
    ],
    exclude: [],
    preprocessors: {
      "**/karma_tests/*.html": ["html2js"],
      "**/templates/**/*.html": ["html2js"],
      "**/karma_tests/*.json": ["json_fixtures"],
    },
    reporters: ["mocha"],
    port: 9876,
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: true,
    browsers: ["Chrome"],
    singleRun: false,
  });
};
