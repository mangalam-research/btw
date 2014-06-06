(function (factory) {
    // If in an AMD environment, define() our module, else use the
    // jQuery global.
    'use strict';
    if (typeof define === 'function' && define.amd)
        define(['jquery'], factory);
    else
        factory(jQuery);
}(function ($) {
    'use strict';

    // This is the plugin proper.
/**
 * A jQuery plugin. The ``find`` method interprets its selector
 * relative to the object that it is called on. So for instance given
 * the HTML:
 *     <ul>
 *         <li>foo</li>
 *     </ul>
 *
 * ``$("ul").find("ul>li")`` will not match the ``li`` element. This
 * plugin allows for making such match with
 * ``$("ul").selectIn("ul>li")``. The way it works is by applying the
 * selector globally and then narrowing down the results to
 * descendants of the jQuery object.
 *
 * @function external:jQuery.selectIn
 * @author Louis-Dominique Dubeau
 * @license MPL 2.0
 * @copyright 2014 Mangalam Research Center for Buddhist Languages
 */

    $.fn.selectIn = function(selector) {
        var $parent = this;
        return $(selector).filter(function () {
            // The parent element is excluded from the result set.
            if ($parent.is(this))
                return false;

            return $(this).closest($parent).length;
        });
    };
}));
