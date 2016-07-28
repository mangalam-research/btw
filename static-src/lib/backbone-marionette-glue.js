define(["backbone", "marionette"], function factory(Bb, Mn) {
  "use strict";
  if (window.__agent) {
    window.__agent.start(Bb, Mn);
  }
  return Mn;
});
