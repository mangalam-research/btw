define(["bluebird"], function module(bluebird) {
  "use strict";

  // We need cancellation for error handling. See ajax.js
  bluebird.config({
    cancellation: true,
  });

  return bluebird;
});
