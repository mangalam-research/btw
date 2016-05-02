define(['bluebird'], function (bluebird) {

// We need cancellation for error handling. See ajax.js
bluebird.config({
    cancellation: true
});

return bluebird;
});
