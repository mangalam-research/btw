// Karma configuration
// Generated on Thu Apr 02 2015 07:49:34 GMT-0400 (EDT)

module.exports = function(config) {
    config.set({
        basePath: '',
        frameworks: ['requirejs', 'mocha', 'chai-as-promised', 'chai'],
        files: [
            'sitestatic/config/requirejs-config-dev.js',
            'test-main.js',
            {pattern: 'sitestatic/lib/**/*.js', included: false},
            {pattern: 'sitestatic/js/**/*.js', included: false},
            {pattern: 'karma_tests/**/*.js', included: false},
            {pattern: 'semantic_fields/karma_tests/**/*.js', included: false},
            {pattern: 'node_modules/sinon/lib/**/*.js', included: false}
        ],
        exclude: [],
        preprocessors: {},
        reporters: ['progress'],
        port: 9876,
        colors: true,
        logLevel: config.LOG_INFO,
        autoWatch: true,
        browsers: ['Chrome'],
        singleRun: false
    });
};
