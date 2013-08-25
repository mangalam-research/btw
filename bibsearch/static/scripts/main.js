require(["jquery", "modules/bibSearch"], function (jQuery, BS) {
    // instantiate the bibliography search class
    var bibSearch = new BS();

    jQuery(document).ready(function () {

        // when the list selection changes fire ajax search event
        jQuery("#id_library").change(function () {
            var keywordField = jQuery("#id_keyword").val();
            if (keywordField.length > 0) {
                // fire the ajax submit
                bibSearch.ajaxSearch();
            }
        });

        var keytimer = null;
        var timerdelay = 300; //adjust speed in ms var
        var keywordHistory = "";

        // when the search keyword changes fire ajax search event
        jQuery("#id_keyword").bind('keyup change input propertychange',
        function (evnt) {

            var code = evnt.which;
            if (code == 13) {
                evnt.preventDefault();
            }

            if (keytimer) {
                //if new key comes before timeout clear it
                clearTimeout(keytimer);
            }

            keytimer = setTimeout(function () {
                var keydata = jQuery("#id_keyword").val()

                if ((keydata.length > 0) && (keywordHistory != keydata))
                // as timerdelay is reached timeout occurs, now
                // fire ajax.
                {
                    bibSearch.ajaxSearch();
                    keywordHistory = keydata;
                }
            }, timerdelay);

        });

    });

});
