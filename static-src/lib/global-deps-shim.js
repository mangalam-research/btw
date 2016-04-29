(function () {
    var require = window.require;
    function dep_require(deps, fn) {
        require(["error-handler"], function () {
            require(deps, fn);
        });
    }

    for (var x in require) {
        dep_require[x] = require[x];
    }

    window.require = dep_require;

    // There is no way to override define to allow a define to
    // automatically trigger the loading of a module. RequireJS expect
    // define to execute synchronously, so we cannot wrap it in a
    // require call. We cannot wrap the function in it in a require
    // call either. Adding to the list of dependencies won't do
    // because it does not guarantee an order.
})();
