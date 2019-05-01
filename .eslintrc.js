module.exports = {
  extends: [
    "lddubeau-base/es5"
  ],
  rules: {
    "import/no-unresolved": "off",
    // eslint is unable to resolve the RequireJS dependencies...
    "import/no-extraneous-dependencies": "off",
    "import/no-webpack-loader-syntax": "off",
  },
  overrides: [{
    files: ["wed/wed.config.js"],
    parserOptions: {
      ecmaVersion: 6,
      sourceType: "module",
    },
    env: {
      node: true,
    }
  }],
};
