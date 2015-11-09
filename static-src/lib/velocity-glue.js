define(['velocity', 'bluebird'], function (velocity, bluebird) {

// Make velocity use bluebird all the time.
velocity.Promise = bluebird.Promise;

return velocity;

});
