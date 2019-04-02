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
      "node_modules/babel-polyfill/dist/polyfill.js",
      {
        pattern: "sitestatic/lib/**/@(*.html|*.hbs|*.js|*.json)",
        included: false,
      },
      { pattern: "sitestatic/js/**/*.js", included: false },
      { pattern: "build/test-data/**/*", included: false },
      { pattern: "karma_tests/**/*.js", included: false },
      { pattern: "karma_tests/**/*.json" },
      { pattern: "semantic_fields/karma_tests/**/*.js", included: false },
      { pattern: "lexicography/karma_tests/**/*.js", included: false },
      { pattern: "lexicography/templates/lexicography/viewer.html" },
      { pattern: "node_modules/sinon/pkg/**/*.js", included: false },
    ],
    exclude: [],
    preprocessors: {
      "**/karma_tests/*.html": ["html2js"],
      "**/templates/**/*.html": ["html2js"],
      "**/karma_tests/**/*.json": ["json_fixtures"],
      "karma_tests/lib/btw/semantic_field_editor/**/*.js": ["babelModule"],
      "karma_tests/lib/testutils/**/*.js": ["babelModule"],
    },
    jsonFixturesPreprocessor: {
      variableName: "__json__",
    },
    customPreprocessors: {
      babelModule: {
        base: "babel",
        options: {
          plugins: ["transform-es2015-modules-amd"],
        },
      },
    },
    babelPreprocessor: {
      options: {
        presets: ["es2015"],
        ignore: [
          "node_modules",
        ],
        sourceMap: "inline",
      },
      filename: function filename(file) {
        return file.originalPath.replace(/\.js$/, ".es5.js");
      },
      sourceFileName: function sourceFileName(file) {
        return file.originalPath;
      },
    },
    // reporters: ["mocha"],
    port: 9876,
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: true,
    browsers: ["ChromeHeadless"],
    singleRun: false,
  });
};
