define(
  ["module", "jquery", "velocity", "bluebird", "ajax", "velocity-ui",
   "bootstrap"],
  function factory(module, $, velocity, bluebird, ajax) {
    "use strict";

    var config = module.config();

    // Check whether we are in test mode.
    var test = config.test;

    var Promise = bluebird.Promise;

    function removeData(node) {
      // We need to manually clean out any data jQuery may have added,
      // but only if we are not testing. In testing we do want to keep
      // the data around so that we can check whether elements have been
      // animated by velocity.
      if (!test) {
        $(node).removeData();
      }
    }

    function slideRightIn(el) {
      return velocity(el, {
        opacity: [1, 0],
        translateX: [0, "100%"],
        translateZ: 0,
      }, { duration: 500 });
    }

    function slideLeftIn(el) {
      return velocity(el, {
        opacity: [1, 0],
        translateX: [0, "-100%"],
        translateZ: 0,
      }, { duration: 500 });
    }

    var htmlTemplate = "\
<div class='card semantic-field-details-card' style='display: none'>\
  <h5 class='card-header'>\
    Semantic Field Details <button class='btn btn-sm btn-outline-dark first' href='#'><i class='fa fa-fast-backward'></i></button> <button class='btn btn-sm btn-outline-dark previous' href='#'><i class='fa fa-backward'></i></button> <button class='btn btn-sm btn-outline-dark next' href='#'><i class='fa fa-forward'></i></button> <button class='btn btn-sm btn-outline-dark last' href='#'><i class='fa fa-fast-forward'></i></button><button class='btn btn-sm btn-outline-dark close-card' href='#' title='Close'><i class='fa fa-times'></i></button> <button class='btn btn-sm btn-outline-dark close-all-cards' href='#' title='Close all'><i class='fa fa-times'></i><i class='fa fa-times'></i>\
</button>\
  </h5>\
  <div class='card-body'>\
    <div class='paged-content'>\
    </div>\
  </div>\
</div>\
";

    /**
     * Instances of this class manage a list of {@link
     * module:semantic-field-search~Displayer Displayer} objects.
     *
     * @param {Node} template The DOM template from which new displayers
     * are created. We expect the DOM node to be the top element of
     * ``htmlTemplate`` above.
     *
     * @property {Array.<module:displayers~Displayer>} displayers The list
     * of displayers managed by this object.
     * @property {Node} template The template that was used when the object was
     * created.
     */
    function Displayers(template) {
      this.template = template;
      this.displayers = [];
    }

    /**
     * Close all displayers managed by this object.
     *
     * @returns {Promise} A promise that is resolved to this object when
     * all displayers have been closed. This promise will resolve once all
     * animations related to the closing have been performed.
     */
    Displayers.prototype.closeAll = function closeAll() {
      var displayers = this.displayers.slice();
      var promises = [];
      // eslint-disable-next-line no-cond-assign
      for (var ix = 0, displayer; (displayer = displayers[ix]); ++ix) {
        promises.push(displayer.close());
      }
      return Promise.all(promises).return(this);
    };


    /**
     * Open a new displayer, if necessary. If none of the currently opened
     * displayer displays the URL passed, a new displayer is created and
     * added at the end of the list of displayers. The first new displayer
     * created is added in the DOM **before** the template that was passed
     * to the constructor of ``this``. Subsequent displayers are added
     * before all the other displayers already managed by ``this``. If
     * there is a displayer which currently shows the URL, the page is
     * scrolled to that displayer but no new displayer is added.
     *
     * @param {string} url The URL to display. This URL must be a URL from
     * which an HTML representation of a semantic field can be loaded.
     * @fires module:semantic-field-search~Displayers#open.displayers
     *
     * @returns {Promise} A promise that resolves to the current
     * object. The promise is resolved when the URL has been opened,
     * displayed, and all animations are done.
     */
    Displayers.prototype.open = Promise.method(function open(url) {
      var displayer;
      // eslint-disable-next-line no-cond-assign
      for (var ix = 0; (displayer = this.displayers[ix]); ++ix) {
        if (displayer.url === url) {
          break;
        }
      }

      // We found a displayer currently showing this URL, just move to it.
      if (displayer) {
        displayer.display_div.scrollIntoView();
        return velocity(displayer.display_div, "callout.shake")
          .return(displayer);
      }

      // No displayer currently shows this URL, create one.
      var dom = this.template.cloneNode(true);
      var before = this.displayers.length ?
          this.displayers[0].display_div : this.template;
      this.template.parentNode.insertBefore(dom, before);
      // eslint-disable-next-line no-use-before-define
      displayer = new Displayer(this, dom);
      this.displayers.unshift(displayer);
      $(dom).one("closed.displayer", function closed() {
        var index = this.displayers.indexOf(displayer);
        this.displayers.splice(index, 1);
      }.bind(this));
      dom.style.display = "";
      dom.scrollIntoView();
      velocity(dom, "transition.expandIn");
      return displayer.display(url).then(function displayed() {
        dom.scrollIntoView();
        /**
         * (The event is not actually an object. The properties
         * described here are passed as parameters to the event
         * handling function given to jQuery.)
         *
         * @event module:semantic-field-search~Displayers#open.displayers
         * @type {jQuery event}
         * @property {module:semantic-field-search~Displayers} displayers The
         * object which had a new URL opened on it.
         */
        $(this.template).trigger("open.displayers", [displayer]);
        return displayer;
      }.bind(this));
    });

    /**
     * A ``Displayer`` displays a semantic field in an area of the
     * page. It is responsible for loading the HTML representation of the
     * semantic field, and providing navigation. The HTML representation
     * of a field is loaded in a card with buttons to navigate the field
     * hierarchy and buttons to go back and forth in the history of what
     * has been show in the card. (Like a browser.) This class is
     * responsible for setting up the GUI and setting up and managing the
     * history.
     *
     * @param {module:semantic-field-search:~Displayers} displayers The
     * ``Displayers`` object that manages this displayer. **A ``Displayer`` object
     * can only be managed by one ``Displayers`` object at any given time.**
     * @param {Node} display_div The DOM node in which the semantic field
     * must be loaded.
     */
    function Displayer(displayers, displayDiv) {
      this.displayers = displayers;
      this.display_div = displayDiv;
      this.content = displayDiv.getElementsByClassName("paged-content")[0];
      this.first_button = displayDiv.getElementsByClassName("first")[0];
      this.previous_button = displayDiv.getElementsByClassName("previous")[0];
      this.next_button = displayDiv.getElementsByClassName("next")[0];
      this.last_button = displayDiv.getElementsByClassName("last")[0];
      this.close_button = displayDiv.getElementsByClassName("close-card")[0];
      this.close_all_button = displayDiv.getElementsByClassName(
        "close-all-cards")[0];
      this.history_ix = -1;
      this.history = [];
      this._closed = false;
      this._network_timeout = 200;

      function wrap(cb) {
        return function wrapper() {
          cb();
        };
      }

      $(this.first_button).click(wrap(this.first.bind(this)));
      $(this.previous_button).click(wrap(this.previous.bind(this)));
      $(this.next_button).click(wrap(this.next.bind(this)));
      $(this.last_button).click(wrap(this.last.bind(this)));
      $(this.close_button).click(wrap(this.close.bind(this)));
      $(this.close_all_button).click(wrap(this.closeAll.bind(this)));

      this._refresh();
    }

    Object.defineProperty(Displayer.prototype, "url", {
      get: function getUrl() {
        return this.history[this.history_ix];
      },
    });

    Object.defineProperty(Displayer.prototype, "closed", {
      get: function getClosed() {
        return this._closed;
      },
    });

    /**
     * Go back to the first semantic field in the history recorded by
     * ``this`` and display the field. Has no effect if we are already at
     * the first semantic field in the history.
     *
     * @returns {Promise} A promise that resolves to this object after the
     * display has been changed to display the new URL and all animations
     * are done. If the operation has no effect, the promise resolves
     * immediately.
     */
    Displayer.prototype.first = function first() {
      if (this.history_ix > 0) {
        this.history_ix = 0;
        return this._refresh({ transition: "previous" });
      }
      return Promise.resolve(this);
    };

    /**
     * Go back to the previous semantic field in the history recorded by
     * ``this`` and display the field. Has no effect if we are already at
     * the first semantic field in the history.
     *
     * @returns {Promise} A promise that resolves to this object after the
     * display has been changed to display the new URL and all animations
     * are done. If the operation has no effect, the promise resolves
     * immediately.
     */
    Displayer.prototype.previous = function previous() {
      if (this.history_ix > 0) {
        this.history_ix--;
        return this._refresh({ transition: "previous" });
      }
      return Promise.resolve(this);
    };

    /**
     * Go forward to the next semantic field in the history recorded by
     * ``this`` and display the field. Has no effect if we are already at
     * the last semantic field in the history.
     *
     * @returns {Promise} A promise that resolves to this object after the
     * display has been changed to display the new URL and all animations
     * are done. If the operation has no effect, the promise resolves
     * immediately.
     */
    Displayer.prototype.next = function next() {
      if (this.history_ix < this.history.length - 1) {
        this.history_ix++;
        return this._refresh({ transition: "next" });
      }
      return Promise.resolve(this);
    };

    /**
     * Go forward to the last semantic field in the history recorded by
     * ``this`` and display the field. Has no effect if we are already at
     * the last semantic field in the history.
     *
     * @returns {Promise} A promise that resolves to this object after the
     * display has been changed to display the new URL and all animations
     * are done. If the operation has no effect, the promise resolves
     * immediately.
     */
    Displayer.prototype.last = function last() {
      if (this.history_ix < this.history.length - 1) {
        this.history_ix = this.history.length - 1;
        return this._refresh({ transition: "next" });
      }
      return Promise.resolve(this);
    };

    /**
     * Close this displayer. Has no effect if the displayer has already
     * been closed. This method actually calls {@link
     * module:semantic-field-search:~Displayers#close} on the
     * ``Displayers`` object that manages this displayer.
     *
     * @returns {Promise} A promise that resolves to this object once the
     * displayer is closed.
     */
    Displayer.prototype.close = Promise.method(function close() {
      if (this.closed) {
        return this;
      }

      var $div = $(this.display_div);
      return velocity(this.display_div, "transition.expandOut")
        .then(function expanded() {
          $div.trigger("closed.displayer", [this]);
          this._close();
          return this;
        }.bind(this));
    });

    /**
     * Close this displayer and all its siblings. Has no effect if the
     * displayer has already been closed. This method actually calls
     * {@link module:semantic-field-search:~Displayers#closeAll} on the
     * ``Displayers`` object that manages this displayer.
     *
     * @returns {Promise} A promise that is resolved to the ``Displayers``
     * that contains this object when all displayers have been
     * closed. This promise will resolve once all animations related to
     * the closing have been performed. If the current object is already
     * closed, the promise resolves to ``null``.
     */
    Displayer.prototype.closeAll = Promise.method(function closeAll() {
      if (!this.display_div.parentNode) {
        return null;
      }

      return this.displayers.closeAll();
    });

    /**
     * Display a URL on this displayer. If the URL passed is the same as
     * the URL currently displayed, it has no effect.
     *
     * @param {string} url The URL of the semantic field to display. This
     * URL must return a HTML representation of the semantic field a
     * ``GET`` that accepts only ``text/html`` is issued on it.
     *
     * @returns {Promise} A promise that is resolved once the new URL is
     * displayed. The resolved value is this Displayer object. The promise
     * will be rejected if the object has already been closed or if its
     * ``display_div`` is not in the DOM anymore.
     *
     */
    Displayer.prototype.display = Promise.method(function display(url) {
      if (this.closed) {
        throw new Error("trying to display a URL on a closed Displayer");
      }

      if (!this.display_div.parentNode) {
        throw new Error("trying to display a URL on a Displayer which is " +
                        "not in the DOM");
      }

      // Don't do anything if the user wants to display what is already
      // there.
      if (url === this.history[this.history_ix]) {
        return this;
      }

      // Scrap the tail of the history.
      this.history = this.history.slice(0, this.history_ix + 1);

      // Record the new history.
      this.history.push(url);
      this.history_ix++;

      return this._refresh({ transition: "next" });
    });

    /**
     * Refresh the URL currently displayed.
     *
     * @param {Object} [options] Options to the refresh method. The field
     * ``transition`` can be used to name a transition to use when showing the URL.
     *
     * @return {Promise} A promise that resolves to this object once the
     * URL has been refreshed and animations completed. If the Ajax
     * operation fails, the promise will be rejected with an ``Error``
     * object that has for fields ``jqXHR``, ``textStatus`` and
     * ``errorThrown`` which correspond to the values that jQuery passes
     * to the ``.fail`` method.
     */
    Displayer.prototype._refresh = Promise.method(function _refresh(options) {
      if (this.closed) {
        return this;
      }

      if (!this.display_div.parentNode) {
        return this;
      }

      options = options || {};

      var self = this;

      var ix = this.history_ix;

      this.first_button.disabled = this.previous_button.disabled = (ix <= 0);
      this.last_button.disabled = this.next_button.disabled =
        (ix >= this.history.length - 1);

      var url = this.history[this.history_ix];
      if (!url) {
        return this;
      }

      function clickHandler(ev) {
        self.display(ev.target.href);
        return false;
      }

      var content = this.content;

      var spinnerTimeout = setTimeout(function onTimeout() {
        // We want to maintain the size while we are loading. Otherwise,
        // putting the spinner in will make the div super small.
        var rect = content.getBoundingClientRect();
        if (content.innerHTML.trim() !== "") {
          content.style.width = rect.width + "px";
          content.style.height = rect.height + "px";
        }
        content.style.lineHeight = rect.height + "px";
        content.style.textAlign = "center";
        removeData(content.childNodes);
        content.innerHTML = "<i class='fa fa-spinner fa-2x fa-spin'></i>";
      }, this._network_timeout);

      return ajax.ajax({
        url: url,
        headers: {
          Accept: "text/html",
        },
      }).finally(function ajaxFinally() {
        clearTimeout(spinnerTimeout);
      }).then(function afterAjax(data) {
        removeData(content.childNodes);
        content.innerHTML = data;
        content.style.width = "";
        content.style.height = "";
        content.style.lineHeight = "";
        content.style.textAlign = "";
        if (options.transition) {
          var transition = {
            previous: slideLeftIn,
            next: slideRightIn,
          }[options.transition];
          if (transition) {
            transition(content);
          }
        }
        var links = content.getElementsByClassName("sf-link");
        $(links).click(clickHandler);
        /**
         * (The event is not actually an object. The properties
         * described here are passed as parameters to the event
         * handling function given to jQuery.)
         *
         * @event module:semantic-field-search~Displayer#display.refresh
         * @type {jQuery event}
         * @property {string} url The URL refreshed.
         */
        $(self.display_div).trigger("refresh.displayer", [self, url]);
        return self;
      });
    });

    /**
     * Refresh the URL currently displayed.
     *
     * @return {Promise} A promise that resolves to this object once the
     * URL has been refreshed and animations completed. If the Ajax
     * operation fails, the promise will be rejected with an ``Error``
     * object that has for fields ``jqXHR``, ``textStatus`` and
     * ``errorThrown`` which correspond to the values that jQuery passes
     * to the ``.fail`` method.
     */
    Displayer.prototype.refresh = function refresh() {
      return this._refresh();
    };

    /**
     * Perform the nitty-gritty parts of closing a displayer. This removes
     * the displayer from the DOM, and marks it as closed.
     */
    Displayer.prototype._close = function _close() {
      if (this._closed) {
        return;
      }

      var d = this.display_div;
      if (d.parentNode) {
        removeData(d);
        d.parentNode.removeChild(d);
      }
      this._closed = true;
    };

    return {
      html_template: htmlTemplate,
      Displayer: Displayer,
      Displayers: Displayers,
    };
  });
