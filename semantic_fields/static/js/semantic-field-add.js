define(['jquery'], function ($) {

/**
 * Adds a button to create children of a semantic field to the HTML
 * that shows a semantic field. Manages this button so as to allow the
 * creation of a new semantic field. When the button is clicked, a
 * form is presented to create a new field. This form has a "Create"
 * button which allows creating a new field and a "Cancel" button to
 * cancel the addition of the field. The HTML shown by the displayers
 * must contain a button of class ``.create-child``, which this code
 * will manage. The button must have an attribute ``data-form-url``
 * which is set to a URL on which a ``GET`` that accepts
 * ``application/x-form`` will result in a HTML form. It must also
 * have a ``data-create-url`` attribute on which a ``POST`` that
 * accepts ``application/x-form`` will result in either the creation
 * of the field or a form with error messages.
 *
 * @param {@link module:semantic-field-search~Displayers} displayers
 * The object that manages the list of semantic fields that appears
 * after the semantic field search table.
 */
return function (displayers) {
    function setup(displayer) {
        var create =
                displayer.display_div.querySelector("button.create-child");
        var form_url = create.getAttribute("data-form-url");
        var create_url = create.getAttribute("data-create-url");
        var div = displayer.display_div.querySelector("div.create-div");

        function displayForm(data) {
            div.innerHTML = data;
            var form = div.getElementsByTagName("form")[0];
            var cancel = form.querySelector("button.cancel");

            function dismiss() {
                div.innerHTML = '';
                displayer.refresh();
            }

            $(form).on("submit", function () {
                $.ajax({
                    type: "POST",
                    url: create_url,
                    data: $(form).serialize(),
                    headers: {
                        Accept: "application/x-form"
                    }
                }).done(dismiss).fail(function (jqXHR, textStatus,
                                                errorThrown) {
                    displayForm(jqXHR.responseText);
                });
                return false;
            });
            $(cancel).click(dismiss);
        }

        $(create).one("click", function () {
            create.parentNode.removeChild(create);
            $.ajax({
                url: form_url,
                headers: {
                    Accept: "application/x-form"
                }
            }).done(displayForm);
        });
        create.style.display = "";

    }

    $(displayers.template).on("open.displayers", function (ev, displayer) {
        $(displayer.display_div).on("refresh.displayer", function (ev, url) {
            setup(displayer);
        });
        setup(displayer);
    });
};

});
