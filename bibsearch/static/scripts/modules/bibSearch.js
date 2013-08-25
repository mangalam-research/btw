define(["jquery"], function (jQuery) {

    var bibSearch = function () {
        // populate html by iterating the given data object
        function populateHTML(data) {
            // html population steps
            jQuery("#result_list").html(data);
        }

        function ajaxResult(pageNumber) {
            var dataString = "page=" + pageNumber
            jQuery.ajax({
                url: '/search/results/',
                context: document.body,
                data: dataString
            })
                .done(function (data) {
                populateHTML(data);
                // add jquery selector for the new sync buttons.
                jQuery("#result_list input").click(function () {
                    ajaxSync(this.name);
                });

                jQuery("#result_list a").click(function () {
                    ajaxResult(this.name);
                });
            });
        }

        function ajaxSync(encString) {
            var dataString = "enc=" + encString
            jQuery.ajax({
                url: '/search/sync/',
                context: document.body,
                data: dataString,
                beforeSend: function () {
                    jQuery('#loadingDiv').css('display', 'inline');
                    return true;
                }
            })
                .done(function (data) {
                // remove the button which was clicked
                // to sync information
                var parentObject = jQuery("[" + "name='" +
                    encString + "']").parent();
                parentObject.html("NA");
                if (data == "OK") {
                    alert("Copy successful!.");
                } else if (data == "DUP") {
                    alert("Duplicate item not copied.")
                } else {
                    alert(data);
                }
            })
                .always(function () {
                jQuery('#loadingDiv').css('display', 'none');
            });
        }

        // create a ajax search call
        this.ajaxSearch = function () {
            var dataString = "library=" + jQuery('#id_library').val() + "&keyword=" +
                jQuery('#id_keyword').val();
            jQuery.ajax({
                url: '/search/',
                context: document.body,
                data: dataString,
                beforeSend: function () {
                    jQuery('#loadingDiv').css('display', 'inline');
                    return true;
                }
            })
                .done(function (data) {
                populateHTML(data);
                // add jquery selector for the new sync buttons.
                jQuery("#result_list input").click(function () {
                    ajaxSync(this.name);
                });

                jQuery("#result_list a").click(function () {
                    ajaxResult(this.name);
                });
            })
                .always(function () {
                jQuery('#loadingDiv').css('display', 'none');
            });
        }

    }

    return bibSearch;

});
