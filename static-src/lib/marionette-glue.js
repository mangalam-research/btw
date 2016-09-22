define(function factory(require) {
  "use strict";

  var Mn = require("marionette");
  var Bb = require("backbone");

  Mn.View.prototype.serializeModel = function serializeModel() {
    if (!this.model) {
      return {};
    }

    return this.model.toJSON();
  };

  Mn.View.prototype.serializeCollection = function serializeCollection() {
    if (!this.collection) {
      return {};
    }

    return this.collection.toJSON();
  };

  if (window.__agent) {
    window.__agent.start(Bb, Mn);
  }

  return Mn;
});
