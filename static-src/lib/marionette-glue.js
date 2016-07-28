define(function factory(require) {
  "use strict";

  var _ = require("underscore");
  var Mn = require("marionette");
  var Radio = require("backbone.radio");
  require("backbone-marionette-glue");

  // Patch Application to use Radio.
  Mn.Application.prototype._initChannel = function _initChannel() {
    this.channelName = _.result(this, "channelName") || "global";
    this.channel = _.result(this, "channel") || Radio.channel(this.channelName);
  };
  return Mn;
});
