define(function factory(require, _exports, module) {
  "use strict";
  var Bb = require("backbone");
  require("backbone-marionette-glue");

  if (module.config().debug) {
    // We patch setElement so that we can grab an element's view from
    // the DOM.
    var originalSetElement = Bb.View.prototype.setElement;

    Bb.View.prototype.setElement = function setElement(element) {
      if (this.el && this.el !== element) {
        delete this.el.backboneView;
      }

      element.backboneView = this;
      element.setAttribute("data-backbone-view", "");

      return originalSetElement.apply(this, arguments);
    };
  }

  return Bb;
});
