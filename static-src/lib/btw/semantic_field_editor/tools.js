/**
 * @module lib/btw/semantic_field_editor/tools
 * @desc Tools for the semantic fields editor app.
 * @author Louis-Dominique Dubeau
 */
define(/** @lends auto */ function factory(require, exports, _module) {
  "use strict";

  var $ = require("jquery");
  var Radio = require("backbone.radio");

  /**
   * Identifies a DOM element as an application element. This allows using
   * ``getApplication`` on it.
   */
  function setApplication(el, app) {
    $(el).data("SFEditor", app).attr("data-sfeditor", true);
  }
  exports.setApplication = setApplication;

  /**
   * Given a DOM element, get a reference to the Marionette application to under
   * which the element is situated. A search is performed in the ancestors of
   * ``el`` to find an element that is marked as being the top level of the
   * SFEditor element. It then uses jQuery's data facilities to get a reference.
   *
   * @param {Element} el The DOM element from which to start the search.
   *
   * @returns {module:Marionette.Application|undefined} The application, if
   * found.
   */
  function getApplication(el) {
    var $closest = $(el).closest("[data-sfeditor=true]");
    if (!$closest[0]) {
      return undefined;
    }

    return $closest.data("SFEditor");
  }
  exports.getApplication = getApplication;

  /**
   * A mixin for setting getters on Backbone/Marionette objects.  This mixin
   * will iterate through the key, value pairs of the ``getters`` property and
   * set each key to have for getter function the corresponding value. If
   * ``getters`` is a function, then it will be called and the return value will
   * be used to do the binding.
   */
  function GettersMixin() {
    if (!this.getters) {
      return;
    }

    var getters = (typeof this.getters === "function") ? this.getters() :
          this.getters;

    var keys = Object.keys(getters);
    for (var i = 0; i < keys.length; ++i) {
      var key = keys[i];
      var value = getters[key];
      Object.defineProperty(this, key, {
        get: value.bind(this),
      });
    }
  }

  exports.GettersMixin = GettersMixin;

  /**
   * Commonly used getters used for communicating with the application that
   * contains a Backbone/Marionette element.
   */
  exports.communicationGetters = {
    application: function application() {
      if (!this._cachedApplication) {
        this._cachedApplication = getApplication(this.el);
      }
      return this._cachedApplication;
    },

    channel: function channel() {
      if (!this._cachedChannel) {
        var channelName = this.application.channels.global;
        this._cachedChannel = Radio.channel(channelName);
      }
      return this._cachedChannel;
    },
  };
});
