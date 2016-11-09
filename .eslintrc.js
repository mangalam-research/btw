module.exports = {
  extends: [
    "lddubeau-base/es5"
  ],
  rules: {
    "import/no-unresolved": "off",
    // eslint is unable to resolve the RequireJS dependencies...
    "import/no-extraneous-dependencies": "off",
  }
};
