define(function factory(require) {
  "use strict";

  var $ = require("jquery");
  var bluebird = require("bluebird");
  var bluejax = require("bluejax");
  var ajax = require("ajax");
  require("bootstrap");

  var Promise = bluebird.Promise;

  function ButtonTimeout(button, timeout) {
    var me = this;
    this.spinner = undefined;
    this.timeout = setTimeout(function spinner() {
      button.insertAdjacentHTML(
        "afterbegin",
        "<i class='fa fa-spinner fa-2x fa-spin'></i>");
      me.spinner = button.querySelector(".fa.fa-spinner");
    }, timeout);
  }

  ButtonTimeout.prototype.clear = function clear() {
    var timeout = this.timeout;
    if (timeout) {
      clearTimeout(timeout);
    }
    this.timeout = undefined;

    var spinner = this.spinner;
    if (spinner && spinner.parentNode) {
      spinner.parentNode.removeChild(spinner);
    }
    this.spinner = undefined;
  };


  /**
   * Manages the functions needed to create or change custom fields.
   *
   * To enable the creation of children, the HTML shown by the
   * displayers must contain a button of class ``create-child``, which
   * this code will manage so as to allow the creation of a new semantic
   * field. When the button is clicked, a form is presented to create a
   * new field. This form has a "Create" button which allows creating a
   * new field and a "Cancel" button to cancel the addition of the
   * field.  The button must have an attribute ``data-form-url`` which
   * is set to a URL on which a ``GET`` that accepts
   * ``application/x-form`` will result in a HTML form. It must also
   * have a ``data-post-url`` attribute on which a ``POST`` that
   * accepts ``application/x-form`` will result in either the creation
   * of the field or a form with error messages.
   *
   * To enable the creation of pos variants, the HTML show by the
   * displayers must contain a button of class
   * ``create-related-by-pos``. The form and the URLs are as described
   * above.
   *
   * @param create_buttons A list of DOM nodes that are buttons used to create
   * fields at the root of the field hierarchy. This can be an array of
   * nodes or any kind of array-like construct.
   *
   * @param {Node} create_div A ``div`` element in which to display the
   * field creation form when ``create_buttons`` are clicked.
   *
   * @param {@link module:semantic-field-search~Displayers} displayers
   * The object that manages the list of semantic fields that appears
   * after the semantic field search table.
   */

  return function semanticFieldEdit(createButtons, createDiv, displayers) {
    var networkTimeout = 200;

    function displayForm(div, submitUrl, method, data) {
      div.innerHTML = data;
      var form = div.getElementsByTagName("form")[0];
      var cancel = form.querySelector("a.btn.cancel");
      var submit = form.querySelector("a.btn.submit");

      // There should be a single top fieldset encompassing all fields.
      var fieldset = form.getElementsByTagName("fieldset")[0];

      return new Promise(function makePromise(resolve, _reject) {
        $(submit).on("click", function clickSubmit() {
          // We have to serialize before disabling because disabling
          // excludes the fields from the serialization!
          var serialized = $(form).serialize();
          var timeout = new ButtonTimeout(submit, networkTimeout);
          fieldset.disabled = true; // Prevent multi clicks.
          ajax.ajax({
            type: method,
            url: submitUrl,
            data: serialized,
            headers: {
              Accept: "application/x-form",
            },
          }).finally(timeout.clear.bind(timeout))
            .catch(bluejax.HttpError, function onError(err) {
              if (err.jqXHR.status !== 400) {
                throw err;
              }
              return displayForm(div, submitUrl, method,
                                 err.jqXHR.responseText);
            })
            .then(resolve);
          return false;
        });
        $(cancel).click(function clickCancel() {
          // We don't know how long dismissal will take.
          fieldset.disabled = true;
          resolve();
        });
      });
    }

    function getAndDisplayForm(button, label, formDiv) {
      var formUrl = button.attributes["data-form-url"].value;
      var timeout = new ButtonTimeout(button, networkTimeout);

      var submitUrl;
      var method;
      var methods = ["post", "patch"];
      for (var i = 0; i < methods.length; ++i) {
        var tryMethod = methods[i];
        var attr = button.attributes["data-" + tryMethod + "-url"];
        if (attr) {
          if (method !== undefined) {
            throw new Error(
              "multiple submit methods specified on button " +
                "with class " + button.className);
          }
          submitUrl = attr.value;
          method = tryMethod;
        }
      }

      if (method === undefined) {
        throw new Error("button without defined submit method; " +
                        "the button's class is " + button.className);
      }

      button.disabled = true;
      return ajax.ajax({
        url: formUrl,
        headers: {
          Accept: "application/x-form",
        },
      })
        .finally(function finallyHandler() {
          timeout.clear();
          button.style.display = "none";
          if (label) {
            label.style.display = "none";
          }
        })
        .then(function display(data) {
          return displayForm(formDiv, submitUrl, method, data);
        })
        .then(function clear() {
          createDiv.innerHTML = "";
          button.disabled = false;
          button.style.display = "";
          if (label) {
            label.style.display = "";
          }
        });
    }

    $(createButtons).click(function createClick(ev) {
      var button = ev.target;
      var label = button.closest("label");

      getAndDisplayForm(button, label, createDiv);
    });

    function bindButtonAndDiv(buttonSel, divSel, displayer) {
      var button = displayer.display_div.querySelector(buttonSel);
      var div = displayer.display_div.querySelector(divSel);

      $(button).one("click", function buttonClick() {
        getAndDisplayForm(button, null, div).then(function refresh() {
          displayer.refresh();
        });
      });
    }

    function setup(displayer) {
      bindButtonAndDiv("button.create-child", "div.create-child-div",
                       displayer);
      bindButtonAndDiv("button.create-related-by-pos",
                       "div.create-related-by-pos-div", displayer);
      bindButtonAndDiv("button.edit-field", "div.edit-div", displayer);
    }

    $(displayers.template).on("open.displayers", function open(ev, displayer) {
      $(displayer.display_div).on("refresh.displayer",
                                  function refresh(_ev, _url) {
                                    setup(displayer);
                                  });
      setup(displayer);
    });
  };
});
