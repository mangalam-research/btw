define(['velocity', 'bluebird', 'jquery'], function (velocity, bluebird) {

//
// When we use velocity-ui, which we do in this project, then velocity **must**
// depend on jQuery. Why? The problem is the way velocity and velocity-ui
// initialize their ``global`` object. Both do ``(window.jQuery || window.Zepto
// || window)``. However, if jQuery is used in a project it is possible to have
// the following sequence:
//
// 1. velocity loads: ``global`` is ``window``.
//
// 2. jQuery loads.
//
// 3. velocity-ui loads: ``global`` is ``window.jQuery``.
//

// Make velocity use bluebird all the time.
velocity.Promise = bluebird.Promise;

return velocity;

});
