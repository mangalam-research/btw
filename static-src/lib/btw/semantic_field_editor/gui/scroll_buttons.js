define(function factory(require) {
  "use strict";
  var $ = require("jquery");
  var ResizeObserver = require("ResizeObserver");

  var template = "\
<div class='scroll-buttons-wrapper'>\
<a href='#' title='Scroll to top'><i class='fa fa-angle-double-up'></i></a>\
<br/>\
<a href='#' title='Scroll to bottom'>\
<i class='fa fa-angle-double-down'></i></a>\
</div>\
";

  /**
   * Add scroll buttons to an element. The buttons are set so that they show up
   * only if the element has a scroll bar. The strategy is that we use
   * ``ResizeObserver`` to listen to size changes on ``forElement`` to this
   * function, and on the single child of this element. The ``forElement``
   * element must have exactly one child element. This is just a means to
   * simplify the code and listen only for changes on two elements.
   */
  function ScrollButtons(forElement) {
    if (forElement.children.length !== 1) {
      throw new Error("the element decorated with scroll buttons must have " +
                      "exactly one child.");
    }

    var div = forElement.ownerDocument.createElement("div");
    div.className = "scroll-buttons";
    div.insertAdjacentHTML("afterbegin", template);

    var wrapper = div.getElementsByClassName("scroll-buttons-wrapper")[0];
    var arrows = div.getElementsByTagName("a");
    var up = arrows[0];
    var down = arrows[1];
    $(up).click(function scrollUp() {
      forElement.scrollTop = 0;
      return false;
    });

    $(down).click(function scrollDown() {
      forElement.scrollTop = forElement.scrollHeight;
      return false;
    });

    var boundRefresh = this.refresh.bind(this);

    var ro = new ResizeObserver(boundRefresh);
    ro.observe(forElement.firstElementChild);
    ro.observe(forElement);

    this.forElement = forElement;
    this.wrapper = wrapper;
    forElement.parentNode.insertBefore(div, forElement);
  }

  ScrollButtons.prototype.refresh = function refresh() {
    // We determine whether there's a scrollbar visible and adjust the
    // visibility of the arrows as needed.
    var forElement = this.forElement;
    this.wrapper.style.display =
      (forElement.scrollHeight > forElement.clientHeight) ? "" : "none";
  };

  return ScrollButtons;
});
