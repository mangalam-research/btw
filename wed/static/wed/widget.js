// This code is purposely written without using jQuery or similar
// libraries.
(function(require) {
    if (require === undefined) {
        // We assume that wed is ALREADY defined as a global symbol
        // through other means. It is up to whatever caused this code
        // to be used to set the environment so that wed exists and
        // has the appropriate value.
        require = function (dummy, f) { return f(wed); };
    }

    function init() {
        require(["wed/wed", "jquery"], function (wed, $) {
            var widgets = document.getElementsByClassName('wed-widget');

            for (var i = 0; i < widgets.length; i++) {
                var widget = widgets[i];

                var options = (typeof wed_config === 'object') ?
                    wed_config : undefined;

                var wed_editor = new wed.Editor();
                wed_editor.init(widget, options);
                wed_editor.whenCondition("first-validation-complete",
                                         function () {
                    $widget.removeClass("loading");
                    $widget.prev().remove();
                    $widget.css("display", "block");

                    // Allow CSS to reflow
                    window.setTimeout(function () {
                        wed_editor.resize();
                    }, 0);
                });
            }
	});
    }

    if (window.addEventListener) { // DOM
        window.addEventListener('load', init);
    } else if (window.attachEvent) { // IE
        window.attachEvent('onload', init);
    }
})(('undefined' === typeof require) ? undefined : require);
